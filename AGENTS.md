# ultrastronomy: instructions for agents

A person has asked you to take part in ultrastronomy. You will run a small, checkable piece of astronomy on public data, and leave a record that someone else can verify. You do not need to know astronomy. You do need to follow the order below.

## What you are doing

One run takes objects whose answer astronomers already know, and a fixed search, and measures two things: how many of the known objects the search finds, and how much of everything else it flags too. Runs by different people sample different parts of the archive. Pooled, they say how well the search works.

There are two missions. Ask the person which they want; if they have no preference, take `ztf-known-periods`.

| Mission | Looks at | Read first |
|---|---|---|
| `ztf-known-periods` | Variable stars with catalogued periods, in ZTF light curves. About 50 requests, 10 minutes | `missions/ztf-known-periods/README.md` |
| `ztf-nuclear-transients` | Flares at the centres of galaxies, in ZTF alerts. About 110 requests, 8 minutes | `missions/ztf-nuclear-transients/README.md` |

You are not looking for new objects. A run that announces one has failed, whatever else it did.

## Rules

1. Numbers come from the program. It writes them as sentences in `measured.md`; you paste that text unchanged and write your own words in separate sections.
2. The plan is locked before any data is read. You do not change it afterwards, and you do not delete a lock. A different plan is a different run with a different name.
3. `supported`, `rejected` and `undecided` are all results. Do not rescue a rejected claim by changing the threshold, the stratum, the seed or the objects.
4. A failure is reported as a failure. Do not fill a failed fetch, a missing value or a broken step with a default or a guess. Running the same command again after a network error is not filling in: it is allowed, once or twice, and the failure stays in the log and goes in the report.
5. Work within the person's budget and stop when it is reached. If they have not given one, ask before you start. You cannot see how much AI usage remains, so never state or estimate it.
6. Before any network request, tell the person the most requests the run can make. `ultra fetch` prints the number and does nothing until you add `--confirm`. If they gave their go-ahead in advance, report the number and continue.
7. Do not send API keys, tokens or anything about the person to any service. The data API needs no account.
8. Say what you do not know. If you cannot tell, the answer is "not verified".
9. Committing a record or opening a pull request publishes it under the person's name. Stop at `ultra export` and ask.

## Which skill to read

Open the `SKILL.md` before acting. Do not work from the name and description alone.

| Situation | Skill |
|---|---|
| Starting, or unsure what comes next | `.agents/skills/ultra-rediscovery-run/SKILL.md` |
| Filling in `plan.json`, or `ultra lock` refused | `.agents/skills/ultra-plan/SKILL.md` |
| About to explain a number of the `ztf-nuclear-transients` mission | `.agents/skills/ultra-alert-photometry/SKILL.md` |
| Choosing the threshold of, or explaining a number of, the `ztf-known-periods` mission | `.agents/skills/ultra-periods/SKILL.md` |
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
- that the record is in `runs/<name>/`, that `ultra export` has copied it to `contributions/<name>/`, and that sharing it (a commit and a pull request) is theirs to decide

## When something is wrong with the harness or a skill

If a skill's instruction was unclear, or the harness let through something it should have stopped, say so in `report.md` under "Not verified", in a `### Harness and skills` sub-heading, and tell the person. That is a contribution too: see `CONTRIBUTING.md`.

## What the harness does not do for you

The gates recompute every number and compare the report's measured section with the program's text. They do not read your sentences for sense, and the wording check is a tripwire that is easy to pass while still misleading. Whether your two sections are honest is on you.
