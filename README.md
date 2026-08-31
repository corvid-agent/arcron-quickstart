# arcron-quickstart

A ten-minute first-party Arcron TestNet demo: one tiny target, one registration on keeper [`769891898`](https://testnet.explorer.perawallet.app/application/769891898), one observed execute.

## Live proof

**Not done.** CRT board: <https://corvid-agent.github.io/arcron-quickstart/> — headline **NOT DEPLOYED**, `docs/deploy.json` has `"appId": 0` and empty `executeTxid`. Do not invent one.

| Item | Status |
| --- | --- |
| Tiny target contract | Source: [`contracts/minimal_target.py`](contracts/minimal_target.py). Live TestNet app id: **not done** (`appId` 0). |
| Registration on keeper [769891898](https://testnet.explorer.perawallet.app/application/769891898) | **Not done.** No upkeep id. |
| Observed execute | **Not done.** No txid, no round. |
| Elapsed time | **Not timed.** The clock starts when the TestNet steps actually run. |

The keeper itself is live on TestNet: app [`769891898`](https://testnet.explorer.perawallet.app/application/769891898) (unaudited, `frozen=0`). This demo has not registered anything on it.

## How to run (under ten minutes)

TestNet only. Throwaway dispenser account, about 0.2 TestNet ALGO. No MainNet. No mnemonic in git (`.env*` is gitignored from commit 1).

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Same compile CI runs. puyapy writes teal next to the source
# (contracts/MinimalTarget.approval.teal). Do not pass --out-dir.
python -m puyapy contracts/minimal_target.py
```

Create with **zero args**. Do not pass `769891898`, an interval, or anything else at create. Mapping every uint64 create-arg onto the keeper id is how a cadence gets frozen; this `__init__` takes nothing so that cannot happen here.

Then, still as creator, name the keeper as an **application**, not a uint64 and not `itob`:

```text
set_keeper(Application(769891898))
```

Hook auth is `Txn.sender == Application(keeper).address`. Then `request_work()`, then register `run()uint64` on keeper 769891898 with `SKIP_AHEAD` (1), interval 30 rounds, fee 0.010 ALGO, funding 0.03 ALGO. Interval floor is 10 rounds. Do not pass `CATCH_UP` (0) by accident.

`python scripts/demo.py` is that sequence (compile, create with empty `app_args`, `set_keeper(application)`, `request_work`, register). It has **not** been run against live algod. `python scripts/observe.py` waits for an execute and prints the txid and round. If none arrives, that is not done — do not invent a txid.

After a real create, write the app id into `docs/deploy.json` (`appId`, still `"network": "testnet"`). The CRT stays **NOT DEPLOYED** while `appId` is 0.

## LocalNet recreate (not TestNet)

Create, `set_keeper(Application(...))`, and a mock-keeper inner-call of `run()` were proven on AlgoKit LocalNet (`dockernet-v1`). That is **not** TestNet. Do **not** copy any LocalNet app id into `docs/deploy.json` or Pages. `appId` stays 0 until a real TestNet create.

LocalNet ids are ephemeral (DevMode / reset). They are not a product and they are not for GitHub Pages.
LocalNet proof for Pages lives in `docs/localnet.json` (CRT shows it when present). `docs/deploy.json` stays honest TestNet `appId: 0`.

```bash
# Docker daemon required
algokit localnet start
# wait until localhost:4001 /v2/status answers

pip install puyapy py-algorand-sdk
python scripts/localnet_recreate.py
# writes docs/localnet.json with network:"localnet" and the new appId
```

The script talks only to `localhost:4001` / `4002`, signs with the LocalNet KMD
`unencrypted-default-wallet` (never prints a mnemonic), refuses TestNet/MainNet
genesis ids, and never modifies `docs/deploy.json`.

DevMode holds last-round at 0 until the first tx. A successful create is a confirmed
`application-index` on genesis id `dockernet-v1`, not a TestNet explorer link.


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

- Live proof is empty: no TestNet deploy, no registration, no observed execute, no timer. CRT `appId` is 0.
- `scripts/demo.py` has not been executed against live algod. Treat it as the intended path, not a measured one.
- TestNet dispenser requires a Google login, which blocked a live create from this environment.
- We have not confirmed that a CorvidLabs keeper will pick up a brand-new registration inside ten minutes.

## Honesty

- **Unaudited.** Keeper [`769891898`](https://testnet.explorer.perawallet.app/application/769891898) is alpha, TestNet only, and `frozen=0` (upgradeable). The creator can replace the programs.
- **No MainNet.** There is no MainNet deployment. This repo's endpoints are TestNet. Do not point it at MainNet.
- **First-party.** This is a CorvidLabs demo of our own keeper. START-HERE.md said nobody outside CorvidLabs had registered an upkeep. Shipping this repo does not change that, and we will not pretend it does.
- **Every keeper running is still ours.** Permissionless is true architecturally and currently false empirically.
- Throwaway dispenser account only. Mnemonics never go in git.
