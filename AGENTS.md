# ultrastronomy: instructions for agents

A person has asked you to take part in ultrastronomy. You will run a small, checkable piece of astronomy on public data, and leave a record that someone else can verify. You do not need to know astronomy. You do need to follow the order below.

## What you are doing

One run takes a list of objects that astronomers already found, and a fixed screen, and measures two things: how many of the known objects the screen keeps, and how much of everything else it keeps too. Runs by different people sample different weeks of the archive. Pooled, they say how well the screen works.

You are not looking for new objects. A run that announces one has failed, whatever else it did.

## Rules

1. Numbers come from the program. You never type a result; you point at it in `results.json`.
2. The plan is locked before any data is read. You do not change it afterwards. A different plan is a different run.
3. `supported`, `rejected` and `undecided` are all results. Do not rescue a rejected claim by changing the threshold, the stratum, the seed or the objects.
4. A failure is reported as a failure. Do not fill a failed fetch, a missing value or a broken step with a default or a guess.
5. Ask the person for a budget before you start, and stop when it is reached. You cannot see how much AI usage remains, so never state or estimate it.
6. Before any network request, tell the person how many requests the run will make. `ultra fetch` prints the number and does nothing until you add `--confirm`.
7. Do not send API keys, tokens or anything about the person to any service. The data API needs no account.
8. Say what you do not know. If you cannot tell, the answer is "not verified".

## Which skill to read

Open the `SKILL.md` before acting. Do not work from the name and description alone.

| Situation | Skill |
|---|---|
| Starting, or unsure what comes next | `.agents/skills/ultra-rediscovery-run/SKILL.md` |
| Filling in `plan.json`, or `ultra lock` refused | `.agents/skills/ultra-plan/SKILL.md` |
| About to explain what a number or a light curve means | `.agents/skills/ultra-alert-photometry/SKILL.md` |
| Writing `claims.json` and `report.md`, or `ultra gates` failed | `.agents/skills/ultra-report/SKILL.md` |

## Commands

```sh
uv run ultra demo                    # whole pipeline on synthetic data, offline
uv run ultra status runs/<name>      # what is done, what comes next
uv run pytest                        # the harness's own tests
```

`ultra status` names the next command at every step.

## What to tell the person

At the end, in plain language:

- what was looked for, and why re-finding known objects matters before looking for unknown ones
- the table, and the verdict the locked rule gave
- what was not checked
- what a next run could do
- that the record is in `runs/<name>/`, and how to share it (`ultra export`, then a pull request)

## When something is wrong with the harness or a skill

If a skill's instruction was unclear, or the harness let through something it should have stopped, say so in `report.md` under "Not verified" and tell the person. That is a contribution too: see `CONTRIBUTING.md`.
