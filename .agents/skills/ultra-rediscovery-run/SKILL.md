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

1. Get the person's budget, in their words: how long, or how many steps, and when to stop. If they already gave one, use it as written and do not ask again. Measure time by the clock, waiting included. Do not estimate how much AI usage is left; you cannot see it.
2. Run `uv run ultra demo`. It needs no network. If it fails, stop and report the error. Do not go on to real data with a broken pipeline.

## Steps

Run every command from the repository root. `ultra status runs/<name>` tells you the next step at any time.

| Step | Command | What you do |
|---|---|---|
| 1 | `uv run ultra init <name> --ai-budget "<their words>"` | Pick a short name, such as `2026-11-23-alice` |
| 2 | edit `runs/<name>/plan.json` | Follow the `ultra-plan` skill. Choose your own `data.seed` |
| 3 | `uv run ultra lock runs/<name>` | After this the plan, the code and the mission files cannot change |
| 4 | `uv run ultra fetch runs/<name>` | Shows the request count. Tell the person the number, then add `--confirm`. If they gave their go-ahead in advance, tell them and go on |
| 5 | `uv run ultra evaluate runs/<name>` | Prints the table, the verdict of the locked rule and the injection test, and writes `measured.md` |
| 6 | write `claims.json` and `report.md` | Follow the `ultra-report` skill |
| 7 | `uv run ultra gates runs/<name>` | Recomputes everything. Every gate must pass |
| 8 | `uv run ultra export runs/<name>` | Copies the record, without raw data, to `contributions/` |

Stop after step 8. Committing the record and opening a pull request publish it under the person's name: ask them first.

Read `ultra-alert-photometry` before you interpret any number in step 5 or write step 6.

After step 4, look at the counts per stratum that `fetch` prints. Fewer objects than asked for means some weeks returned nothing for that class. That is a fact about the sample, to be reported, not an error to retry.

## What success looks like

- `ultra gates` exits 0.
- The verdict is whatever the locked rule gave: `supported`, `rejected` and `undecided` are all valid results. A rejected claim with a passing record is a contribution.
- The person can say, in one sentence, what was measured and what was not.

## Typical failures

- Looking at the data first and writing the plan afterwards. The harness refuses to fetch before the lock, but a cache from an earlier run may be on disk. Do not open it.
- Changing the threshold, the stratum or the seed after seeing the table, to get a nicer verdict. Start a new run instead and say in its plan what you had already seen.
- Treating a failed fetch as an empty result. A network error stops `fetch` with exit code 1 and a `fetch_failed` line in `log.jsonl`. A week with no alerts does not: it shows as `"available": 0` in a `sample` line.
- Going past the budget. When the budget is reached, stop, write what is done, and say what the next step would be.

## Verification

`uv run ultra gates runs/<name>` recomputes the results from the data and compares. Someone else checks a shared record with `uv run ultra verify contributions/<name> --refetch --confirm`, which downloads the same objects again. Alerts are cut at a fixed date so that a later download gives the same rows; if Fink reprocesses its archive the hashes will differ, and the gate says so.

## Example

```sh
uv run ultra demo
uv run ultra init 2026-11-23-alice --ai-budget "30 minutes, stop after the gates"
# edit runs/2026-11-23-alice/plan.json
uv run ultra lock runs/2026-11-23-alice
uv run ultra fetch runs/2026-11-23-alice --confirm
uv run ultra evaluate runs/2026-11-23-alice
# write claims.json and report.md
uv run ultra gates runs/2026-11-23-alice
uv run ultra export runs/2026-11-23-alice
```
