"""Static honesty: TestNet deploy.json stays 0; LocalNet proof stays localnet."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = json.loads((ROOT / "docs" / "deploy.json").read_text())
LOCALNET = json.loads((ROOT / "docs" / "localnet.json").read_text())
README = (ROOT / "README.md").read_text()
RECREATE = (ROOT / "scripts" / "localnet_recreate.py").read_text()
LISTEN_SRC = ROOT / "scripts" / "localnet_listen.py"
APP_JS = (ROOT / "docs" / "app.js").read_text()


def test_deploy_json_stays_testnet_undeployed() -> None:
    assert DEPLOY.get("network") == "testnet"
    assert int(DEPLOY.get("appId") or 0) == 0
    assert int(DEPLOY.get("upkeepId") or 0) == 0
    assert DEPLOY.get("executeTxid") in ("", None)
    assert DEPLOY.get("hook") == "run()uint64"


def test_localnet_json_is_localnet_not_testnet() -> None:
    assert LOCALNET.get("network") == "localnet"
    assert int(LOCALNET.get("appId") or 0) > 0
    genesis = str(LOCALNET.get("genesisId") or "").lower()
    assert "testnet" not in genesis
    assert "mainnet" not in genesis
    assert "localhost:4001" in str(LOCALNET.get("algod") or "")


def test_localnet_appid_not_copied_into_deploy() -> None:
    assert int(DEPLOY.get("appId") or 0) != int(LOCALNET.get("appId") or 0)
    assert str(LOCALNET.get("appId")) not in json.dumps(DEPLOY)


def test_recreate_never_writes_deploy_json() -> None:
    assert "Never writes docs/deploy.json" in RECREATE
    assert "DEPLOY_JSON.write" not in RECREATE
    assert "docs/deploy.json" in RECREATE  # it may warn, but must not write
    assert "OUT.write_text" in RECREATE


def test_listen_never_writes_deploy_json() -> None:
    src = LISTEN_SRC.read_text()
    assert "Never writes docs/deploy.json" in src
    assert "DEPLOY_JSON.write" not in src
    assert "LISTEN_JSON.write_text" in src


def test_readme_says_testnet_appid_stays_zero() -> None:
    lowered = README.lower()
    assert "appid stays 0" in lowered or "appid: 0" in lowered or "appId stays 0" in README
    assert "python scripts/localnet_recreate.py" in README
    assert "python scripts/localnet_listen.py" in README
    assert "not TestNet" in README or "not testnet" in lowered


def test_pages_does_not_paint_localnet_as_testnet() -> None:
    assert "loadLocalnetProof" in APP_JS
    assert 'ln.network !== "localnet"' in APP_JS
    assert "INDEXER" in APP_JS
    assert "./deploy.json" in APP_JS
    assert "./localnet.json" in APP_JS
    assert "./listen.json" in APP_JS
    assert "./due.json" in APP_JS
    assert "loadDueSnapshot" in APP_JS
    assert "quickstartAppId" in APP_JS
    assert "setNetworkMeta" in APP_JS
    assert "ln.created_at" in APP_JS
    assert '" · proof "' in APP_JS or " · proof " in APP_JS
    # Undeployed path must keep "not on TestNet" even when due.json has a TestNet round
    assert "not on TestNet" in APP_JS
    html = (ROOT / "docs" / "index.html").read_text()
    assert 'id="network-meta"' in html
    assert "LocalNet proof only" in html
    assert "not on TestNet" in html
    assert "created_at" in html
    assert "2026-09-18" in html
    assert "due.json" in html


def test_readme_stamps_last_recreate_and_dockerd_block() -> None:
    assert "2026-09-18" in README
    assert "2026-09-22" in README
    assert "no dockerd" in README.lower() or "Container engine not found" in README
    assert "unsigned" in README.lower()
    assert "probe_keeper.py" in README
    assert "docs/due.json" in README or "`docs/due.json`" in README
    assert int(DEPLOY.get("appId") or 0) == 0


def test_listen_json_is_localnet_not_testnet() -> None:
    listen_path = ROOT / "docs" / "listen.json"
    assert listen_path.is_file()
    listen = json.loads(listen_path.read_text())
    assert listen.get("network") == "localnet"
    assert int(listen.get("appId") or 0) == int(LOCALNET.get("appId") or 0)
    assert int(listen.get("mockKeeperAppId") or 0) > 0
    assert int(listen.get("mockKeeperAppId") or 0) != int(DEPLOY.get("appId") or 0)
    genesis = str(listen.get("genesisId") or "").lower()
    assert "testnet" not in genesis
    assert "mainnet" not in genesis
    # Quickstart MinimalTarget globals (not deadman tripped/timeout_rounds).
    g = listen.get("global") or {}
    assert int(g.get("work_done") or 0) >= 1
    assert int(g.get("pending") or 0) == 0
    assert int(g.get("last_run_round") or 0) > 0
    assert int(g.get("keeper_app") or 0) == int(listen.get("mockKeeperAppId") or 0)
    calls = listen.get("calls") or []
    methods = [c.get("method") for c in calls]
    assert "set_keeper" in methods
    assert "request_work" in methods
    assert "run" in methods
    assert str(listen.get("appId")) not in json.dumps(DEPLOY)


def test_mock_keeper_is_localnet_only_source() -> None:
    src = (ROOT / "smart_contracts" / "mock_keeper" / "contract.py").read_text()
    assert "Not for TestNet" in src
    assert "def run(self, app: Application)" in src
    assert 'arc4_signature("run()uint64")' in src


def test_due_json_unsigned_keeper_probe() -> None:
    """Unsigned TestNet keeper probe; never invents a quickstart app/upkeep."""
    due_path = ROOT / "docs" / "due.json"
    assert due_path.is_file()
    due = json.loads(due_path.read_text())
    assert due.get("network") == "testnet"
    assert int(due.get("keeperAppId") or 0) == 769891898
    assert int(due.get("quickstartAppId") or 0) == 0
    assert int(due.get("quickstartUpkeepId") or 0) == 0
    assert int(due.get("lastRound") or 0) > 0
    assert int(due.get("nextUpkeepId") or 0) > 0
    assert due.get("probedAt")
    assert "unsigned" in str(due.get("source") or "").lower() or "algod" in str(due.get("source") or "").lower()
    # LocalNet proof ids must not leak into due.json as a TestNet quickstart
    assert int(due.get("quickstartAppId") or 0) != int(LOCALNET.get("appId") or 0)
    skipped = {int(s.get("id")) for s in (due.get("skipped") or []) if isinstance(s, dict)}
    assert 81 in skipped
    assert 87 in skipped
    assert int(DEPLOY.get("appId") or 0) == 0
    assert str(LOCALNET.get("appId")) not in json.dumps(
        {k: due[k] for k in due if k not in ("notes",)}
    )


def test_probe_keeper_never_writes_deploy_json() -> None:
    src = (ROOT / "scripts" / "probe_keeper.py").read_text()
    assert "Never writes docs/deploy.json" in src or "never writes docs/deploy.json" in src.lower()
    assert "DEPLOY_JSON.write" not in src
    assert "OUT.write_text" in src
    assert "docs/due.json" in src
    assert "769891898" in src
    assert "81" in src and "87" in src
    assert "BANK" in src
