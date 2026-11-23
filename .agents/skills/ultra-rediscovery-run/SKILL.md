---
name: ultra-rediscovery-run
description: Carry out one ultrastronomy run from start to shared record - re-find known astronomical objects in public ZTF alert data with a fixed screen, measure how much of the alert stream passes the same screen, and record it so others can check it. Use when a person asks to take part in ultrastronomy, to run a mission, to spend spare AI usage on astronomy, or to replicate a rediscovery result. Start here before any other ultrastronomy skill.
license: Apache-2.0
compatibility: Requires Python 3.11+, uv, and network access to api.ztf.fink-portal.org for real runs. The demo runs offline.
---

# ultra-rediscovery-run

One run answers one question: with this fixed screen, what share of the known objects pass, and what share of everything else passes too? A run does not look for anything new.

## When to use

A person wants to contribute a run, or wants to see what ultrastronomy does. No astronomy knowledge is assumed, of them or of you.

## Before you start

1. Ask the person for a budget, in their words: how long, or how many steps, and when to stop. Write it down exactly. Do not estimate how much AI usage is left; you cannot see it.
2. Run `uv run ultra demo`. It needs no network. If it fails, stop and report the error. Do not go on to real data with a broken pipeline.

## Steps

Run every command from the repository root. `ultra status runs/<name>` tells you the next step at any time.

| Step | Command | What you do |
|---|---|---|
| 1 | `uv run ultra init <name> --ai-budget "<their words>"` | Pick a short name, such as `2026-11-23-alice` |
| 2 | edit `runs/<name>/plan.json` | Follow the `ultra-plan` skill. Choose your own `data.seed` |
| 3 | `uv run ultra lock runs/<name>` | After this the plan and the scoring code cannot change |
| 4 | `uv run ultra fetch runs/<name>` | Shows the request count. Tell the person, then add `--confirm` |
| 5 | `uv run ultra evaluate runs/<name>` | Prints the table and the verdict of the locked rule |
| 6 | `uv run ultra inject runs/<name>` | Measures how faint a flare can be and still pass |
| 7 | write `claims.json` and `report.md` | Follow the `ultra-report` skill |
| 8 | `uv run ultra gates runs/<name>` | Every gate must pass |
| 9 | `uv run ultra export runs/<name>` | Copies the record to `contributions/` for a pull request |

Read `ultra-alert-photometry` before you interpret any number in step 5 or write step 7.

## What success looks like

- `ultra gates` exits 0.
- The verdict is whatever the locked rule gave: `supported`, `rejected` and `undecided` are all valid results. A rejected claim with a passing record is a contribution.
- The person can say, in one sentence, what was measured and what was not.

## Typical failures

- Looking at the data first and writing the plan afterwards. The harness refuses to fetch before the lock, but a cache from an earlier run may be on disk. Do not open it.
- Changing the threshold, the stratum or the seed after seeing the table, to get a nicer verdict. Start a new run instead and say in its plan what you had already seen.
- Treating a failed fetch as an empty result. A week with no observations and a network error are different things; the log says which.
- Going past the budget. When the budget is reached, stop, write what is done, and say what the next step would be.

## Verification

`uv run ultra gates runs/<name>` re-checks the record. Anyone with the repository can re-run `evaluate` on the same provenance and must get the same numbers.

## Example

```sh
uv run ultra demo
uv run ultra init 2026-11-23-alice --ai-budget "30 minutes, stop after the gates"
# edit runs/2026-11-23-alice/plan.json
uv run ultra lock runs/2026-11-23-alice
uv run ultra fetch runs/2026-11-23-alice --confirm
uv run ultra evaluate runs/2026-11-23-alice
uv run ultra inject runs/2026-11-23-alice
# write claims.json and report.md
uv run ultra gates runs/2026-11-23-alice
uv run ultra export runs/2026-11-23-alice
```
