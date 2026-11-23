# Mission: re-find the overlooked nuclear transients of the ZTF archive

## The question

Quintin et al. (2026) went back through six years of ZTF alerts with a classifier and by eye, and reported 23 objects that had been overlooked: 19 flares in the centres of galaxies (candidate tidal disruption events and flares in active galaxies) and 4 supernova candidates.

With alert photometry and a fixed six-criterion screen, how much of the alert stream would a person have to look at to re-find those 19?

## Why it matters

A search that cannot re-find what is already known cannot be trusted to find anything else. This mission measures the screen on known objects, so that anything built on it later starts from a measured recall and a measured cost.

## The pieces

- Known objects: `ground_truth.tsv`, copied from table 1 of the paper (arXiv:2511.19016, CC BY 4.0). Groups: `tde`, `ant` (flare in an active galaxy), `ambiguous`, `sn`. The first three are the positives.
- Background: objects that had an alert in a randomly chosen week, drawn in equal numbers from five Fink classes. Each run draws its own weeks from its seed.
- Screen: `src/ultrastronomy/score.py`, six criteria after van Velzen et al. (2021). Fixed for the mission.
- Data: alert photometry from the Fink broker's public API. Nothing is redistributed here; each run fetches and caches its own.

## What an earlier run found

A first run outside this harness (484 background objects from 30 weeks, seed 20261123) is recorded in the re-science repository. At score >= 5:

| Stratum | Known nuclear transients | Background |
|---|---|---|
| Unknown | 14/19 | 1/112 |
| SN candidate | 14/19 | 4/112 |
| (SIMBAD) Galaxy | 14/19 | 9/52 |
| (SIMBAD) QSO | 14/19 | 27/112 |
| (SIMBAD) Seyfert_1 | 14/19 | 37/96 |

The threshold of 5 was chosen after the scores of the known objects had been seen, and before any background object was scored. If you reuse it, say in your plan that you read this table.

## Known limits

- The known objects were selected for looking like tidal disruption events. A screen for that look passes them by construction, so recall here says nothing about objects no one has noticed.
- Alerts have far fewer points than the forced photometry the paper used. Four of the five known nuclear transients that scored below 5 in the first run lacked simultaneous g and r detections.
- `(SIMBAD) Galaxy` returns nothing after mid 2022, so that stratum only covers the earlier period. The cause was not found.
- Equal numbers per class is not the real mix. On one night checked (2022-03-03) Fink labelled about 100,000 alerts `Unknown` and about 1,000 `SN candidate`.

## What a run adds

A new seed samples new weeks. `ultra pool` counts each background object once across all contributed runs, so every run tightens the intervals on the background pass rates. The recall side cannot grow: there are 23 known objects.
