---
name: ultra-periods
description: What a period search on a ZTF light curve does and how its results mislead - Lomb-Scargle power, false-alarm probability, half and double periods, one-day aliases, catalogue errors, and what a flagged star does and does not mean. Use before interpreting a run of the ztf-known-periods mission, before choosing its threshold, before explaining why a catalogued period was or was not found, or whenever a variable star, a period, VSX or a periodogram is involved.
license: Apache-2.0
---

# ultra-periods

Read this before you choose the threshold of a `ztf-known-periods` run, and before you say what its numbers mean. The mission's own README has the definitions; this is how to read them.

## When to use

A run of the mission `ztf-known-periods`: when writing the plan, and when writing your two sections of the report.

## What the search does

A light curve is a list of times and brightnesses. The search tries tens of thousands of periods and asks, for each, how well a wave of that period fits. The best one is reported with a false-alarm probability: how likely pure noise would give a fit that good.

| Term | Meaning | Trap |
|---|---|---|
| Period | Time for one cycle, in days | The search covers 0.1 to 100 days. Anything outside cannot be found |
| Magnitude | Brightness; smaller is brighter | An amplitude of 0.1 magnitude is about 10% in brightness |
| False-alarm probability | Chance of this fit from noise with no memory | Real photometry has memory: seeing, moonlight, the same calibration stars night after night. The stated probability is too optimistic, sometimes by many orders of magnitude |
| Flagged | The probability is below 10^-e, with e fixed in the plan | Flagged means "this light curve is not white noise". It does not mean "this star varies" |
| Found | Flagged, and within 1% of the catalogued period or of half or double it | Half and double are counted as found on purpose |
| Epochs | Number of measurements | Below 50 the star is not searched and counts as not found |

## Why half and double count

Two stars that eclipse each other dim twice per orbit. If the two dips look alike, a wave fits best at half the orbital period, and catalogues differ in which they list. The measured text gives both the number found and the number found at the exact period.

## The one-day problem

A telescope on the ground observes at night, so its measurements repeat every day. Anything that changes with the time of night shows up as a period of one day, half a day, a third of a day. The search leaves out a narrow band around those. A true variable with a period there is lost, and a systematic just outside the band can still be flagged.

## Reading the three groups

- `catalogued, found elsewhere`: the independent test. Their periods were measured by other telescopes. This is the recall that matters.
- `catalogued, found by ZTF`: the period came from ZTF data. Finding it again in ZTF data mostly shows the code agrees with someone else's code. Do not add it to the recall.
- `not catalogued`: what the search flags among stars nobody lists as variable. VSX is incomplete, so some of these are real variables. Report the rate as the share of uncatalogued stars flagged, never as a false-alarm rate.

A catalogued period that is not found has several possible reasons, and the run cannot tell them apart: too few epochs, an amplitude below the noise, a period near one day, a non-sinusoidal shape, or a wrong period in the catalogue.

## Choosing e

There is no correct value. Small e (3) finds more catalogued periods and flags more of everything. Large e (20) flags little and misses faint variables. Whatever you choose, say why, and do not look at any light curve first. The measured text reports 3, 5, 10 and 20 regardless, so the choice decides only which line the verdict is read from.

## What a flagged, uncatalogued star is not

It is not a new variable star, a candidate, or a find. It is an entry in a list of stars someone could look at. The steps from there to a catalogue entry are a person's: inspect the folded light curve, check other surveys and catalogues, rule out a neighbouring star and an instrumental period, and follow the submission guidelines of VSX, where moderators decide. A run does none of this and submits nothing.

List such stars under "Not verified" by identifier. Say nothing about what they might be.

## Typical failures

- Calling the flag rate of the background a false-alarm rate.
- Adding the `found by ZTF` group to the recall.
- Treating the false-alarm probability as a real probability ("one in a hundred thousand").
- Explaining a miss with one cause when the run cannot distinguish the causes.
- Reading the injection as the search's sensitivity to real variables. It injects sinusoids; eclipses and pulsations are not sinusoids.

## Verification

Every number you quote is in `measured.md`. For one star, `results.json` has `objects[].period`, `cat_period`, `log10_fap`, `match` and `n_points`. If you say why a star was missed, it is an inference: give the basis, and keep the star's identifier out of the Inferred section.

## Example

"At 10^-5 the search found the period of 9 of the 14 stars catalogued without ZTF, 7 of them at the exact period, and flagged 2 of 15 uncatalogued stars. The injection shows 0.05-magnitude sinusoids are mostly missed in these light curves, so some of the five misses may simply be faint." The first sentence restates measured numbers; the second is an inference and says what it rests on.
