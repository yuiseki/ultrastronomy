# Run 2026-11-23-opencode

## Measured

- Data: ZTF alert photometry from the Fink API.
- Locked rule: score of 5 or more; positives against the `Unknown` stratum.
- Positives passing: 14 of 19. `Unknown` objects passing: 0 of 12.
- Difference in pass rates: +0.737, 95% interval +0.406 to +0.882.
- Verdict: supported.
- All known objects passing at that score, supernova candidates included: 14 of 23.
- `(SIMBAD) Galaxy` objects passing at that score: 1 of 8.
- `(SIMBAD) QSO` objects passing at that score: 2 of 12.
- `(SIMBAD) Seyfert_1` objects passing at that score: 5 of 12.
- `SN candidate` objects passing at that score: 0 of 12.
- `Unknown` objects passing at that score: 0 of 12.
- Background objects scored: 56. Of these, 20 had no positive detection and score 0.
- Synthetic flares passing at that score, by peak magnitude, under a model cadence (each band observed on a third of nights during a 240-day season, 30% of visits lost to weather, limiting magnitude 20.5 with 0.3 mag scatter): 17.0: 100 of 100, 17.5: 100 of 100, 18.0: 100 of 100, 18.5: 86 of 100, 19.0: 79 of 100, 19.5: 47 of 100, 20.0: 20 of 100, 20.5: 0 of 100.

## Inferred

At the locked threshold of 5, this sample has the screen keeping about three quarters of the known positives (14 of 19) while keeping none of the 12 `Unknown` background objects, so the locked rule returned `supported`. The 95% interval for the difference runs from +0.406 to +0.882, entirely above zero.

The background objects that did pass were not spread evenly by label. They cluster in the active-galaxy strata: 5 of 12 `(SIMBAD) Seyfert_1` and 2 of 12 `(SIMBAD) QSO` passed, against 1 of 8 `(SIMBAD) Galaxy`, 0 of 12 `SN candidate` and 0 of 12 `Unknown`. On this sample, a person applying the screen would spend most of their inspection on things Fink already labels as active galaxies.

A large share of the background scored zero for a simple reason: 20 of the 56 scored background objects had no positive detection at all, so they scored 0 without any colour or duration test being decisive. That is a property of alert photometry (fewer points than the forced photometry the original list used), not evidence about what those objects are.

The injection test keeps ideal synthetic flares in almost every case down to about magnitude 19 and then falls off (about half at 19.5, about a fifth at 20.0, none at 20.5). This is on the stated model cadence and ideal hosts, so it is not a statement about the real sky.

## Not verified

- Whether any object is what its label says. The screen ranks by photometric criteria; it does not classify.
- Each background object that passed the screen is listed here, and nothing in this run examined any of them: ZTF18aahbiav ((SIMBAD) Seyfert_1, score 6), ZTF18aaluviz ((SIMBAD) Seyfert_1, score 6), ZTF21aabcscsv ((SIMBAD) Seyfert_1, score 6), ZTF18aczergd ((SIMBAD) QSO, score 5), ZTF19aanfkmp ((SIMBAD) Seyfert_1, score 5), ZTF19acgkead ((SIMBAD) Galaxy, score 5), ZTF20aahlxul ((SIMBAD) Seyfert_1, score 5), ZTF21aaitkhl ((SIMBAD) QSO, score 5).
- The positive side is the same 19 known objects used by every run, chosen for looking like this. This run repeats only the background side; it does not independently replicate the recall.
- Sensitivity on the real sky: the injection uses ideal flares in ideal hosts on a made-up observing schedule.
- The `(SIMBAD) Galaxy` stratum returned nothing for two of the six sampled weeks (2022-10-29 and 2023-03-26), so it has 8 objects instead of 12. The cause is not known from this run.
- The real inspection load of the alert stream: strata are sampled in equal numbers, and a busy class such as `Unknown` is drawn from the tail of a single night, not from a week.
- Anything said from background knowledge rather than from `results.json` or `measured.md`.

### Harness and skills

- AGENTS.md "Rules" is numbered 1-6, then 9, then 7-8 (lines 19-21). It reads as an ordering mistake; it did not change what I did, but it is easy to mis-cite.
- AGENTS.md rule 4 and `ultra-rediscovery-run/SKILL.md` "Typical failures" do not say whether a transient network error may be retried or must stand as the run's result. The first `ultra fetch` failed with HTTP 502 after 84 requests; I treated that as a transient error and retried, and the retry completed with 26 more requests while the harness counted the 84 against the 130-request budget. If retrying is not intended, the instructions should say so.
- `ultra fetch` prints "this plan needs at most N requests" on every attempt but only prints the already-used count separately; it never prints the remaining count directly. Not wrong, but a reader has to subtract.
