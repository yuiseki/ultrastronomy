# Design

## Purpose

Let a person with an AI agent and some spare usage do a small piece of astronomy that someone else can check, without needing to know astronomy and without the agent overclaiming.

## Non-goals

- Finding new objects. The first mission only re-finds known ones.
- A central server, accounts, a job scheduler, or a layer over AI providers. A participant uses the agent they already have.
- Moving or pooling usage limits or credits between people. Providers' terms decide that, not this project.
- Classifying objects. The screen ranks; classification needs spectra and people.
- A new detection algorithm. The screen is modelled on published criteria.
- Security against a participant who forges a record. See "What is not enforced".

## Architecture

Three parts, each replaceable.

| Part | Where | Job |
|---|---|---|
| Harness | `src/ultrastronomy/`, the `ultra` command | Fetch within a budget, compute, decide, record, recompute, refuse |
| Skills | `.agents/skills/` | Tell an agent what to do next and what the numbers mean |
| Missions | `missions/` | A question, a list of known objects, strata, and what earlier runs found |

Everything is local files. A run is a directory; a contribution is a copy of that directory without raw data. The harness has one dependency (numpy) and uses the standard library for the network.

## Who the harness protects against

An agent, or a person, who is trying to do the work properly and makes the usual mistakes: deciding the comparison after seeing the result, misreading a column, typing a number from memory, dropping an inconvenient object, describing a pass as a find.

It is not built to stop someone who sets out to deceive. Everything lives in files on their own machine. That is what review is for.

## What is enforced, and how

Each line is a mechanism in code with a test in `tests/test_harness.py`.

| Risk | Mechanism |
|---|---|
| The comparison is chosen after seeing results | `fetch` and `evaluate` refuse to run until `lock` has hashed the plan. A changed plan fails every later command |
| The code or the mission is changed after the fact | The lock hashes every module of the package and the mission's files, and records the git commit. The modules that compute, and the mission files, must still match; the gates and the command line may change without invalidating a record |
| The verdict is chosen by the agent | The program applies the locked rule |
| A stored number is wrong, edited or invented | The gates do not read the stored results as truth: they recompute them from the data and the locked plan and require equality, including the injection table |
| A number is typed or misremembered in the report | The `## Measured` section, and `measured.md`, must equal the text the program generated. Nothing but a title may precede the section, and HTML is not allowed |
| A true number is put under a false sentence | The agent cannot write measured statements at all; its claims are `inferred` or `unverified`, each with a basis |
| A guess about one object is slipped in as a reading of the results | Object identifiers are not allowed in `## Inferred` or in an inferred claim, with formatting removed before matching |
| A later classification leaks into the screen | Only allow-listed alert columns are requested, and the gates check the columns present in the data |
| Data changed, or is not the data the record names | Every object has a source, a time and a content hash. Without the data on the machine the record is reported as not verified, not as passing |
| A known object is dropped or relabelled, a stratum is left out, an object is counted twice | The list of objects, their roles and their labels is derived again from the locked plan, the mission and the sampled weeks, and must equal the provenance |
| A verdict on almost no data | Fewer than 10 objects on either side gives `undecided` |
| No difference read as a rejection | `rejected` needs the interval below zero |
| The data API is overused | The request count is shown first, `--confirm` is required, and a budget that adds up over attempts stops the run |
| AI usage runs away | The person's limit is recorded in the plan in their words. The harness cannot see usage and never reports it |

## What is not enforced

Stated plainly, because the first version of this document claimed more than the code did, and two independent reviews showed it (see `evals/README.md`). The table above is what the tests cover today. It has been wrong twice.

- The lock is a file. Someone can delete it, change the plan and lock again. The log records two locks and the gate catches that, but the log is a file too. The ordering is only as trustworthy as the place it is published: commit the locked plan before fetching, and the commit history of the pull request shows the order.
- Data can be read before the lock, by opening the cache or by calling the functions directly, and several seeds can be tried before one is locked. `seen_before_lock` is a declaration.
- A cache can be filled with invented light curves, and a run on it passes the local gates. Only a re-download catches it: `ultra verify --refetch`.
- The wording check is a lint. It flags common announcement words, fails honest denials that use the same words, and can be evaded by rephrasing.
- Sentences in `## Inferred` and `## Not verified` are free text. They can be wrong, and can contain numbers nobody compared with anything.
- `ultra pool` trusts the records in `contributions/`. They get there through review.

## Review

A contribution is a pull request. The reviewer runs:

```sh
uv run ultra verify contributions/<name> --refetch --confirm
```

That downloads the sampled weeks and every object in the record's provenance again, derives the sample, checks the hashes, recomputes the results and the measured text, and runs the remaining gates. Then the reviewer reads the two free-text sections. A record that cannot be recomputed is not merged.

Alerts are cut at the mission's `alerts_until` date and sorted before hashing, so that an object which kept alerting gives the same rows later. If Fink reprocesses its archive the hashes will change; the gate reports that as a mismatch, and the record then needs a new run.

## How this follows Claudestronomy's stated practices

Claudestronomy (https://claudestronomy.com/) lists six things it cares about. ultrastronomy is independent of it and is not endorsed by it; it adopts the same practices.

| Practice | Here | How far |
|---|---|---|
| Recover known objects in the same data before trusting a search | The whole first mission | Done, on objects that were selected for looking like the screen |
| Inject synthetic sources, measure recovery, calibrate false positives separately | The injection table; the background strata | Injection is on a model schedule with ideal hosts, not on real epochs. Background pass rates are per class, not weighted to the real stream |
| Write down thresholds and predictions before new data arrives; document later changes | `ultra lock`; a change means a new run | Enforced locally; anchored only if the plan is committed first |
| Have a fresh agent session challenge the analysis | `ultra verify --refetch` by a reviewer; `evals/` records what fresh agents did | The review that reshaped the gates was one agent, once |
| Publish code, methods and results; say what has not been ruled out | Records in `contributions/`; the "Not verified" section | Done |
| Publish useful null results with sensitivity and coverage | `rejected` and `undecided` runs are merged like any other | Coverage is stated as weeks and classes sampled, not as a completeness curve on the sky |

## MVP

The acceptance criteria are in `INITIAL_PROMPT.md`. Which are met, and how that was checked, is in `evals/README.md`.
