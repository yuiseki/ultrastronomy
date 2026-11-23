# ultrastronomy

An open-source harness and skill collection that lets anyone contribute to astronomy with the AI agent they already use, and makes that agent's work checkable by someone else.

SETI@home put idle computers to work on a search. ultrastronomy is for idle AI usage: point your agent at this repository, give it a budget, and it carries out a small, checkable piece of research on public sky data and leaves a record others can verify.

It is early. There is one mission, and it looks for nothing new.

## What a run does

Astronomers went back through six years of the Zwicky Transient Facility's alerts and reported 23 objects that had been overlooked. The first mission asks: with a simple fixed screen, how many of those would be kept, and how much of everything else would be kept with them?

Each run samples different weeks of the archive. Pooled, the runs measure how much of everything else the screen lets through. The known objects are the same in every run, so that side is measured once. A search that has been measured on known objects is the starting point for any later search for unknown ones.

## Start

You need Python 3.11 or later, [uv](https://docs.astral.sh/uv/), and git.

```sh
git clone https://github.com/yuiseki/ultrastronomy
cd ultrastronomy
uv run ultra demo
```

The demo runs the whole pipeline on synthetic light curves, offline, in a few seconds. It prints a table, a verdict, a sensitivity curve and the result of every gate.

For a real run, open your agent in this directory and say:

> Read AGENTS.md and take me through an ultrastronomy run. My budget is 30 minutes.

The agent writes a plan, locks it, makes about 110 small requests to the Fink broker's public API (roughly eight minutes), and reports back. You can also do every step by hand: `uv run ultra status runs/<name>` always names the next command.

## What your agent can and cannot do

It can run the mission, explain what the numbers mean, and write down what it infers and what nobody checked.

The harness is built so that an agent following the steps cannot get these wrong by accident: the verdict is computed by the program, the plan is hashed before data is read, the measured part of the report is text the program wrote, and the gates recompute every number from the data before a record can be exported.

The harness does not make a record trustworthy on its own. Files on a participant's machine can be edited by hand, a plan can be re-made after a peek at cached data, and a misleading sentence can be written without tripping the wording check. A record counts once someone else has recomputed it from data they downloaded themselves, which is one command: `uv run ultra verify contributions/<name> --refetch --confirm`. See [docs/design.md](docs/design.md) for what is enforced and what is not.

## How results are validated

- The plan (claim, threshold, comparison) is hashed, with the code and the mission files, before any data is read.
- The program computes every number and applies the decision rule. With fewer than 10 objects on a side it gives no verdict.
- The measured section of a report is generated. The agent's sentences are labelled inferred or unverified and kept in their own sections.
- Synthetic flares are injected and counted, on a made-up observing schedule: a check of where the criteria stop working on clean data, not of sensitivity on the real sky.
- A record carries the source, time and hash of every object used. Alerts are cut at a fixed date so that a later download gives the same rows.
- A pull request that adds a record is re-downloaded and recomputed by CI, using the code of the main branch and not the code in the pull request.
- `supported`, `rejected` and `undecided` are all results. A run that finds the screen does not work is kept.

"An AI found something" and "a finding was confirmed" are different statements. Nothing in this repository makes the second one.

## Where it stands

[RESULTS.md](RESULTS.md) is generated from the contributed records and cannot be edited by hand without a test failing. Today it says two things. The screen keeps about three quarters of the known objects and almost none of the bulk of the alert stream. And two catalogue flags about the host galaxy do that just as well as the full screen: the light-curve criteria add nothing this sample can show. The first mission has mostly measured its own screen and found it wanting, which is what a rediscovery test is for.

## Contribute

When the gates pass, `uv run ultra export runs/<name>` copies the record (no raw data) into `contributions/`. Sharing it as a pull request is your decision, not the agent's. Reports of a skill that confused an agent, or of a gate that let something through, are as useful as runs. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Relation to Claudestronomy

[Claudestronomy](https://claudestronomy.com/) is a grants programme and community for people using AI agents on public sky data. ultrastronomy shares its aims and adopts the scientific practices it lists; [docs/design.md](docs/design.md) maps them one by one. ultrastronomy is an independent project. It is not affiliated with, endorsed by or sponsored by Claudestronomy, macrogrants, or any AI provider.

## Status

- Review: an independent agent got 24 of 31 tampered records through the first version of the gates, and a free model then got 9 of 10 through the rebuilt version. Each case is now a test, and the gates have not been attacked since. What a determined forger can still do is listed in [docs/design.md](docs/design.md).
- Agents: a full run has been completed by a Claude Code subagent and by OpenCode with a free model, once each. Codex and Gemini CLI have not been tried. The skills follow the [Agent Skills specification](https://agentskills.io/specification) and the entry point is a plain `AGENTS.md`. `CLAUDE.md` and `.claude/skills` only point Claude Code at `AGENTS.md` and `.agents/skills`; they hold nothing of their own.
- Missions: one.
- Injection: uses a simplified model of when ZTF observes, not the real schedule, and ideal hosts.
- Screen: version 1 has known weaknesses, listed in `src/ultrastronomy/score.py`, and its thresholds have not been checked against the paper they are modelled on.
- Data: nothing from ZTF is redistributed here. Each run fetches its own from Fink.

What was measured about the harness and the skills themselves is in [evals/README.md](evals/README.md).

## Licence

Apache-2.0. The list of known objects is from Quintin et al. (2026), arXiv:2511.19016, CC BY 4.0.
