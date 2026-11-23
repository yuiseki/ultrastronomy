# Run 2026-11-23-first

The maintainer's first run through the harness on real data: the rule of the earlier run, on six new weeks (seed 2207).

## Measured

- Data: ZTF alert photometry from the Fink API.
- Locked rule: score of 5 or more; positives against the `Unknown` stratum.
- Positives passing: 14 of 19. `Unknown` objects passing: 0 of 12.
- Difference in pass rates: +0.737, 95% interval +0.406 to +0.882.
- Verdict: supported.
- All known objects passing at that score, supernova candidates included: 14 of 23.
- `(SIMBAD) Galaxy` objects passing at that score: 0 of 6.
- `(SIMBAD) QSO` objects passing at that score: 4 of 12.
- `(SIMBAD) Seyfert_1` objects passing at that score: 4 of 12.
- `SN candidate` objects passing at that score: 1 of 12.
- `Unknown` objects passing at that score: 0 of 12.
- Background objects scored: 54. Of these, 23 had no positive detection and score 0.
- Synthetic flares passing at that score, by peak magnitude, under a model cadence (each band observed on a third of nights during a 240-day season, 30% of visits lost to weather, limiting magnitude 20.5 with 0.3 mag scatter): 17.0: 100 of 100, 17.5: 100 of 100, 18.0: 99 of 100, 18.5: 94 of 100, 19.0: 80 of 100, 19.5: 55 of 100, 20.0: 15 of 100, 20.5: 0 of 100.

## Inferred

On this sample the screen keeps about three quarters of the known nuclear transients and none of the Unknown stratum. Twelve Unknown objects is close to the smallest sample the rule accepts, so this agrees with the earlier run more than it adds to it.

The strata of known active galaxies are where the screen separates least: a third of the QSO and Seyfert_1 objects pass. Their nuclei are central, blue and long-lived on their own.

The positive side is unchanged from the earlier run although the code now ignores the i band and rows without a sign flag. Those corrections did not move any known object across the threshold.

## Not verified

- Whether any object is what its label says. The screen ranks; it does not classify.
- Nine background objects scored 5 or more: ZTF18aaqlukq, ZTF18acevggt, ZTF19aaomkbg and ZTF21abrptgf (Seyfert_1 stratum), ZTF18aautpwv, ZTF18adlrdlv, ZTF19aasaywo and ZTF19aasbuev (QSO stratum), ZTF21abavqaz (SN candidate stratum). Nothing in this run examined them.
- Whether the recall would hold for objects nobody has noticed. The positives are the same 19 objects as in every run, selected for looking like this, and the threshold was chosen after their scores had been seen. This run repeats the background side only.
- The real inspection load. Strata are sampled in equal numbers, and a busy class is sampled from the tail of one night.
- Sensitivity on the real sky. The injection is ideal flares in ideal hosts on a made-up schedule.
- Why the (SIMBAD) Galaxy stratum returned nothing for the weeks of 2022-11-30, 2023-08-19 and 2024-03-29.
- Why five known nuclear transients scored below 5. The criteria they missed are in results.json; no light curve was looked at.
- The plan was written after the full results of the earlier run and of two discarded small runs had been seen, as `seen_before_lock` says.

### Harness and skills

- This record has not been recomputed by anyone but its author.
