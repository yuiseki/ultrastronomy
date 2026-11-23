"""Build the working directory for the bare condition: data, no harness, no skills.

    python evals/prepare_bare_task.py <raw-cache> <ground_truth.tsv> <background.tsv> <workdir>

`raw-cache` holds one JSON file per object as returned by the Fink API with
its full set of columns, including the ones the harness never requests
(`d:tns`, `d:cdsxmatch`). The bare agent gets the data as a person would
find it, traps included.
"""

import csv
import json
import random
import shutil
import sys
from pathlib import Path

SEED = 7
PER_STRATUM = 12


def main(raw, truth_tsv, background_tsv, workdir) -> int:
    raw, work = Path(raw), Path(workdir)
    (work / "data" / "lightcurves").mkdir(parents=True)
    truth = list(csv.DictReader(open(truth_tsv, newline=""), delimiter="\t"))
    background = list(csv.DictReader(open(background_tsv, newline=""), delimiter="\t"))
    rng = random.Random(SEED)
    picked = []
    for stratum in sorted({b["fink_class"] for b in background}):
        rows = [b for b in background if b["fink_class"] == stratum]
        picked += rng.sample(rows, PER_STRATUM)
    for row in truth + picked:
        shutil.copy(raw / f"{row['ztf_id']}.json", work / "data" / "lightcurves" / f"{row['ztf_id']}.json")
    with (work / "data" / "known_objects.tsv").open("w") as fh:
        fh.write("ztf_id\ttns_name\tgroup\n")
        fh.writelines(f"{t['ztf_id']}\t{t['tns_name']}\t{t['group']}\n" for t in truth)
    with (work / "data" / "other_objects.tsv").open("w") as fh:
        fh.write("ztf_id\tfink_class\n")
        fh.writelines(f"{b['ztf_id']}\t{b['fink_class']}\n" for b in picked)
    print(json.dumps({"known": len(truth), "others": len(picked)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
