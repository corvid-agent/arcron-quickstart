"""The smallest contract Arcron can drive.

Zero-arg hook, keeper-app authorization via Application(...).address
no-op returns rather than fails. The keeper app id is
set once through set_keeper — it is not a create argument, and it is
not hardcoded here.

Modeled on CorvidLabs/arcron examples/minimal_target.py.
The full reasoning is in that repo's docs/integrating.md.
"""

from algopy import (  # pyright: ignore[reportMissingModuleSource]
    ARC4Contract,
    Application,
    Global,
    GlobalState,
    Txn,
    UInt64,
)
from algopy.arc4 import abimethod  # pyright: ignore[reportMissingModuleSource]


class MinimalTarget(ARC4Contract):
    """Does a small amount of work, on a schedule, for whoever pays."""

    def __init__(self) -> None:
        # Named later via set_keeper. Do not pass the keeper id at create
        # and do not stuff that id into every uint64 argument.
        self.keeper_app = GlobalState(UInt64(0))
        self.work_done = GlobalState(UInt64(0))
        self.last_run_round = GlobalState(UInt64(0))
        self.pending = GlobalState(UInt64(0))

    @abimethod()
    def set_keeper(self, keeper: Application) -> None:
        """Name the keeper whose app account may call run.

        Creator only, once. Pass the keeper application, not a raw uint64
        cadence. Store .id. run() authorizes Application(keeper).address.
        """
        assert Txn.sender == Global.creator_address, "Only the creator can set the keeper"
        assert self.keeper_app.value == 0, "Keeper already set"
        assert keeper.id != 0, "Keeper app required"
        self.keeper_app.value = keeper.id

    @abimethod()
    def request_work(self) -> UInt64:
        """Something for the scheduled call to find. Stands in for real state."""
        self.pending.value += 1
        return self.pending.value

    @abimethod()
    def run(self) -> UInt64:
        """The hook. Zero arguments, so Arcron can call it with only the selector.

        Returns what it did, which is often nothing — and nothing is fine.
        """
        # Arcron's inner call comes from the keeper application's account.
        # Application(id).address is the check. Do not encode the id as bytes.
        assert (
            Txn.sender == Application(self.keeper_app.value).address
        ), "Only the keeper app may run this"

        # Cheap no-op, and a return rather than an assert. A hook that
        # fails trips keeper backoff and stops being serviced.
        if self.pending.value == 0:
            return UInt64(0)

        done: UInt64 = self.pending.value
        self.pending.value = UInt64(0)
        self.work_done.value += done
        self.last_run_round.value = Global.round
        return done
