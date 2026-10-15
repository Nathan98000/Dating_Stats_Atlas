"""Phase 8 (the round-4 review's R13): real descriptions for the city
photographs whose alt text a screen reader could not use, each written after
looking at the photograph, with any building or place named only where the
photograph's own source (its Commons title or description) names it.

Recorded as the photo review records rewritten alt texts
(results/phase4/photo_review.json `alt_overrides`, which its apply step
reapplies) and written to the render manifest the same way
(web/src/data/city-images.json), without re-running the whole apply step.
All are DRAFTS for Nathan's approval (atlas/PHASE8.md §3).

    python3 atlas/results/phase8/alt_texts.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "results" / "phase4" / "photo_review.json"
CITY = ROOT / "web" / "src" / "data" / "city-images.json"
WHY = "Phase 8 (the round-4 review's R13, Nathan's go of 15 October 2026): "

# slug -> (the old alt's problem, the new alt)
ALTS = {
    "indianapolis-indiana": ("the city's name in lower case", "Downtown Indianapolis from above on a clear day, its twin-spired tallest tower at the centre and an arena's arched roof in the foreground."),
    "montgomery-alabama": ("a library catalogue record", "Downtown Montgomery from the air, with the riverboat landing and the long train shed on the Alabama River in the foreground."),
    "abilene-texas": ("\"image\", announced as nothing", "Downtown Abilene's brick and stone towers rising above a line of green trees under a deep blue sky."),
    "casper-wyoming": ("a file name and a crop note", "Downtown Casper beside the North Platte River, with the broad slopes of Casper Mountain rising behind the city."),
    "chambersburg-pennsylvania": ("empty", "Memorial Square in Chambersburg, with a tiered iron fountain and a brick courthouse's white clock cupola on a summer day."),
    "el-centro-california": ("empty", "The Imperial County courthouse in El Centro, its columned front lit up at dusk beside a palm trunk."),
    "gadsden-alabama": ("a file name, announced as nothing", "Gadsden from the air, its downtown grid beside the curving Coosa River among wooded hills."),
    "hot-springs-arkansas": ("a list of file names", "A collage of Hot Springs: the town among wooded hills from above, a domed bathhouse's arcade, the brick Army and Navy Hospital tower, a hot spring pooling among rocks, and a street of old hotels lit at night."),
    "macon-georgia": ("a file name, announced as nothing", "Macon from high above, its downtown streets and highways spread across wooded country in a blue haze."),
    "gettysburg-pennsylvania": ("a caption followed by a copied heritage-listing notice", "Devil's Den on the Gettysburg battlefield seen from Little Round Top, with boulders and green grass under a broad sky."),
    "kahului-hawaii": ("a caption with an uploader's note", "Kahului from the air, its low buildings and harbor along the blue Pacific coast of Maui."),
    "st-cloud-minnesota": ("a caption followed by a copied heritage-listing notice", "The brick and stone storefronts of St. Germain Street's 800 block in downtown St. Cloud on a sunny day."),
    "sebastian-florida": ("\"Sebastian, Florida: City hall\" with stray line breaks", "Sebastian's city hall, a cream building with a red tile roof and an arched porch, among palm trees under a clear blue sky."),
    "dubuque-iowa": ("the place's name only", "Downtown Dubuque's brick buildings and church spires seen over treetops from a bluff, with green hills beyond."),
    "greenville-north-carolina": ("the place's name only", "A downtown Greenville street seen from above at sunset, cars passing between brick buildings under a fiery orange sky."),
    "hanford-california": ("the place's name only", "Hanford's civic auditorium, its tall columns and pale front facing a lawn under a deep blue sky."),
    "mansfield-ohio": ("the place's name only", "Mansfield's skyline above a band of green trees: a tall red-brick tower, two white high-rises and church spires on the left."),
    "springfield-ohio": ("the place's name only", "Red-brick buildings on a corner of downtown Springfield in late-afternoon sun, with people walking beneath leafy trees."),
    "st-george-utah": ("the place's name only, in capitals", "St. George's houses spread across the valley below red cliffs, with snow-dusted mountains under a clouded sky beyond."),
    "waterloo-iowa": ("the place's name only", "Downtown Waterloo's brick buildings along the Cedar River, its surface patched with ice, behind a low bridge."),
    "watertown-new-york": ("the place's name only", "Public Square in Watertown on a spring day, with a stone obelisk, benches and young trees in leaf beside the street."),
    "wenatchee-washington": ("the place's name only", "Wenatchee among green trees in its river valley, with brown foothills and snow-capped mountains behind."),
    "victoria-texas": ("\"Skyline\"", "A broad street in Victoria leading toward a tall office building, with traffic and trees in late-afternoon light."),
    "monroe-michigan": ("\"Monroe Skyline\"", "Downtown Monroe's brick buildings and a low arched bridge across the River Raisin under a big cloudy sky."),
    "decatur-illinois": ("\"Downtown Decatur\"", "Downtown Decatur's brick storefronts and a tall historic tower at dusk, seen from above a lit street corner."),
    "minot-north-dakota": ("the place's name only", "Downtown Minot's low brick buildings and a few taller blocks beyond tall grass and shrubs under a clear sky."),
    "sumter-south-carolina": ("\"Downtown Sumter\"", "A tree-lined brick street in downtown Sumter, with a red awning and flower planters in summer."),
    "yuba-city-california": ("\"Downtown Yuba City\"", "A sunny sidewalk in downtown Yuba City, with shopfronts, a palm tree and a water tower behind."),
    "gainesville-georgia": ("the place's name only", "A red-brick building with a white domed cupola in downtown Gainesville, framed by tree branches against a blue sky."),
    "grand-junction-colorado": ("\"Grand Junction, Colorado skyline\"", "Grand Junction spread across the valley floor beyond dry hills, with a long range of hills on the horizon under clouds."),
    "fayetteville-north-carolina": ("\"Fayetteville, NC Downtown Skyline\"", "Downtown Fayetteville from above, with church steeples, brick buildings and tree-lined streets on a clear day."),
    "jonesboro-arkansas": ("\"Collage of Jonesboro, AR\"", "A collage of Jonesboro: a tall clock tower, a brick civic building with a statue in front, a red-brick house with a porch, and a downtown street of shopfronts."),
    "lebanon-pennsylvania": ("\"Cumberland Street View Image\"", "Cumberland Street in downtown Lebanon from above, cars passing brick buildings and a glass-fronted corner building."),
    "la-crosse-wisconsin": ("\"La Crosse Main Street\"", "Main Street in downtown La Crosse, with red-brick storefronts, a sidewalk clock and people crossing on a summer day."),
    "saginaw-michigan": ("\"Saginaw from the River\"", "Saginaw's downtown towers and a bridge seen across the calm Saginaw River on a clear evening."),
    "rochester-minnesota": ("two words run together (\"Peace PlazaDowntown\")", "Peace Plaza in downtown Rochester, a brick square with lamps and trees surrounded by glass and stone towers."),
    "dover-delaware": ("wiki markup (\"w:Dover\")", "West Loockerman Street in downtown Dover, with storefronts and bare trees in early spring."),
    "st-joseph-missouri": ("wiki markup (\"w:Buchanan County\")", "The Buchanan County Courthouse in downtown St. Joseph, a red-brick building with white columns and a silver dome."),
    "mankato-minnesota": ("wiki markup (\"en:\")", "Brick storefronts of the North Riverfront Drive Commercial District in Mankato on a sunny day."),
    "bloomington-indiana": ("a web address", "Kirkwood Avenue in Bloomington at sunset, a street of shops and restaurants under a golden sky."),
    "bozeman-montana": ("the wrong town (\"Springfield, Montana\")", "Main Street in downtown Bozeman, a row of brick buildings and shade trees on a sunny day."),
    "sandusky-ohio": ("a misspelling (\"Ariel view\")", "Downtown Sandusky from the air at sunset, its marina and waterfront on Sandusky Bay below a streaked sky."),
    "charlottesville-virginia": ("a population figure the site did not compute", "Downtown Charlottesville from the air, brick buildings among dense trees with green mountains beyond."),
    "hattiesburg-mississippi": ("a population figure the site did not compute", "Downtown Hattiesburg from the air, its brick and stone buildings beside a railway line under an overcast sky."),
    # found by the new manifest test (web/tests/phase8.test.ts)
    "bellingham-washington": ("a population figure the site did not compute", "Downtown Bellingham from the air, its red-brick towered old city hall among trees, with forested hills under a summer sky."),
    "fond-du-lac-wisconsin": ("wiki markup (\"w:\") and a copied heritage-listing notice", "Main Street in downtown Fond du Lac, a broad street of historic brick buildings under leafy trees on a sunny day."),
    "mount-vernon-washington": ("a population figure the site did not compute", "Downtown Mount Vernon from the air beside the Skagit River and a bridge, with green mountains under clouds beyond."),
    "pittsfield-massachusetts": ("a population figure the site did not compute", "Downtown Pittsfield from the air, brick buildings among dense trees with the green Berkshire hills beyond."),
    "pueblo-colorado": ("a population figure the site did not compute", "Downtown Pueblo from the air, its brick buildings and the Riverwalk's channel spread out under a clear sky."),
    "morgantown-west-virginia": ("two words (\"Woodburn Hall\")", "Woodburn Hall in Morgantown, a red-brick building with a clock tower and mansard roofs, framed by green trees."),
}


def main() -> None:
    rev = json.loads(REVIEW.read_text())
    city = json.loads(CITY.read_text())
    # a re-run keeps each entry's first record of the old text
    was = {r["key"]: r["was"] for r in rev.get("alt_overrides", [])
           if r["page"] == "city" and r["key"] in ALTS and "was" in r}
    keep = [r for r in rev.get("alt_overrides", []) if not (r["page"] == "city" and r["key"] in ALTS)]
    new = []
    for slug, (problem, alt) in ALTS.items():
        assert slug in city, slug
        new.append({"page": "city", "key": slug, "alt": alt,
                    "was": was.get(slug, city[slug].get("alt") or ""),
                    "why": WHY + f"the old alt text was {problem}; this one describes the photograph (DRAFT for Nathan's approval)."})
        city[slug]["alt"] = alt
    rev["alt_overrides"] = keep + new
    REVIEW.write_text(json.dumps(rev, indent=1, ensure_ascii=False) + "\n")
    # the render manifest, written as the photo review's apply step writes it
    sys.path.insert(0, str(ROOT.parent))
    from atlas.pipeline.build import photo_review as PR
    PR._write_render(CITY, city)
    print(f"{len(new)} alt texts written")


if __name__ == "__main__":
    main()
