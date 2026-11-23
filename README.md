# ultrastronomy

An open-source harness and skill collection that lets anyone contribute to astronomy with the AI agent they already use, and keeps that agent from overclaiming.

SETI@home put idle computers to work on a search. ultrastronomy is for idle AI usage: point your agent at this repository, give it a budget, and it carries out a small, checkable piece of research on public sky data and leaves a record others can verify.

It is early. There is one mission, and it looks for nothing new.

## What a run does

Astronomers went back through six years of the Zwicky Transient Facility's alerts and reported 23 objects that had been overlooked. The first mission asks: with a simple fixed screen, how many of those would be kept, and how much of everything else would be kept with them?

Each run samples different weeks of the archive. Pooled, the runs measure the screen. A search that has been measured on known objects is the starting point for any later search for unknown ones.

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

The agent asks for your budget, writes a plan, locks it, fetches about 70 small requests from the Fink broker's public API, and reports back. You can also do every step by hand: `uv run ultra status runs/<name>` always names the next command.

## What your agent can and cannot do

It can run the mission, explain what the numbers mean, and write up what was measured, what it inferred, and what nobody checked.

It cannot choose the verdict, change the plan after seeing data, type a number that the program did not compute, or describe an object as newly found. Those are refused in code, not by instruction: see [docs/design.md](docs/design.md).

## How results are validated

- The plan (claim, threshold, comparison) is hashed before any data is read.
- The program computes every number and applies the decision rule.
- Each statement in a record is labelled measured, inferred or unverified. Measured statements must match the computed results.
- Sensitivity is measured by injecting synthetic flares and counting how many pass.
- A record carries the source, time and hash of every object used, so anyone can recompute it.
- `supported`, `rejected` and `undecided` are all results. A run that finds the screen does not work is kept.

"An AI found something" and "a finding was confirmed" are different statements. Nothing in this repository makes the second one.

## Contribute

When the gates pass, `uv run ultra export runs/<name>` copies the record (no raw data) into `contributions/`, ready for a pull request. Reports of a skill that confused an agent, or of a gate that let something through, are as useful as runs. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Relation to Claudestronomy

[Claudestronomy](https://claudestronomy.com/) is a grants programme and community for people using AI agents on public sky data. ultrastronomy shares its aims and adopts the scientific practices it lists; [docs/design.md](docs/design.md) maps them one by one. ultrastronomy is an independent project. It is not affiliated with, endorsed by or sponsored by Claudestronomy, macrogrants, or any AI provider.

## Status

- Agents: exercised with Claude Code subagents only. The skills follow the [Agent Skills specification](https://agentskills.io/specification) and the entry point is a plain `AGENTS.md`, but Codex, Gemini CLI and OpenCode have not been tried.
- Missions: one.
- Injection: uses a simplified model of when ZTF observes, not the real schedule.
- Data: nothing from ZTF is redistributed here. Each run fetches its own from Fink.

What was measured about the harness and the skills themselves is in [evals/README.md](evals/README.md).

## Licence

Apache-2.0. The list of known objects is from Quintin et al. (2026), arXiv:2511.19016, CC BY 4.0.
