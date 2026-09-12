"""Phase 2a Gate 0: expanded, stratified variance battery.

480 shapes — 3x Phase 1's 160, which was thin for a model with more than two
terms. Stratification is explicit rather than sampled: 160 shapes carry no
race filter (the stratum whose 34% residual error is undiagnosed) and every
race level gets 40 shapes, each block cycled deterministically across
age-span buckets {4-8, 9-15, 16-30}, education floors, income floors
(including the 150k/250k tail) and marital screens, with seeded jitter for
ages. Every shape is evaluated with the full 81-replicate machinery across
all 387 metros: ~186k (shape, metro) points.

Splits are assigned at fit time, not here: 70/30 by shape and 80/20 by metro
(stratified by metro sample size), so the Gate 0 model is validated on
shapes it never saw AND metros it never saw.
"""
from __future__ import annotations

import itertools
import random

import pandas as pd

from atlas.pipeline.fetch import DATA
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.build.variance import eval_shapes

POINTS2_PARQUET = DATA / "variance_points2.parquet"
SHAPES2_PARQUET = DATA / "battery2_shapes.parquet"
SEED = 202

EDU_FLOORS = [("any", "TRUE"),
              ("some_college+", "edu4 IN ('some_college','bachelors','graduate')"),
              ("ba+", "edu4 IN ('bachelors','graduate')"),
              ("graduate", "edu4 = 'graduate'")]
INC_FLOORS = [None, None, 25_000, 50_000, 75_000, 100_000, 150_000, 250_000]
MARITALS = [("not_married", "msp IN (3,4,5,6)"), ("never", "msp = 6"),
            ("any", "TRUE")]
SPANS = [(4, 8), (9, 15), (16, 30)]
RACES = [None] * 4 + ["hispanic", "nh_white", "nh_black", "nh_asian",
                      "nh_aian", "nh_nhpi", "nh_twoplus", "nh_other"]
PER_RACE = 40  # x (4 none-slots + 8 races) = 480 shapes


def sample_shapes() -> list[dict]:
    rng = random.Random(SEED)
    shapes = []
    sid = 1000
    for race in RACES:
        cyc = itertools.product(SPANS, EDU_FLOORS, MARITALS)
        combos = list(cyc)  # 3*4*3 = 36 strata; 40 shapes cycle through them
        for k in range(PER_RACE):
            span, (edu_name, edu_sql), (mar_name, mar_sql) = combos[k % len(combos)]
            inc = INC_FLOORS[k % len(INC_FLOORS)]
            sex = 1 if (k // len(INC_FLOORS)) % 2 == 0 else 2
            lo = rng.randint(18, 55)
            hi = min(70, lo + rng.randint(*span))
            where = (f"sex = {sex} AND agep BETWEEN {lo} AND {hi} "
                     f"AND {edu_sql} AND {mar_sql}")
            if inc:
                where += f" AND inc_adj >= {inc}"
            if race:
                where += f" AND race8 = '{race}'"
            shapes.append({"shape_id": sid, "sex": sex, "age_lo": lo, "age_hi": hi,
                           "age_span": hi - lo + 1, "edu": edu_name, "inc": inc,
                           "marital": mar_name, "race": race, "where": where})
            sid += 1
    assert len(shapes) == len(RACES) * PER_RACE
    return shapes


def main() -> None:
    con = open_pool()
    shapes = sample_shapes()
    pd.DataFrame(shapes).to_parquet(SHAPES2_PARQUET, index=False)
    pts = eval_shapes(con, shapes, "battery2")
    pts.to_parquet(POINTS2_PARQUET, index=False)
    print(f"battery2: {len(shapes)} shapes -> {len(pts):,} points -> {POINTS2_PARQUET}")


if __name__ == "__main__":
    main()
