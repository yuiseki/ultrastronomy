# Task: rediscovery

The same request is given in both conditions. Only what the agent has in its working directory differs.

## Bare condition

Working directory: `data/lightcurves/*.json` (alert photometry from the Fink API, all columns), `data/known_objects.tsv`, `data/other_objects.tsv`. No harness, no skills, no network needed.

> These are ZTF alert light curves from the Fink broker. `data/known_objects.tsv` lists 23 objects that a 2026 paper (arXiv:2511.19016) reported as overlooked: nuclear transients (groups tde, ant, ambiguous) and supernova candidates (sn). `data/other_objects.tsv` lists 60 other objects with the class Fink gave them. Assess whether a simple photometric screen for flares that look like tidal disruption events can re-find the known nuclear transients without also flagging too many of the other objects. Write your findings in `report.md` and keep your code in this directory. I am not an astronomer. My budget for this is about 25 minutes of your work.

## Harness condition

Working directory: a copy of this repository at the commit under test, with an empty cache.

> Read AGENTS.md and take me through an ultrastronomy run. I am not an astronomer. My budget is about 25 minutes of your work; a small run is fine. If you need my go-ahead for network requests, you have it.

## Rubric

Scored from the files the agent left, one point each. `evidence` says where to look.

| # | Item | Evidence |
|---|---|---|
| 1 | The comparison (threshold, what is compared) was fixed before results were seen | a dated plan, or code and log order |
| 2 | Negative subtractions (`isdiffpos` f) are not counted as brightening | code |
| 3 | The -999 sentinel is not used as a distance or score | code |
| 4 | Later classifications (`d:tns`, `d:cdsxmatch`) are not used by the screen | code |
| 5 | The pass rate of the other objects is reported, per class, next to recall | report |
| 6 | An interval or other statement of uncertainty accompanies the comparison | report |
| 7 | Sensitivity is measured with injected or simulated sources | code, report |
| 8 | The data used is traceable: source and a list or hashes of the objects | files |
| 9 | Measured numbers are kept apart from interpretation | report |
| 10 | No object is called a TDE, a discovery or confirmed on the strength of the screen | report |
| 11 | What was not verified is listed, including how the known objects were selected | report |
| 12 | Three numbers picked from the report match what the code outputs | spot check |
