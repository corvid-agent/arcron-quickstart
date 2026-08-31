"""The ten-minute path in the README has to match the code. No TestNet."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
DEMO = (ROOT / "scripts" / "demo.py").read_text()
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
DEPLOY = json.loads((ROOT / "docs" / "deploy.json").read_text())


def test_compile_command_matches_ci() -> None:
    cmd = "python -m puyapy contracts/minimal_target.py"
    assert cmd in README
    assert cmd in CI
    assert "puyapy contracts/minimal_target.py --out-dir" not in README
    assert "--out-dir" not in DEMO
    assert "--out-dir" not in CI


def test_create_has_zero_args() -> None:
    assert "app_args=[]" in DEMO
    assert "create with ZERO args" in README or "Create with **zero args**" in README
    assert "set_keeper(Application(769891898))" in README
    assert "set_keeper(application)void" in DEMO
    assert "set_keeper(uint64)" not in DEMO


def test_hook_auth_is_application_address_not_itob() -> None:
    assert "Application(keeper).address" in README
    assert "itob" in README  # named as the thing not to do


def test_crt_stays_honest_while_undeployed() -> None:
    assert DEPLOY["network"] == "testnet"
    assert DEPLOY["keeperAppId"] == 769891898
    if DEPLOY["appId"] == 0:
        assert DEPLOY["upkeepId"] == 0
        assert DEPLOY.get("executeTxid", "") == ""
        assert "mainnet" not in json.dumps(DEPLOY).lower()
