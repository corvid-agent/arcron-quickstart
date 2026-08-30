#!/usr/bin/env python3
"""Wait until keeper 769891898 executes our target. TestNet only."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from algosdk.v2client.indexer import IndexerClient
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
KEEPER_APP_ID = 769891898


def _require_testnet(url: str) -> None:
    lowered = url.lower()
    if "mainnet" in lowered:
        sys.exit(f"Refusing MainNet endpoint: {url}")
    if "testnet" not in lowered:
        sys.exit(f"Refusing non-TestNet endpoint: {url}")


def main() -> None:
    load_dotenv(ROOT / ".env")
    server = os.environ.get("INDEXER_SERVER", "https://testnet-idx.algonode.cloud")
    token = os.environ.get("INDEXER_TOKEN", "")
    _require_testnet(server)
    last = ROOT / "artifacts" / "last_run.txt"
    if not last.exists():
        sys.exit("No artifacts/last_run.txt — run scripts/demo.py first.")
    values = dict(line.split("=", 1) for line in last.read_text().splitlines() if "=" in line)
    app_id = int(values["app_id"])
    upkeep_id = int(values["upkeep_id"])
    indexer = IndexerClient(token, server)
    print(f"watching keeper {KEEPER_APP_ID} for inner calls to app {app_id} (upkeep {upkeep_id})")
    deadline = time.time() + 15 * 60
    seen: set[str] = set()
    while time.time() < deadline:
        try:
            page = indexer.search_transactions(application_id=KEEPER_APP_ID, limit=30)
        except Exception as exc:  # noqa: BLE001 — indexer blips
            print(f"indexer error {exc}; retry")
            time.sleep(8)
            continue
        for txn in page.get("transactions", []):
            txid = txn.get("id", "")
            if txid in seen:
                continue
            inners = txn.get("inner-txns", []) or txn.get("inner-transactions", [])
            for inner in inners:
                inner_app = (inner.get("application-transaction") or {}).get("application-id")
                if inner_app == app_id:
                    rnd = txn.get("confirmed-round")
                    print(f"execute tx {txid} round {rnd}")
                    print(f"https://testnet.explorer.perawallet.app/tx/{txid}")
                    return
            seen.add(txid)
        time.sleep(8)
    sys.exit("No execute observed in 15 minutes. Not done — do not invent a txid.")


if __name__ == "__main__":
    main()
