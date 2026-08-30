# arcron-quickstart

A ten-minute first-party Arcron TestNet demo: one tiny target, one registration on keeper [`769891898`](https://testnet.explorer.perawallet.app/application/769891898), one observed execute.

## Live proof

**Not done.** This repository ships the path. It has not been run against TestNet, so there is no app id, no upkeep id, and no execute txid. Do not invent one. The table is the verification bar; three of four items are not done, and the clock was not started.

| Item | Status |
| --- | --- |
| Tiny target contract | Source: [`contracts/minimal_target.py`](contracts/minimal_target.py). Live TestNet app id: **not done**. |
| Registration on keeper [769891898](https://testnet.explorer.perawallet.app/application/769891898) | **Not done.** No upkeep id. |
| Observed execute | **Not done.** No txid, no round. |
| Elapsed time | **Not timed.** The clock starts when the TestNet steps actually run. |

The keeper itself is live on TestNet: app [`769891898`](https://testnet.explorer.perawallet.app/application/769891898) (unaudited, `frozen=0`). This demo has not yet registered anything on it.

## How to run (under ten minutes)

TestNet only. You need a throwaway account with about 0.2 TestNet ALGO (AlgoKit dispenser, not MainNet, not a real mnemonic).

1. Copy `.env.example` to `.env` and set `DEPLOYER_MNEMONIC`. `.env*` is gitignored from commit 1. Do not commit it.
2. `python3.12 -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt -r requirements-dev.txt`
4. Compile the target: `python -m puyapy contracts/minimal_target.py --out-dir artifacts`
5. `python scripts/demo.py` deploys the app, calls `set_keeper` with the keeper application `769891898`, `request_work()`, and registers `run()uint64` on keeper 769891898 with `SKIP_AHEAD`.
6. `python scripts/observe.py` waits until an execute shows up on the indexer and prints the txid and round.

Default cadence is 30 rounds (about a minute and a half) so a keeper can hit it inside the ten minutes. The console walkthrough uses 215 rounds; that is fine too, it just may not finish inside the timed path. Interval floor is 10 rounds. Policy is `SKIP_AHEAD` (1), not `CATCH_UP` (0).

The hook is zero-arg `run()uint64`. Authorization is `Txn.sender == Application(keeper).address`. `set_keeper` takes an `Application`, not a uint64, so the call site cannot confuse interval with keeper id. It is not a create argument and it is not hardcoded in the contract.

## Measured cost

Not measured. We have not signed a register group.

What the Arcron docs *claim* for a similar first upkeep (recompute before you trust it; `docs/first-upkeep.md` has gotten its own arithmetic wrong more than once):

- Box MBR: 0.0621 ALGO for a bare 4-byte selector, refunded in full on cancel.
- Escrow: whatever you fund. The walkthrough suggested 0.03 ALGO (three runs at 0.010).
- Network fees: 0.003 ALGO for the three-transaction register group, gone either way.
- Minimum fee per execution: 0.004 ALGO (`MIN_UPKEEP_FEE`). Below that, register is rejected at validation (`assert failed pc=404`). The console suggests 0.010.
- Rough up-front total in that walkthrough: on the order of 0.1 TestNet ALGO, mostly refundable. START-HERE said ~0.2.

This demo uses fee 0.010 and funding 0.03 unless you change the constants in `scripts/demo.py`.

## What does not work yet

- Live proof is empty: no TestNet deploy, no registration, no observed execute, no timer.
- `scripts/demo.py` has not been executed against live algod. Treat it as the intended path, not a measured one.
- We have not confirmed that a CorvidLabs keeper will pick up a brand-new registration inside ten minutes.
- GitHub Pages is the same honest not-done table. It 404s until the Pages workflow has run once.
- Compiling needs `puyapy` (`algorand-python`). If the compile CLI flag in CI is wrong, that job is the bug report.

## Honesty

- **Unaudited.** Keeper [`769891898`](https://testnet.explorer.perawallet.app/application/769891898) is alpha, TestNet only, and `frozen=0` (upgradeable). The creator can replace the programs.
- **No MainNet.** There is no MainNet deployment. This repo's endpoints are TestNet. Do not point it at MainNet.
- **First-party.** This is a CorvidLabs demo of our own keeper. START-HERE.md said nobody outside CorvidLabs had registered an upkeep. Shipping this repo does not change that, and we will not pretend it does.
- **Every keeper running is still ours.** Permissionless is true architecturally and currently false empirically.
- Throwaway dispenser account only. Mnemonics never go in git.
