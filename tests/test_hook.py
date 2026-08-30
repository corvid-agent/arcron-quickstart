"""Static checks that the hook rules hold. No TestNet, no mnemonic."""

from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "contracts" / "minimal_target.py").read_text()


def test_hook_is_zero_arg() -> None:
    assert "def run(self) -> UInt64:" in SRC
    assert "def run(self, " not in SRC


def test_auth_uses_application_address_not_itob() -> None:
    assert "Application(self.keeper_app.value).address" in SRC
    assert "itob" not in SRC


def test_keeper_id_is_not_hardcoded_in_the_contract() -> None:
    assert "769891898" not in SRC


def test_create_does_not_take_the_keeper() -> None:
    assert "def __init__(self) -> None:" in SRC
    assert "def set_keeper(self, keeper_app: UInt64) -> None:" in SRC


def test_noop_returns_rather_than_asserting() -> None:
    assert "return UInt64(0)" in SRC
