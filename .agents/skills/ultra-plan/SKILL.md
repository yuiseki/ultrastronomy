---
name: ultra-plan
description: Write and lock the plan of an ultrastronomy run before any data is read - the claim, the decision rule, what a bad result would mean, and the other explanations for a good one. Use when filling in plan.json, when `ultra lock` refuses a plan, when choosing a threshold or a seed, or when tempted to change a plan after seeing results.
license: Apache-2.0
---

# ultra-plan

After results are in, any outcome can be explained. The plan is written first so that the result can disagree with you.

## When to use

Step 2 of `ultra-rediscovery-run`: `runs/<name>/plan.json` exists and is empty.

## Inputs

- `missions/<mission>/mission.json`: the question, the strata, where the known objects come from.
- `missions/<mission>/README.md`: what earlier runs found. You may read it. Say so in `seen_before_lock`.

Do not open cached light curves, `results.json` of this run, or any data file before the lock.

## The fields

| Field | What to write |
|---|---|
| `claim` | One sentence that numbers can contradict. "At score >= T, the known nuclear transients pass more often than the S stratum." |
| `decision_rule.threshold` | The score, 1 to 6, at which you compare. Higher keeps fewer objects on both sides |
| `decision_rule.primary_stratum` | The background class you compare against. `Unknown` is most of the real alert stream |
| `rationale` | Why this threshold and this stratum. If you copied them from an earlier run, say so |
| `failure_interpretation` | What it means if the claim is rejected, and which changes you will not make to rescue it |
| `alternative_explanations` | Reasons the claim could come out supported while being wrong. See below |
| `seen_before_lock` | Everything you had read or been told about results before locking. "Nothing" is a valid answer only if true |
| `ai_budget` | The person's limit, in their words. Already filled in by `ultra init` |
| `data.seed` | An integer you choose. It picks which weeks of the archive your run samples. Do not reuse a seed from `contributions/` |
| `data.weeks`, `data.per_class` | How many random weeks, and how many objects per class and week. 3 and 2 is a small run |
| `data.max_requests` | The most network requests this run may make |

The rule is applied by the program: `supported` if the 95% interval of the difference in pass rates lies above zero, `rejected` if the difference is zero or negative, `undecided` otherwise. You do not get to choose the verdict.

## Other explanations to consider

Write the ones that apply to this run. Leave out the ones that do not.

- Circularity: the known objects were chosen by a classifier and by eye for looking like this. A screen for the same look passes them by construction.
- Observation effort: the number of detections and the duration depend on how often that field was observed, not only on the object.
- Sampling: the background is drawn from objects that alerted in a given week, so objects that alert often are over-represented.
- Chance: a run has few known objects and a small background sample.
- Label drift: a class label may stop being used partway through the archive, so a stratum covers only part of the period.

## Success

`uv run ultra lock runs/<name>` prints a timestamp. If it refuses, it lists every field that is not ready.

## Verification

After the lock, `uv run ultra status runs/<name>` shows "done: lock the plan". Read your `seen_before_lock` once more: if it leaves out something you had seen, the run is not a confirmation. Start a new run and say so.

## Typical failures

- A claim with no number in it ("the screen works").
- A threshold chosen because an earlier table looked best at that value, with `seen_before_lock` left as "Nothing".
- Editing `plan.json` after the lock. Every later command will refuse the run. Start a new run.

## Example

```json
{
  "claim": "At score >= 5, the known nuclear transients pass more often than objects in the Unknown stratum.",
  "decision_rule": {"threshold": 5, "primary_stratum": "Unknown"},
  "rationale": "Same rule as the first run in missions/ztf-nuclear-transients/README.md, to replicate it on a new sample.",
  "failure_interpretation": "On this sample the screen does not separate them. I will not change the threshold, the stratum or the seed to recover the claim.",
  "alternative_explanations": ["Circularity: the known objects were selected for looking TDE-like.", "Chance: 6 background objects per stratum."],
  "seen_before_lock": "The mission README, including the first run's table. No data of this run."
}
```
