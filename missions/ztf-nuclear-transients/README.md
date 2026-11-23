# Mission: re-find the overlooked nuclear transients of the ZTF archive

## The question

Quintin et al. (2026) went back through six years of ZTF alerts with a classifier and by eye, and reported 23 objects that had been overlooked: 19 flares in the centres of galaxies (candidate tidal disruption events and flares in active galaxies) and 4 supernova candidates.

With alert photometry and a fixed six-criterion screen, how much of the alert stream would a person have to look at to re-find those 19?

## Why it matters

A search that cannot re-find what is already known cannot be trusted to find anything else. This mission measures the screen on known objects, so that anything built on it later starts from a measured recall and a measured cost.

## The pieces

- Known objects: `ground_truth.tsv`, copied from table 1 of the paper (arXiv:2511.19016, CC BY 4.0). Groups: `tde`, `ant` (flare in an active galaxy), `ambiguous`, `sn`. The first three are the positives.
- Background: for each randomly chosen week and each of five Fink classes, a few objects drawn from the last 3,000 alerts of that class in that week. For a busy class such as `Unknown` (about 100,000 alerts a night) that is the tail of the last observed night, a few fields; quieter classes reach back several nights. Each run draws its own weeks from its seed.
- Screen: `src/ultrastronomy/score.py`, six criteria modelled on van Velzen et al. (2021). The thresholds were written from memory of that paper and not checked against it. Fixed for the mission; its known weaknesses are listed in that file.
- Data: alert photometry from the Fink broker's public API. Nothing is redistributed here; each run fetches and caches its own.

## What an earlier run found

A first run outside this harness (484 background objects from 30 weeks, seed 20261123) is recorded in the [re-science repository](https://github.com/yuiseki/re-science/tree/main/poc/ztf-rediscovery). At score >= 5:

| Stratum | Known nuclear transients | Background |
|---|---|---|
| Unknown | 14/19 | 1/112 |
| SN candidate | 14/19 | 4/112 |
| (SIMBAD) Galaxy | 14/19 | 9/52 |
| (SIMBAD) QSO | 14/19 | 27/112 |
| (SIMBAD) Seyfert_1 | 14/19 | 37/96 |

The threshold of 5 was chosen after the scores of the known objects had been seen, and before any background object was scored. If you reuse it, say in your plan that you read this table.

That run used an earlier version of the code, which counted the i band and rows without a sign flag; the harness does not. Its numbers are a guide, not a result of this harness.

## Known limits

- The known objects were selected for looking like tidal disruption events. A screen for that look passes them by construction, so recall here says nothing about objects no one has noticed. The claim of this mission is hard to refute for the same reason, and for one more: most `Unknown` objects have too few detections to meet `well_sampled` or either colour criterion, whatever they are.
- An agent working without this harness reported that, on a sample of this data, its colour and fading checks changed nothing: what separated the known objects was being a single brightening at the centre of a galaxy. Whether that holds for this screen has not been tested. It is the next thing to measure.
- Alerts have far fewer points than the forced photometry the paper used. Four of the five known nuclear transients that scored below 5 in the first run lacked simultaneous g and r detections.
- `(SIMBAD) Galaxy` returns nothing after mid 2022, so that stratum only covers the earlier period. `(SIMBAD) Seyfert_1` returned nothing for a week in March 2025 in one run. The causes were not found.
- Equal numbers per class is not the real mix. On one night checked (2022-03-03) Fink labelled about 100,000 alerts `Unknown` and about 1,000 `SN candidate`.

## What a run adds

A new seed samples new weeks. `ultra pool` counts each background object once across all contributed runs, so every run tightens the intervals on the background pass rates. The recall side cannot grow and is not replicated by a new run: it is the same 23 known objects every time.
