#!/usr/bin/env python3
"""Deploy the tiny target on Algorand TestNet and register it on Arcron.

TestNet only. Throwaway dispenser account in .env (gitignored).
This script has not yet been proven against live algod; if a step
fails, believe the chain, not this file.
"""

from __future__ import annotations

import base64
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

from algosdk import account, encoding, logic, mnemonic, transaction
from algosdk.abi import ABIType, Method
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
KEEPER_APP_ID = 769891898
KEEPER_APP_ADDRESS = "M4YFP33L5VIFRF53X53WUMQWBOWSLYQNBSSAJV2SORGF43L36XBY7OREUA"
MIN_UPKEEP_FEE = 4_000
BOX_MBR_FIXED = 2_500 + 400 * 139
SKIP_AHEAD = 1
CATCH_UP = 0  # do not pass this by accident
INTERVAL_ROUNDS = 30
FEE_PER_EXECUTION = 10_000
FUNDING = 30_000
HOOK_SIGNATURE = "run()uint64"


def _require_testnet(url: str) -> None:
    lowered = url.lower()
    if "mainnet" in lowered:
        sys.exit(f"Refusing MainNet endpoint: {url}")
    if "testnet" not in lowered:
        sys.exit(f"Refusing non-TestNet endpoint: {url}")


def _client() -> tuple[AlgodClient, str, AccountTransactionSigner]:
    load_dotenv(ROOT / ".env")
    server = os.environ.get("ALGOD_SERVER", "https://testnet-api.algonode.cloud")
    token = os.environ.get("ALGOD_TOKEN", "")
    port = os.environ.get("ALGOD_PORT", "443")
    _require_testnet(server)
    phrase = os.environ.get("DEPLOYER_MNEMONIC", "").strip()
    if not phrase:
        sys.exit("Set DEPLOYER_MNEMONIC in .env (throwaway TestNet dispenser account).")
    sk = mnemonic.to_private_key(phrase)
    addr = account.address_from_private_key(sk)
    algod_address = server if server.endswith(str(port)) or port in ("443", "") else f"{server}:{port}"
    if server.startswith("http") and ":443" not in server and port == "443":
        algod_address = server
    client = AlgodClient(token, algod_address)
    return client, addr, AccountTransactionSigner(sk)


