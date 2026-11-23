---
name: ultra-alert-photometry
description: What the numbers in ZTF alert photometry from the Fink broker mean, and the ways they mislead - difference-image magnitudes, negative subtractions, missing-value sentinels, the absence of non-detections, the gap between alerts and forced photometry, and columns that leak later classifications. Use before interpreting an ultrastronomy table, before explaining why a known object failed the screen, or whenever a ZTF light curve, magpsf, isdiffpos, sgscore or a Fink class is involved.
license: Apache-2.0
---

# ultra-alert-photometry

You do not need astronomy to run the harness. You do need this page before you explain what a number means.

## When to use

Before writing anything about why objects passed or failed, and before answering a person's question about a light curve.

## What an alert is

ZTF photographs the sky, subtracts an older reference image, and issues an alert for each place where the difference is significant. An object's alerts are therefore a list of the nights it differed enough from the reference. A night with no alert is not a measurement of "nothing": the field may not have been observed.

## The columns the harness uses

| Column | Meaning | Trap |
|---|---|---|
| `i:jd` | Time, as a Julian Date (days) | Not a calendar date. JD 2459000.5 is 2020-05-31 |
| `i:fid` | Filter: 1 is g (green), 2 is r (red), 3 is i | The harness uses g and r only. Colour needs a g and an r detection within 1.5 days of each other |
| `i:magpsf` | Brightness of the difference, in magnitudes | Smaller is brighter. 5 magnitudes is a factor of 100. It is the excess over the reference, not the object's total brightness |
| `i:isdiffpos` | `t` if the source got brighter than the reference, `f` if fainter | For `f`, `magpsf` is the size of the deficit. The harness ignores those rows, and rows where the flag is missing. An object with no `t` rows scores 0 |
| `i:distpsnr1` | Distance in arcseconds to the nearest source in the Pan-STARRS catalogue | -999 means no match, not a negative distance. The nearest source is usually, not always, the host galaxy; the `nuclear` criterion assumes it is |
| `i:sgscore1` | 0 looks like a galaxy, 1 looks like a star | Bright galaxy cores can score high; that is why some active galaxies fail `galaxy_host` |

No other column is requested. In particular `d:tns` and `d:cdsxmatch` are never read: they hold classifications added later, some of them after the paper that listed the known objects, so using them would hand the screen the answer. The class names of the strata do come from Fink's cross-matching. They decide which pile an object is counted in, never its score.

## The six criteria

`galaxy_host`, `nuclear`, `blue_at_peak`, `no_reddening`, `long_lived`, `well_sampled`. The idea is the photometric selection of tidal disruption events in van Velzen et al. (2021); the thresholds were written from memory of that paper and not checked against it, and the last two criteria are simplifications. A value that cannot be computed counts as not met. `src/ultrastronomy/score.py` lists the screen's known weaknesses.

## What the screen cannot tell you

- Whether an object is a tidal disruption event. That takes a spectrum, and usually other wavelengths.
- Anything about objects with too few alerts. The paper behind the known objects used forced photometry, which has many more points than alerts. A known object that fails for lack of a colour measurement failed because of the data, not because it is ordinary.
- Much about known active galaxies. Their nuclei are central, blue and long-lived on their own, so a large share of them pass.
- The real mix of the sky. The background is the same number of objects per class, while the real stream is mostly the `Unknown` class.
- How faint a real flare can be. The injection test places ideal flares in ideal hosts on a made-up observing schedule. It shows where the criteria stop working on clean data, mostly because the colour slope can no longer be measured.

## Typical failures

- Reading a larger magnitude as brighter.
- Counting an `f` row as a detection of a flare.
- Saying "no detections between two dates" when the alerts simply have a gap. Fields are unobservable for months each year.
- Explaining a pass or a fail from the object's name or a remembered fact about it. Use only what `results.json` holds, or mark the statement as inferred.

## Verification

For any object, `results.json` lists which criteria it met under `objects[].met`. Quote those. If you want to say why a criterion failed, say it as an inference and give the basis.

## Example

"ZTF20aatpzog scored 2. It has 5 positive detections (`n_det`), below the 10 that `well_sampled` asks for, and no simultaneous g and r pair, so neither colour criterion could be computed." The first sentence is measured; the reason is read from `met` and `n_det`.
