from pathlib import Path

from ultrastronomy import cli, mission as M
from ultrastronomy.analysis import SCREENS, ablation, results_markdown

ROOT = Path(__file__).resolve().parents[1]
ALL = {"galaxy_host": True, "nuclear": True, "long_lived": True, "well_sampled": True,
       "blue_at_peak": True, "no_reddening": True}


def obj(role, label, **failed):
    return {"id": f"{role}-{label}-{sorted(failed)}", "role": role, "label": label, "met": {**ALL, **{k: False for k in failed}}}


def test_each_sub_screen_asks_for_what_it_says():
    red = obj("background", "QSO", blue_at_peak=1, no_reddening=1)
    off_centre = obj("background", "SN", nuclear=1)
    result = ablation([obj("truth", "tde"), red, off_centre], ["tde"])["table"]
    assert result["host"]["QSO"]["passed"] == 1 and result["host"]["SN"]["passed"] == 0
    assert result["colour"]["QSO"]["passed"] == 0 and result["colour"]["SN"]["passed"] == 1
    assert result["5 of 6"]["QSO"]["passed"] == 0 and result["5 of 6"]["SN"]["passed"] == 1
    assert result["6 of 6"]["SN"]["passed"] == 0
    assert all(result[name]["positives"] == {"passed": 1, "n": 1} for name in SCREENS)


def test_supernova_candidates_among_the_known_objects_are_not_positives():
    result = ablation([obj("truth", "tde"), obj("truth", "sn")], ["tde"])
    assert result["table"]["host"]["positives"]["n"] == 1


def test_results_md_is_what_the_records_give():
    """RESULTS.md is generated. If this fails, run `uv run ultra results --write`."""
    mission = M.load_mission("ztf-nuclear-transients")
    expected = results_markdown(ROOT / "contributions", mission, cli.pool(ROOT / "contributions"))
    assert (ROOT / "RESULTS.md").read_text(encoding="utf-8") == expected