def _compile_target() -> tuple[bytes, bytes]:
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "puyapy",
        str(ROOT / "contracts" / "minimal_target.py"),
        "--out-dir",
        str(artifacts),
    ]
    print("compile:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)
    approval = next(artifacts.rglob("*approval.teal"), None)
    clear = next(artifacts.rglob("*clear.teal"), None)
    if approval is None or clear is None:
        sys.exit(f"puyapy did not emit approval/clear teal under {artifacts}")
    return approval.read_bytes(), clear.read_bytes()


def _compile_teal(client: AlgodClient, source: bytes) -> bytes:
    result = client.compile(source.decode())
    return base64.b64decode(result["result"])


def _selector(signature: str) -> bytes:
    return hashlib.new("sha512_256", signature.encode()).digest()[:4]


def _global_uint(client: AlgodClient, app_id: int, name: str) -> int | None:
    info = client.application_info(app_id)
    for entry in info["params"].get("global-state", []):
        key = base64.b64decode(entry["key"])
        try:
            decoded = key.decode("utf-8")
        except UnicodeDecodeError:
            decoded = ""
        if decoded == name:
            return int(entry["value"].get("uint", 0))
    return None


def _sp(client: AlgodClient):
    params = client.suggested_params()
    last = client.status()["last-round"]
    params.first = last
    params.last = last + 1_000
    return params


def deploy(client: AlgodClient, sender: str, signer: AccountTransactionSigner) -> int:
    approval_src, clear_src = _compile_target()
    approval = _compile_teal(client, approval_src)
    clear = _compile_teal(client, clear_src)
    extra = max(0, (max(len(approval), len(clear)) - 1) // 2048)
    params = _sp(client)
    params.flat_fee = True
    params.fee = 1_000
    txn = transaction.ApplicationCreateTxn(
        sender=sender,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval,
        clear_program=clear,
        global_schema=transaction.StateSchema(num_uints=4, num_byte_slices=0),
        local_schema=transaction.StateSchema(num_uints=0, num_byte_slices=0),
        extra_pages=extra,
    )
    atc = AtomicTransactionComposer()
    atc.add_transaction(TransactionWithSigner(txn, signer))
    result = atc.execute(client, 8)
    txid = result.tx_ids[0]
    info = client.pending_transaction_info(txid)
    app_id = int(info["application-index"])
    print(f"deployed app {app_id} tx {txid}")
    return app_id


def _call(client, sender, signer, app_id: int, method: Method, args: list) -> None:
    params = _sp(client)
    params.flat_fee = True
    params.fee = 2_000
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=app_id,
        method=method,
        sender=sender,
        sp=params,
        signer=signer,
        method_args=args,
    )
    result = atc.execute(client, 8)
    print(f"{method.name} tx {result.tx_ids[0]} return {result.abi_results[0].return_value!r}")


def register(client, sender, signer, target_app: int) -> int:
    derived = logic.get_application_address(KEEPER_APP_ID)
    if derived != KEEPER_APP_ADDRESS:
        sys.exit(f"keeper app address mismatch: {derived} != {KEEPER_APP_ADDRESS}")
    next_id = _global_uint(client, KEEPER_APP_ID, "next_upkeep_id")
    if next_id is None:
        # Guess: algopy GlobalState uses the field name as the key.
        # integrating.md says this is not derivable from that page.
        sys.exit(
            "Could not read global-state key 'next_upkeep_id' on 769891898. "
            "That key is inferred from the keeper contract field name; "
            "docs/integrating.md says the box ref lives in docs/arcron.md."
        )
    selector = _selector(HOOK_SIGNATURE)
    call_args = [selector]
    encoded = ABIType.from_string("byte[][]").encode([list(a) for a in call_args])
    mbr = BOX_MBR_FIXED + 400 * len(encoded)
    params = _sp(client)
    params.flat_fee = True
    params.fee = 1_000
    mbr_pay = transaction.PaymentTxn(sender, params, KEEPER_APP_ADDRESS, mbr)
    fund_pay = transaction.PaymentTxn(sender, params, KEEPER_APP_ADDRESS, FUNDING)
    method = Method.from_signature(
        "register(pay,pay,application,byte[][],uint64,uint64,uint64,uint64,uint64,uint64)uint64"
    )
    box_name = b"u" + next_id.to_bytes(8, "big")
    call_params = _sp(client)
    call_params.flat_fee = True
    call_params.fee = 2_000
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=KEEPER_APP_ID,
        method=method,
        sender=sender,
        sp=call_params,
        signer=signer,
        method_args=[
            TransactionWithSigner(mbr_pay, signer),
            TransactionWithSigner(fund_pay, signer),
            target_app,
            call_args,
            INTERVAL_ROUNDS,
            FEE_PER_EXECUTION,
            SKIP_AHEAD,
            0,
            0,
            0,
        ],
        boxes=[(KEEPER_APP_ID, box_name)],
    )
    result = atc.execute(client, 8)
    upkeep_id = int(result.abi_results[0].return_value)
    print(
        f"registered upkeep {upkeep_id} on keeper {KEEPER_APP_ID}; "
        f"tx {result.tx_ids[-1]}; interval {INTERVAL_ROUNDS} SKIP_AHEAD"
    )
    print(f"explorer app https://testnet.explorer.perawallet.app/application/{target_app}")
    print(f"explorer keeper https://testnet.explorer.perawallet.app/application/{KEEPER_APP_ID}")
    print(f"explorer tx https://testnet.explorer.perawallet.app/tx/{result.tx_ids[-1]}")
    return upkeep_id


def main() -> None:
    started = time.time()
    client, sender, signer = _client()
    print(f"sender {sender}")
    app_id = deploy(client, sender, signer)
    _call(client, sender, signer, app_id, Method.from_signature("set_keeper(uint64)void"), [KEEPER_APP_ID])
    _call(client, sender, signer, app_id, Method.from_signature("request_work()uint64"), [])
    upkeep_id = register(client, sender, signer, app_id)
    elapsed = time.time() - started
    print(f"demo wall time so far: {elapsed:.1f}s (execute not yet observed)")
    print("next: python scripts/observe.py")
    (ROOT / "artifacts" / "last_run.txt").write_text(
        f"app_id={app_id}\nupkeep_id={upkeep_id}\nsender={sender}\n"
    )


if __name__ == "__main__":
    main()
