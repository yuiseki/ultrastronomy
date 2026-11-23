# Mission: re-find the catalogued periods of known variable stars

## The question

Many stars vary in brightness with a regular period: pulsating stars, pairs of stars that eclipse each other, spotted stars that rotate. The AAVSO keeps an index of the known ones, VSX, with their periods.

With ZTF's public light curves and a plain period search, for what share of variable stars that were catalogued without ZTF is the catalogued period found? And how often does the same search flag a star that no catalogue lists as variable?

## Why it matters

A period search that flags stars is only useful if two numbers are known: how many real variables it finds, and how many ordinary stars it flags anyway. This mission measures both on stars whose answer is already catalogued.

Unlike the first mission, this one leads somewhere a person can go. A star that is flagged, is not in VSX, and survives the checks VSX asks for can be submitted to VSX, where moderators review it. That is a path to a confirmed result that does not need a telescope. The mission itself does not take it: see "What a flagged star is not" below.

## The pieces

- Sky: each run picks random patches of sky from its seed, each 0.3 degrees in radius.
- Known stars: VSX entries in the patch that are marked `Variable`, have a period between 0.11 and 90 days, and are between magnitude 13.5 and 19. They are split by who found them:
  - `catalogued, found elsewhere`: the discoverer is not ZTF. These are the positives. Their periods come from other telescopes, so finding them in ZTF data is an independent check.
  - `catalogued, found by ZTF`: the period was derived from ZTF data in the first place. Finding it again says little, and it is reported separately for that reason.
- Background: `not catalogued`. ZTF sources in a small cone at the patch centre, with at least 50 epochs, more than 5 arcseconds from every VSX entry.
- Search: `src/ultrastronomy/periods.py`. A Lomb-Scargle periodogram over periods from 0.1 to 100 days, leaving out frequencies at whole numbers of cycles per day. A period is "flagged" when its false-alarm probability is below a level the plan fixes, 10^-e.
- Found: the flagged period is within 1% of the catalogued one, or of half or double it. Eclipsing pairs with two similar dips show up at half their period.
- Injection: a sinusoid is added to the real light curves of background stars that were not flagged, and the search is run again. The observing times and the noise are the star's own.
- Data: light curves from IRSA, the catalogue from VSX. Nothing is redistributed here. Light curves are cut at a fixed date and VSX entries at a fixed number, so that a later download selects the same stars.

## Choosing the level

`decision_rule.threshold` is the exponent e, from 2 to 20. A larger e flags fewer stars on both sides. The false-alarm probability assumes noise with no memory, which real photometry is not, so 10^-3 does not mean one false flag in a thousand: the `not catalogued` column is there to show what it does mean. The measured text reports 3, 5, 10 and 20 whichever you choose.

## What a flagged star is not

A `not catalogued` star that is flagged is one of three things: a variable no catalogue has, a variable that is catalogued under a position more than 5 arcseconds away, or a constant star with a systematic in its photometry. This mission cannot tell which. It is listed under "Not verified" by its identifier and nothing more is said about it.

Taking one further is a person's work, outside a run: look at the folded light curve, check other catalogues and surveys, rule out a neighbour and an instrumental period, and follow VSX's submission guidelines. A run never submits anything.

## What the first runs suggest

[RESULTS.md](../../RESULTS.md) has the pooled table. With one run in it, the search found the period of about a third of the variables catalogued without ZTF, and of every variable ZTF catalogued itself.

How often it flags an ordinary star is not settled. In the one recorded run it flagged none of 11, but those light curves were short. In another agent's unfinished run, which is not a record, more than half of 16 were flagged at the loosest level, at periods near one day, half a day and a month: the rhythm of the observing schedule and of the Moon. The false-alarm probability means little for a star with a thousand epochs, and the rate will depend on how well-sampled the background stars of a run happen to be. More runs are what this needs.

## Known limits

- VSX is not complete, so `not catalogued` contains real variables. The flag rate of the background is an upper bound on false flags, not a false-alarm rate.
- VSX grows and is revised. Entries added later are ignored by number, but an entry that is corrected or removed will change the sample, and an old record will then fail to verify.
- Many `found elsewhere` entries come from surveys whose periods are themselves automatic and sometimes wrong. A catalogued period that is not found may be the catalogue's error.
- Only the r band is used, and only the longest light curve of a star when several ZTF fields cover it.
- Outlying points are not removed before the search.
- A real variable observed only at night also shows power at its frequency plus or minus one cycle per day. The search can settle on that alias with great confidence, and the matching rule, which accepts the period, its half and its double, then counts the star as not found. The first run showed this. The rule was left as it is: changing it after seeing which stars it loses would be tuning.
- Stars from the same patch share a ZTF field and its observing history, so they are not independent. The rule treats them as if they were.
- Patches in the Milky Way hold hundreds of catalogued stars and patches far from it a handful, so sparse patches contribute fewer stars than asked.
- The frequencies near whole cycles per day are left out, so a variable with a period very close to 1 day or a simple fraction of it will not be found at that period.
