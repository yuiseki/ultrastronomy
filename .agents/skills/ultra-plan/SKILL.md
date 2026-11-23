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

Do not open cached light curves (anything under `.cache/`), `results.json` of this run, or any data file before the lock. The demo's output is synthetic and may be looked at; mention it in `seen_before_lock`.

Leave `mission`, `kind` and `data.source` as `ultra init` wrote them.

## The fields

| Field | What to write |
|---|---|
| `claim` | One sentence that numbers can contradict. "At score >= T, the known nuclear transients pass more often than the S stratum." |
| `decision_rule.threshold` | The level at which you compare; the mission README says what it is and its range. Higher keeps fewer objects on both sides |
| `decision_rule.primary_stratum` | The background group you compare against, one of the mission's `strata` |
| `rationale` | Why this threshold and this stratum. If you copied them from an earlier run, say so |
| `failure_interpretation` | What it means if the claim is rejected, and which changes you will not make to rescue it |
| `alternative_explanations` | Reasons the claim could come out supported while being wrong. See below |
| `seen_before_lock` | Everything you had read or been told about results before locking. "Nothing" is a valid answer only if true |
| `ai_budget` | The person's limit, in their words. Already filled in by `ultra init` |
| `data.seed` | Any integer, picked without looking at data: a random number is best. It decides which weeks of the archive your run samples. Avoid seeds already used: those in `contributions/*/plan.json`, and 20261123 from the mission README |
| the other `data` fields | How much to sample: `weeks` and `per_class`, or `patches` and `per_stratum`, depending on the mission. The defaults are a small run. Below 10 objects on either side of the comparison the rule gives no verdict |
| `data.max_requests` | The most network requests this run may make, over all attempts. `ultra lock` refuses a plan that cannot fit and says how many it needs |

The rule is applied by the program to the difference in pass rates, positives minus background: `supported` if its 95% interval lies above zero, `rejected` if the interval lies below zero, `undecided` if it contains zero or either side has fewer than 10 objects. Seeing no difference is `undecided`, not `rejected`. You do not get to choose the verdict.

## Other explanations to consider

Write the ones that apply to this run. Leave out the ones that do not.

- Circularity: the known objects were chosen by a classifier and by eye for looking like this, and the threshold used by earlier runs was picked after their scores had been seen. The positive side is the same 19 objects in every run. A new run repeats the background side only; it is not an independent replication of the recall.
- Observation effort: the number of detections and the duration depend on how often that field was observed, not only on the object.
- Sampling: a stratum is drawn from the last 3,000 alerts of its class in the sampled week. For a busy class that is the tail of one night, not a week. Objects that alert often are over-represented.
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
  "alternative_explanations": ["Circularity: the known objects were selected for looking TDE-like and the threshold was chosen after seeing their scores; this run repeats only the background side.", "Chance: 12 background objects per stratum."],
  "seen_before_lock": "The mission README, including the first run's table. No data of this run."
}
```
