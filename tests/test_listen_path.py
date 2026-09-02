"""LocalNet recreate + listen path guards. No algod, no mnemonic, no spend."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
LISTEN_SRC = (ROOT / "scripts" / "localnet_listen.py").read_text()
RECREATE_SRC = (ROOT / "scripts" / "localnet_recreate.py").read_text()
DEPLOY = json.loads((ROOT / "docs" / "deploy.json").read_text())
LOCALNET = json.loads((ROOT / "docs" / "localnet.json").read_text())
LISTEN = json.loads((ROOT / "docs" / "listen.json").read_text())

BANK = "IFZZOTEBLLAV7DA4WP7IPZWZW67KXB5ZNYLZAWJ2S6M3KKNAX55BRXVK2Y"
FORBIDDEN_LOCALNET_COPY = {1001, 1002, 1003, 1004, 1005}


def test_deploy_json_never_holds_localnet_ids() -> None:
    assert DEPLOY["network"] == "testnet"
    assert DEPLOY["appId"] == 0
    assert DEPLOY["upkeepId"] == 0
    assert DEPLOY.get("executeTxid", "") == ""
    assert DEPLOY["appId"] not in FORBIDDEN_LOCALNET_COPY
    assert int(LOCALNET["appId"]) not in (0, DEPLOY["appId"]) or DEPLOY["appId"] == 0
    # Never paste the LocalNet recreate/listen app into TestNet Pages config.
    assert DEPLOY["appId"] != int(LOCALNET["appId"])
    assert DEPLOY["appId"] != int(LISTEN["appId"])
    assert DEPLOY["appId"] != int(LISTEN.get("mockKeeperAppId") or -1)


def test_localnet_snapshot_is_clearly_localnet_only() -> None:
    assert LOCALNET["network"] == "localnet"
    assert LOCALNET["genesisId"] == "dockernet-v1"
    assert LOCALNET["algod"] == "http://localhost:4001"
    assert int(LOCALNET["appId"]) > 0
    assert int(LOCALNET["appId"]) not in FORBIDDEN_LOCALNET_COPY
    assert "testnet" not in LOCALNET["notes"].lower() or "not" in LOCALNET["notes"].lower()
    assert "Do NOT copy this appId into docs/deploy.json" in LOCALNET["notes"]
    assert BANK not in json.dumps(LOCALNET)


def test_listen_snapshot_matches_recreate_and_shows_mock_run() -> None:
    assert LISTEN["network"] == "localnet"
    assert LISTEN["genesisId"] == "dockernet-v1"
    assert LISTEN["algod"] == "http://localhost:4001"
    assert int(LISTEN["appId"]) == int(LOCALNET["appId"])
    assert int(LISTEN["mockKeeperAppId"]) > 0
    assert int(LISTEN["mockKeeperAppId"]) != int(LISTEN["appId"])
    assert int(LISTEN["mockKeeperAppId"]) not in FORBIDDEN_LOCALNET_COPY

    methods = [c["method"] for c in LISTEN["calls"]]
    assert methods == ["set_keeper", "request_work", "run"]
    assert all(c.get("success") is True for c in LISTEN["calls"])
    run = LISTEN["calls"][2]
    assert run["via"] == "mock_keeper.run"
    assert run["hook"] == "run"
    assert int(run["innerCount"]) >= 1
    assert int(run["targetAppId"]) == int(LISTEN["appId"])

    g = LISTEN["global"]
    assert int(g["keeper_app"]) == int(LISTEN["mockKeeperAppId"])
    assert int(g["work_done"]) >= 1
    assert int(g["pending"]) == 0
    assert int(g["last_run_round"]) > 0
    assert "Do NOT copy this appId into docs/deploy.json" in LISTEN["notes"]
    assert "81" in LISTEN["notes"] and "87" in LISTEN["notes"]
    assert BANK not in json.dumps(LISTEN)


def test_listen_and_recreate_scripts_stay_on_localhost() -> None:
    for src in (LISTEN_SRC, RECREATE_SRC):
        assert 'ALGOD_URL = "http://localhost:4001"' in src
        assert 'KMD_URL = "http://localhost:4002"' in src
        assert "testnet-api" not in src
        assert "mainnet-api" not in src
        assert "Never writes docs/deploy.json" in src
        assert "refuse_wrong_network" in src
        assert 'if "testnet" in g:' in src
        assert 'if "mainnet" in g:' in src
        assert f'BANK = "{BANK}"' in src
        assert "if addr == BANK:" in src
        assert "DEPLOY_JSON.write_text" not in src
        assert "mnemonic" not in src.lower() or "never" in src.lower()


def test_listen_script_writes_listen_json_only() -> None:
    assert "LISTEN_JSON.write_text" in LISTEN_SRC
    assert "OUT.write_text" in RECREATE_SRC  # localnet.json
    assert re.search(r"DEPLOY_JSON\.write", LISTEN_SRC) is None
    assert re.search(r"DEPLOY_JSON\.write", RECREATE_SRC) is None
    assert "mock_keeper.run" in LISTEN_SRC or "MK_RUN" in LISTEN_SRC
    assert 'Method.from_signature("run(uint64)void")' in LISTEN_SRC
    assert "request_work()uint64" in LISTEN_SRC


def test_readme_documents_localnet_proof_without_promoting_ids() -> None:
    assert "docs/localnet.json" in README
    assert "docs/listen.json" in README
    assert "LocalNet-only" in README or "LocalNet ids are ephemeral" in README
    assert "Do **not** copy any LocalNet app id into `docs/deploy.json`" in README
    assert "`appId` stays 0 until a real TestNet create" in README
    # Live TestNet table stays honest.
    assert "Live TestNet app id: **not done**" in README
    assert "scripts/localnet_recreate.py" in README
    assert "scripts/localnet_listen.py" in README
