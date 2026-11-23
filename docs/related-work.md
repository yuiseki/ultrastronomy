# Related work

Looked at on 2026-11-23. Unless noted, each entry was judged from its search result and repository description, not from its code.

## Communities

- Claudestronomy (https://claudestronomy.com/): grants and a group chat for people using AI agents on public sky data, run by macrogrants. Its page was read in full. It states scientific practices but, on that page, offers no software. ultrastronomy is an attempt at software that enforces those practices. It is independent and not affiliated.
- Zooniverse projects such as Backyard Worlds: people classify by eye on a hosted platform. Different in kind: central platform, human judgement as the instrument.

## Agent skills and tools for astronomy

| Project | What it gives an agent | Difference from this project |
|---|---|---|
| SitianClaw (github.com/Yu-Yang-Li/SitianClaw) | Skills for a supernova-candidate workflow on ZTF, including forced-photometry requests | Workflow skills for one team's pipeline. No plan lock or gates, as far as the description shows |
| starfetch (github.com/starfetch-js/starfetch) | Reproducible access to astronomy catalogues over MCP | Data access. Could become a data source here; not needed for the first mission |
| Astronomy-AI-Toolkit (github.com/rudrathegreat/Astronomy-AI-Toolkit) | Skills and agents for pulsar astronomy | Different domain |
| larun (github.com/Paddy1981/larun) | Transit detection on TESS data with small models | A detection tool, aimed at finding candidates |
| scientific-agent-toolkit, K-Dense scientific-agents | Large general collections of science skills and profiles | Breadth. This project is one mission deep, with enforcement in code |

None of these, as described, makes the agent fix its plan before data, computes the verdict itself, or blocks unverified claims. That is the part built here.

## Reused

- Fink broker REST API (https://doc.ztf.fink-broker.org/): the data source. Used as is.
- The photometric selection of tidal disruption events in van Velzen et al. (2021): the screen's criteria and thresholds.
- Quintin et al. (2026), arXiv:2511.19016, CC BY 4.0: the list of known objects.
- Newcombe (1998): the interval for a difference of proportions.
- The re-science repository: the first run of this screen, and the procedure it came from.
- The structure of GeoAI-master-skills and Geo-Ref-skills: an `AGENTS.md` entry point, skills with scripts and tests, gates that refuse instead of repair, and evals that compare runs with and without the skills.

## Not built, and why

- An astronomy library dependency (astropy, lightkurve): nothing in the first mission needs coordinates, units or FITS.
- An MCP server: the harness is a command-line program any agent can run.
- A leaderboard or points: a run's value is its record, and ranking people invites overclaiming.
- Fetching through other brokers (ALeRCE, Lasair, ANTARES): one source is enough to measure one screen.

## Not examined

Whether SitianClaw, larun or the general toolkits contain checks comparable to the gates here. Reading their code is the next step before claiming a difference more strongly than "as described".
