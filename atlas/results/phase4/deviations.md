# Phase 4 deviations

One line each; PHASE4.md's list is kept identical.

- Stage 0: the phase 2g manifest (`results/phase2g/hero_image.csv`) is read by nothing — `hero_image.py` wrote it beside `web/src/data/hero.json` from the same record, and the site reads only hero.json — so it is deleted like the phase 2f file rather than kept with its stray change discarded; `hero_image.py` no longer writes it, and hero.json stays the hero's committed record. Both files' stray change was line endings only (CRLF), which git's `core.autocrlf=input` already hid from `git status`.
- Stage 1: PHASE3D.md's A1 heading cited `efd93d7`, an amended draft of the Phase 3d A1 commit that was never on main (it survived only as an unreachable object), so filter-repo's commit map has no entry for it; the citation now names A1 as it is on main (`98725a2` before the rewrite), in the same follow-up commit as the mapped hashes.
