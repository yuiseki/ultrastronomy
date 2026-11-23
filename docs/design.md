# Design

## Purpose

Let a person with an AI agent and some spare usage do a small piece of astronomy that someone else can check, without needing to know astronomy and without the agent overclaiming.

## Non-goals

- Finding new objects. The first mission only re-finds known ones.
- A central server, accounts, a job scheduler, or a layer over AI providers. A participant uses the agent they already have.
- Moving or pooling usage limits or credits between people. Providers' terms decide that, not this project.
- Classifying objects. The screen ranks; classification needs spectra and people.
- A new detection algorithm. The screen is taken from published criteria.

## Architecture

Three parts, each replaceable.

| Part | Where | Job |
|---|---|---|
| Harness | `src/ultrastronomy/`, the `ultra` command | Fetch within a budget, compute, decide, record, refuse |
| Skills | `.agents/skills/` | Tell an agent what to do next and what the numbers mean |
| Missions | `missions/` | A question, a list of known objects, strata, and what earlier runs found |

Everything is local files. A run is a directory; a contribution is a copy of that directory without raw data, sent as a pull request.

The harness has one dependency (numpy) and uses the standard library for the network.

## How the harness keeps an agent from being wrong

Each line is a mechanism in code, with a test in `tests/test_harness.py`. None of them relies on the agent choosing to behave.

| Risk | Mechanism |
|---|---|
| The plan is fitted to the result | `ultra fetch`, `evaluate` and `inject` refuse to run until `ultra lock` has hashed the plan. A changed plan fails every later command |
| The scoring code is changed after the fact | The lock also hashes `score.py` and `lightcurve.py` |
| The verdict is chosen by the agent | The program applies the locked rule. A gate recomputes the verdict from the stored counts |
| A number is typed or misremembered | A `measured` claim must point into `results.json`, and its value must equal what is there |
| A guess is presented as a measurement | Every claim is labelled `measured`, `inferred` or `unverified`; the report needs the three sections |
| A later classification leaks into the screen | Only allow-listed alert columns are ever requested from the API |
| Data changes or cannot be traced | Every object has a provenance record with source, time and content hash; changed content is refused |
| A known object is quietly dropped | A gate requires every known object of the mission to be scored |
| Sensitivity is never measured | A gate requires an injection and recovery table at the locked threshold |
| A candidate is announced | A gate rejects announcement wording; synthetic runs cannot be exported; no command publishes anything |
| The data API is overused | A request count is shown before fetching, `--confirm` is required, and a hard budget stops the run |
| AI usage runs away | The person's limit is recorded in the plan in their words. The harness cannot see usage and never reports it |

What the harness cannot do: stop an agent from reading a cache file outside the harness before locking, or from writing a misleading sentence that avoids the listed words. The plan's `seen_before_lock` field and the report's "Not verified" section are where honesty is asked for; a reviewer reads them.

## How this follows Claudestronomy's stated practices

Claudestronomy (https://claudestronomy.com/) lists six things it cares about. ultrastronomy is independent of it and is not endorsed by it; it adopts the same practices.

| Practice | Here |
|---|---|
| Recover known objects in the same data before trusting a search | The whole first mission |
| Inject synthetic sources, measure recovery, calibrate false positives separately | `ultra inject` for recovery; the background strata for the pass rate of everything else. The injection uses a model cadence, not real epochs |
| Write down thresholds and predictions before new data arrives; document later changes | `ultra lock`; a change means a new run |
| Have a fresh agent session challenge the analysis | A contribution is re-run from its provenance by a reviewer. `evals/` records what fresh agents did with and without the harness |
| Publish code, methods and results; say what has not been ruled out | Records in `contributions/`; the "Not verified" section |
| Publish useful null results with sensitivity and coverage | `rejected` and `undecided` runs are merged like any other, with their injection table |

## MVP

See the acceptance criteria in `INITIAL_PROMPT.md`. Which are met, and how that was checked, is in `evals/README.md`.
