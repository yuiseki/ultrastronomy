---
name: ultra-report
description: Write the claims and the report of an ultrastronomy run so that measured numbers, inferences and unchecked statements stay apart, pass the gates, and share the record. Use when writing claims.json or report.md, when `ultra gates` fails, when wording a result for a person, or before exporting a run or telling anyone about a candidate.
license: Apache-2.0
---

# ultra-report

The program computes; you describe. Every statement you make carries one of three labels, and the gates check that you kept them apart.

## When to use

Steps 7 to 9 of `ultra-rediscovery-run`: `results.json` exists, with the injection section.

## The three kinds

| Kind | Meaning | What the gate requires |
|---|---|---|
| `measured` | A number or verdict the program computed | `evidence`: a path into `results.json`. `value`: must equal what is there |
| `inferred` | Your reading of the measured numbers | `basis`: which numbers, and the reasoning |
| `unverified` | Not checked by anything in this run | `basis`: why it is not checked, or what would check it |

Never type a number from memory or from the terminal into a `measured` claim. Copy the path, and let the gate compare.

## Steps

1. Write `runs/<name>/claims.json`: a list of claims. Include at least the verdict.
2. Write `runs/<name>/report.md` with these three headings, exactly: `## Measured`, `## Inferred`, `## Not verified`.
3. Tell the person, in plain words: what was looked for, what the table says, what was not checked, what a next run could do.
4. Run `uv run ultra gates runs/<name>`. Fix what it names. Do not edit `results.json`.
5. Run `uv run ultra export runs/<name>`, commit `contributions/<name>/`, and open a pull request.

## What goes under "Not verified"

At the least:

- Whether any object is what its label says. The screen does not classify.
- The real inspection load. Strata are sampled in equal numbers, not in the proportions of the alert stream.
- Sensitivity on the real sky. The injection uses a simple cadence model and injects ideal hosts.
- Anything you said from background knowledge.

## Words

The objects in this mission are already known. They were re-found, not found.

- Use: "re-found", "passed the screen", "candidate", "consistent with".
- Do not use: "discovered", "confirmed", "new object", "new transient", "first detection". The gate rejects them.
- If a background object passes every criterion, it is an object that passed the screen. It is not a candidate for anything until someone checks existing catalogues and classifications, and that check is outside this mission. List it under "Not verified" by its identifier and say nothing more.

Announcing an object is not something a run can do. Classification needs a spectrum; reporting goes through the Transient Name Server and the people who work on that kind of object.

## Typical failures

- A `measured` claim whose value was rounded. Put the exact value; round in the report text.
- An explanation for the verdict written under "Measured". Explanations are inferences.
- Leaving "Not verified" nearly empty because the verdict was `supported`.
- Rewording until the gate passes while the meaning stays an announcement. The gate matches words; you are responsible for the meaning.

## Verification

`uv run ultra gates runs/<name>` exits 0. Then re-read the report once as someone who wants to quote it: is there a sentence that would be false if quoted alone?

## Example

```json
[
  {"kind": "measured", "text": "Verdict of the locked rule.", "evidence": "/decision/verdict", "value": "supported"},
  {"kind": "measured", "text": "Known nuclear transients scoring 5 or more.", "evidence": "/decision/positives_passed", "value": 14},
  {"kind": "inferred", "text": "The screen narrows the Unknown stratum far more than the QSO stratum.", "basis": "recall_vs_load at threshold 5: 0 of 6 Unknown against 3 of 6 QSO; small numbers."},
  {"kind": "unverified", "text": "Whether the two QSO-stratum objects that scored 6 are flares or ordinary variability.", "basis": "Nothing in this run looks at them individually."}
]
```
