---
name: ultra-report
description: Write the claims and the report of an ultrastronomy run so that what the program measured, what you infer and what nobody checked stay apart, then pass the gates and export the record. Use when writing claims.json or report.md, when `ultra gates` fails, when wording a result for a person, or before exporting a run or telling anyone about an object that passed the screen.
license: Apache-2.0
---

# ultra-report

The program measures and writes the measurements down. You add two things: what you read into them, and what was not checked.

## When to use

Step 6 onwards of `ultra-rediscovery-run`: `results.json` and `measured.md` exist.

## The three sections

`report.md` is a one-line `# ` title followed by exactly these three `## ` headings, in this order. Nothing else comes before `## Measured`. Use `### ` for any sub-heading, and plain Markdown only: no HTML.

| Section | Who writes it | Rule |
|---|---|---|
| `## Measured` | The program | Paste `measured.md` in full and change nothing. Not a digit, not a word |
| `## Inferred` | You | Your reading of the measured numbers. No object identifiers here |
| `## Not verified` | You | What this run did not check. Individual objects are named here and only here |

You may quote and round numbers in your own sections ("about three quarters"). The gate cannot check them, so a reader will: keep them few, and never state a number that is not in `measured.md` or `results.json`.

## claims.json

A list. Each entry has exactly three keys.

```json
{"kind": "inferred", "text": "...", "basis": "which measured numbers, and the reasoning"}
{"kind": "unverified", "text": "...", "basis": "why it is not checked, or what would check it"}
```

There is no `measured` kind: measured statements are the program's. At least one entry must be `unverified`. An `inferred` entry may not name an object; a statement about one object is `unverified`.

## Steps

1. Read `runs/<name>/measured.md`. Read `ultra-alert-photometry` if you have not.
2. Write `runs/<name>/claims.json`.
3. Write `runs/<name>/report.md`: a title, then the three sections.
4. Run `uv run ultra gates runs/<name>`. Fix what it names. Never edit `results.json` or `measured.md`; if they look wrong, run `ultra evaluate` again and report the problem.
5. Tell the person, in plain words: what was looked for, what was measured, what you infer, what was not checked, what a next run could do.
6. Run `uv run ultra export runs/<name>`. Stop there. Committing and opening a pull request is the person's decision.

## What goes under "Not verified"

At the least:

- Whether any object is what its label says. The screen ranks; it does not classify.
- Any background object that passed the screen: give its identifier and that nothing examined it. Say nothing about what it might be.
- The real inspection load. Strata are sampled in equal numbers, and a busy class is sampled from one night.
- That the positive side is the same known objects as in every other run, selected for looking like this.
- Sensitivity on the real sky. The injection is ideal flares on a made-up schedule.
- Weeks or classes that returned nothing, and that the cause is not known.
- Anything you said from background knowledge.
- Problems with the harness or a skill, under a `### Harness and skills` sub-heading.

## Wording

The known objects were re-found, not found. An object that passed the screen is an object that passed the screen.

Do not call anything a candidate, a detection of something, or consistent with being something. Those are the first steps of an announcement, and a run has no way to take the later ones: classification needs a spectrum, and reporting goes through the Transient Name Server and the people who work on that kind of object.

The `wording_lint` gate flags words such as "discovered", "confirmed", "novel", "first detection". It is a tripwire. It cannot tell "this is not a discovery" from "this is a discovery", and it can be evaded. If it fires, do not reword until it passes: the sentence is probably saying more than the run measured. Say what was measured and what was not checked, and leave the rest out.

## Typical failures

- Tidying `measured.md` while pasting it: rounding, reordering, turning it into a table.
- An explanation for the verdict placed under "Measured".
- Naming an object under "Inferred" with a guess at what it is.
- Leaving "Not verified" short because the verdict was `supported`.
- Reading `undecided` as a failed run. With few objects it is the expected and correct result.

## Verification

`uv run ultra gates runs/<name>` exits 0. Then read your two sections as someone who wants to quote them: is there a sentence that would mislead if quoted alone?

## Example

```markdown
# Run 2026-11-23-alice

## Measured

(the full text of measured.md)

## Inferred

The screen keeps about three quarters of the known nuclear transients and almost none of the Unknown stratum in this sample. The Seyfert_1 stratum is where background objects pass most often, which fits what earlier runs saw.

## Not verified

- ZTF21aarjibk (QSO stratum) met all six criteria. Nothing in this run examined it.
- Whether any object is what its label says.
- The week of 2025-03-20 returned nothing for two classes. The cause is not known.
```
