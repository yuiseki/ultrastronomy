# Contributing

Three kinds of contribution are welcome, in this order of usefulness.

## 1. A run

Follow `AGENTS.md` with your own agent, or by hand. When `uv run ultra gates runs/<name>` passes:

```sh
uv run ultra export runs/<name>
git checkout -b run/<name>
git add contributions/<name>
git commit -m "Add run <name>"
```

Open a pull request. The record holds the plan, its lock, the log, the provenance, the computed results, the measured text, the claims and the report. It holds no raw data, and nothing about you beyond what you wrote in it.

A lock on your own disk proves nothing to anyone else. If you want the order of events to be checkable, commit `plan.json` and `plan.lock` and push them before you run `ultra fetch`; the history of the pull request then shows that the plan came first. This is optional, and it is the only way the lock becomes more than your word.

A run whose claim was rejected or undecided is as welcome as one that was supported. So is a run that stopped early and says why.

A reviewer runs `uv run ultra verify contributions/<name> --refetch --confirm`, which downloads the record's objects again, recomputes everything and compares, and then reads the two free-text sections of the report. A record that cannot be recomputed is not merged.

## 2. A failure of the harness or a skill

If an agent got lost following a skill, or the gates passed something they should have stopped, open an issue with: what was asked, what the agent did, which instruction or gate was involved. A reproduction as a test is better still.

A gate that let a wrong record through is fixed by tightening the gate and adding the case to `tests/`, not by fixing that one record.

## 3. A mission

A mission needs four things before any code: a list of known objects with a licence that allows copying it, a public data source with terms that allow this use, a screen taken from published criteria, and a statement of how the known objects were selected. Open an issue with those first.

## Ground rules

- Tests first for anything that computes a number. `uv run pytest` must pass.
- No raw survey data in the repository. Each run fetches its own.
- No secrets, tokens or personal data, in code or in records.
- Public text is in English.
- Nothing in the repository may state or imply that an object is newly found or confirmed.
