# Run 2026-11-23-periods-first

## Measured

- Data: ZTF public r-band light curves from IRSA; known variables from the AAVSO VSX.
- Locked rule: a period is flagged when its false-alarm probability is below 10^-5; variables catalogued without ZTF against stars not catalogued.
- Catalogued variables whose period was found (exactly, or at half or double): 5 of 15. Stars not catalogued that were flagged: 0 of 11.
- Difference: +0.333, 95% interval +0.017 to +0.583.
- Verdict: supported.
- At 10^-3: `catalogued, found by ZTF` 8 of 8 found (4 at the exact period); `catalogued, found elsewhere` 5 of 15 found (2 at the exact period); `not catalogued` 0 of 11 flagged.
- At 10^-5: `catalogued, found by ZTF` 8 of 8 found (4 at the exact period); `catalogued, found elsewhere` 5 of 15 found (2 at the exact period); `not catalogued` 0 of 11 flagged.
- At 10^-10: `catalogued, found by ZTF` 8 of 8 found (4 at the exact period); `catalogued, found elsewhere` 4 of 15 found (2 at the exact period); `not catalogued` 0 of 11 flagged.
- At 10^-20: `catalogued, found by ZTF` 8 of 8 found (4 at the exact period); `catalogued, found elsewhere` 4 of 15 found (2 at the exact period); `not catalogued` 0 of 11 flagged.
- Stars with fewer than 50 epochs, which cannot be searched and count as not found: 2.
- Sinusoids added to real r-band light curves of background stars that were not flagged, found at the injected period, by amplitude: 0.02 mag: 2 of 11, 0.05 mag: 6 of 11, 0.1 mag: 6 of 11, 0.2 mag: 8 of 11.

## Inferred

This is the first run of the periods mission, by its maintainer. It is a repeat: the same plan was evaluated three times before while the search code was made faster, and the plan says so.

On this sample a plain period search finds about a third of the variables that were catalogued without ZTF, and flags none of the stars no catalogue lists. The difference clears zero, barely. The level chosen hardly matters: from the loosest to the strictest the counts move by one star.

Every period that ZTF itself catalogued was found. Set against a third of the others, that is what agreement between two programs reading the same data looks like, and it is the reason the two groups are reported apart.

Some of the misses look like one-day aliases: the search is confident in a period whose frequency is close to one cycle per day away from the catalogued one. The matching rule accepts only the period, its half and its double, and it was not changed after seeing this.

The background light curves are shallow. Most have fewer than a hundred epochs, and even a 0.2 magnitude sinusoid added to them is missed in three of eleven. So none flagged is weak evidence that those stars do not vary, and weak evidence about how often the search flags ordinary stars.

## Not verified

- Why each catalogued period was missed. Too few epochs, a faint signal, an alias, a shape that is not a sinusoid and a wrong period in the catalogue all look the same here.
- Whether any uncatalogued star in the sample varies.
- Whether the catalogued periods are right. They are taken from VSX as given.
- Whether the background flag rate holds elsewhere. Another agent's unfinished run on a different seed, which is not part of any record, had well-sampled background stars flagged at periods near one day, half a day and a month. Those are the periods of the observing schedule and of the Moon, not of stars.
- Two catalogued stars had fewer than 50 epochs in the light curve that was selected and count as not found. Whether another ZTF field has a longer light curve for them was not checked.
- Fewer stars than asked in every group: 15, 8 and 11 instead of 16. Some patches had too few.
- The sensitivity of the search to real variables. The injection adds sinusoids; eclipses and pulsations are not sinusoids.

### Harness and skills

- The matching rule has no notion of one-day aliases, and the band left out around whole cycles per day is narrow. Whether to change either is a question for a second version, judged on stars this run did not use.
- The background cone of 36 arcseconds often holds fewer than two stars with 50 epochs, and those it holds are faint.
