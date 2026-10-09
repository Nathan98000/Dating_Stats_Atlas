# Phase 6 halted before commit C: the descriptions would change the build id

9 October 2026. Branch `claude/phase6`, after commits R, A and B.

## What the prompt asked

B.2: regenerate `metros.json`'s descriptions with the build's description step, so the city
descriptions use the new spoken-figure rule (2 significant figures, and a metro outside the
ranked set never reads at or above the 250,000 floor). Its stop conditions:

> regenerating the descriptions (B.2) would change any build file other than `metros.json`'s
> `description` field. If the build id must change, stop before C and ask.

## What I found

The description lives in **two** build files, and both are hashed into the build id:

| Build file | Changes when the descriptions are regenerated |
|---|---|
| `metros.json` | `description` only (260 of 387 metros) |
| `features.parquet` | its `description` column only (the same 260) |
| `count_cube.npy`, `pool_cube.npy`, `sumw2_cube.npy`, `kernel.json`, `kernel.npz`, `pairing_cells.parquet` | no |

`cube.py` hashes every data file into `data_version`, so the build id would move from
**63c4e5fa51bf** to **d62202fd0280** (built in a scratch folder only; nothing in
`atlas/data/builds/` changed and `results/phase2c/city_meta.csv` was restored). No number in
either file moves; only the description text does. The 260 changed sentences are in
`descriptions_regenerated_preview.json` (Champaign: "about 250,000" → "about 240,000"; Abilene:
"about 200,000" → "about 180,000").

## What is built without it

Everything else in B, on build 63c4e5fa51bf with its manifest refreshed (m4.3.0):

- the who-lives-here **card** uses the new rule now: every figure within 5% of its value (worst
  4.7%; 68 metros were off by 10% or more), and no unranked metro's card reaches 250,000;
- the description step itself uses the same function, ready to run;
- the new validation gate (`spoken_figures`) **fails** today on exactly this: 16 unranked metros'
  descriptions still say "about 250,000" (Appleton, Barnstable Town, Bellingham, Binghamton,
  Burlington, Champaign and 10 more). A failing check is a finding; it passes once the
  descriptions are regenerated.

## The choice for Nathan

1. **Take the new build id** (d62202fd0280): regenerate the descriptions, refresh launch.json and
   the deploy notes to the new id; the next deploy copies a new build folder. No number moves.
2. **Keep 63c4e5fa51bf** and leave the descriptions as they are for now; the gate stays failing
   and Champaign's page keeps "about 250,000" over the floor note.
3. Something else (for example, composing the description's population words at serve time).

Commits C to I and the report wait for this answer.
