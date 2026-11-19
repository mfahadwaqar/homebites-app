"""Build catalog/data/nutrition.json from quantified reference recipes.

Each serving is a documented sum: grams of each ingredient x its energy density
(kcal per 100 g, standard USDA FoodData Central values, cooked weight for rice,
noodles, pulses and meats). Values are estimates for a typical home-cooked
serving, not laboratory measurements. Edit quantities here and re-run.
"""
import json
from pathlib import Path

KCAL = dict(  # kcal per 100 g
    jrice=130, brice=130, srice=97, noodle=138, rnoodle=108, egg=143, chicken=190, beef=230, mince_beef=250,
    mince_chicken=185, lamb=260, prawn=99, hilsa=310, potato=87, tomato=18, onion=40, garlic=149, ginger=80,
    chilli=40, lime=30, peanut=567, coconut_milk=197, tamarind=239, sugar=387, oil=884, ghee=876, butter=717,
    cream=340, yogurt=61, milk=61, paneer=321, spinach=23, lentil=116, chickpea=164, flour=364, rice_flour=366,
    jaggery=383, mung=105, papaya=43, bean=47, sprout=30, carrot=41, mango=60, sesame=573, cauli=25, pea=81,
    aubergine=25, bamboo=27, cowpea=116, cabbage=25, coconut=354, milkpowder=496, spice=300, friedonion=500,
    pistachio=560, mustard=508, bread=280, urad=105, gundruk=30, puri=480, samosa=400, paste=100, ricepowder=360,
    herb=30, soy=53, scallion=32, galangal=70, lemongrass=99, pickled=20, wheat=340, vegetable=40, sambar_dal=116,
    rosewater=0, water=0, cooked_rice=130, fish_sauce=35,
)
# code: (serving text, [(ingredient key, grams)])
R = {
    "TH01": ("1 plate (350 g)", [("rnoodle", 200), ("egg", 50), ("sprout", 40), ("peanut", 15), ("tamarind", 15), ("sugar", 10), ("oil", 15)]),
    "TH02": ("1 bowl (400 g)", [("prawn", 120), ("lemongrass", 10), ("galangal", 8), ("herb", 5), ("chilli", 8), ("lime", 20), ("tomato", 40), ("oil", 8), ("water", 190)]),
    "TH03": ("1 bowl with rice (450 g)", [("chicken", 120), ("coconut_milk", 100), ("paste", 25), ("herb", 10), ("aubergine", 50), ("oil", 10), ("jrice", 135)]),
    "TH04": ("1 plate (250 g)", [("papaya", 130), ("tomato", 40), ("bean", 30), ("lime", 15), ("peanut", 15), ("sugar", 8), ("fish_sauce", 8), ("garlic", 4)]),
    "TH05": ("1 plate (350 g)", [("jrice", 250), ("egg", 50), ("scallion", 15), ("carrot", 25), ("soy", 10), ("oil", 15)]),
    "TH06": ("1 bowl with rice (450 g)", [("beef", 110), ("potato", 90), ("coconut_milk", 80), ("paste", 25), ("peanut", 12), ("onion", 30), ("oil", 8), ("jrice", 60)]),
    "TH07": ("1 plate with rice (400 g)", [("mince_chicken", 110), ("herb", 15), ("chilli", 8), ("garlic", 8), ("oil", 15), ("soy", 10), ("jrice", 235)]),
    "TH08": ("1 bowl (450 g)", [("noodle", 170), ("chicken", 100), ("coconut_milk", 100), ("paste", 25), ("pickled", 25), ("oil", 8), ("onion", 20)]),
    "TH09": ("1 plate (200 g)", [("mince_chicken", 120), ("lime", 15), ("herb", 10), ("ricepowder", 8), ("chilli", 5), ("onion", 20), ("fish_sauce", 8), ("srice", 30)]),
    "TH10": ("1 plate (250 g)", [("mango", 120), ("srice", 100), ("coconut_milk", 50), ("sugar", 18), ("sesame", 3)]),
    "PK01": ("1 plate (400 g)", [("brice", 260), ("chicken", 130), ("yogurt", 30), ("onion", 40), ("oil", 15), ("spice", 6)]),
    "PK02": ("1 bowl (350 g)", [("beef", 150), ("flour", 12), ("ginger", 8), ("spice", 6), ("chilli", 3), ("ghee", 20), ("onion", 40), ("water", 110)]),
    "PK03": ("1 bowl (350 g)", [("beef", 100), ("wheat", 35), ("lentil", 80), ("ginger", 8), ("friedonion", 15), ("ghee", 15), ("spice", 6)]),
    "PK04": ("1 portion (300 g)", [("chicken", 180), ("tomato", 90), ("ginger", 8), ("garlic", 8), ("chilli", 8), ("oil", 25)]),
    "PK05": ("2 kebabs (180 g)", [("mince_beef", 130), ("onion", 25), ("tomato", 20), ("herb", 8), ("chilli", 4), ("oil", 25), ("flour", 12)]),
    "PK06": ("1 bowl (300 g)", [("mince_beef", 140), ("potato", 90), ("onion", 40), ("tomato", 50), ("spice", 4), ("oil", 20)]),
    "PK07": ("1 bowl (320 g)", [("lamb", 140), ("spinach", 150), ("onion", 35), ("ginger", 8), ("spice", 5), ("oil", 22)]),
    "PK08": ("1 plate (450 g)", [("lentil", 200), ("brice", 200), ("onion", 30), ("spice", 4), ("oil", 12)]),
    "PK09": ("1 plate (250 g)", [("samosa", 60), ("potato", 50), ("chickpea", 60), ("yogurt", 50), ("tamarind", 12), ("onion", 15)]),
    "PK10": ("1 bowl (200 g)", [("milk", 150), ("brice", 35), ("sugar", 25), ("spice", 1), ("pistachio", 8)]),
    "BD01": ("1 plate (420 g)", [("brice", 220), ("lamb", 130), ("yogurt", 40), ("potato", 60), ("ghee", 15), ("spice", 8), ("onion", 30)]),
    "BD02": ("1 bowl (350 g)", [("cooked_rice", 180), ("mung", 120), ("onion", 25), ("ginger", 6), ("ghee", 18), ("vegetable", 30)]),
    "BD03": ("1 portion (200 g)", [("hilsa", 130), ("mustard", 10), ("chilli", 6), ("oil", 15), ("onion", 25), ("spice", 3)]),
    "BD04": ("1 bowl (250 g)", [("beef", 170), ("onion", 50), ("ginger", 8), ("garlic", 8), ("spice", 6), ("oil", 30)]),
    "BD05": ("1 bowl (300 g)", [("prawn", 160), ("coconut_milk", 100), ("onion", 40), ("ginger", 8), ("spice", 3), ("oil", 15)]),
    "BD06": ("1 plate (400 g)", [("brice", 250), ("chicken", 130), ("onion", 30), ("ghee", 22), ("spice", 6)]),
    "BD07": ("1 serving (180 g)", [("aubergine", 150), ("onion", 20), ("chilli", 5), ("oil", 18), ("herb", 5)]),
    "BD08": ("1 bowl (350 g)", [("cooked_rice", 300), ("onion", 20), ("chilli", 5), ("water", 25)]),
    "BD09": ("8 pieces (200 g)", [("puri", 60), ("potato", 70), ("chickpea", 50), ("tamarind", 12), ("chilli", 5)]),
    "BD10": ("1 cup (150 g)", [("milk", 100), ("yogurt", 30), ("jaggery", 20)]),
    "NP01": ("8 momos (240 g)", [("flour", 95), ("mince_chicken", 110), ("onion", 25), ("ginger", 5), ("garlic", 5), ("oil", 12)]),
    "NP02": ("1 plate (500 g)", [("brice", 250), ("lentil", 130), ("potato", 60), ("cauli", 50), ("oil", 15)]),
    "NP03": ("2 rings (130 g)", [("rice_flour", 65), ("sugar", 12), ("milk", 25), ("spice", 1), ("oil", 30)]),
    "NP04": ("1 bowl (450 g)", [("noodle", 180), ("chicken", 90), ("carrot", 30), ("cabbage", 30), ("ginger", 6), ("oil", 10), ("water", 110)]),
    "NP05": ("1 bowl (300 g)", [("potato", 110), ("bamboo", 60), ("cowpea", 70), ("tomato", 40), ("oil", 15), ("spice", 3)]),
    "NP06": ("1 chatamari (180 g)", [("rice_flour", 60), ("egg", 50), ("mince_chicken", 50), ("onion", 15), ("herb", 5), ("oil", 12)]),
    "NP07": ("2 pieces (140 g)", [("rice_flour", 70), ("jaggery", 35), ("sesame", 6), ("coconut", 15)]),
    "NP08": ("1 bowl (300 g)", [("gundruk", 40), ("potato", 90), ("tomato", 40), ("onion", 25), ("chilli", 4), ("oil", 10), ("water", 95)]),
    "NP09": ("1 plate (220 g)", [("chicken", 180), ("yogurt", 20), ("spice", 3), ("ginger", 6), ("garlic", 6), ("oil", 12)]),
    "NP10": ("1 cup (150 g)", [("milk", 100), ("yogurt", 30), ("sugar", 14), ("spice", 1)]),
    "IN01": ("1 bowl (300 g)", [("chicken", 150), ("tomato", 80), ("butter", 25), ("cream", 30), ("spice", 4), ("onion", 30)]),
    "IN02": ("1 dosa with filling (250 g)", [("brice", 70), ("urad", 40), ("potato", 100), ("onion", 25), ("oil", 15), ("mustard", 2)]),
    "IN03": ("1 plate (350 g)", [("chickpea", 150), ("flour", 60), ("tomato", 40), ("onion", 30), ("oil", 25), ("spice", 4)]),
    "IN04": ("1 bowl (300 g)", [("paneer", 100), ("spinach", 150), ("onion", 30), ("garlic", 6), ("cream", 25), ("oil", 12)]),
    "IN05": ("1 plate (400 g)", [("brice", 280), ("carrot", 30), ("pea", 30), ("cauli", 30), ("oil", 12), ("spice", 6)]),
    "IN06": ("1 bowl (300 g)", [("lamb", 150), ("yogurt", 50), ("ginger", 8), ("spice", 5), ("oil", 25), ("onion", 40)]),
    "IN07": ("4 idli with sambar (400 g)", [("brice", 90), ("urad", 40), ("sambar_dal", 80), ("vegetable", 60), ("tamarind", 8), ("oil", 8)]),
    "IN08": ("1 plate with 2 pav (350 g)", [("potato", 120), ("tomato", 60), ("pea", 40), ("butter", 25), ("bread", 90), ("onion", 15)]),
    "IN09": ("2 pieces (250 g)", [("chicken", 200), ("yogurt", 30), ("lime", 8), ("spice", 4), ("oil", 12)]),
    "IN10": ("2 pieces (100 g)", [("milkpowder", 30), ("flour", 12), ("sugar", 50), ("spice", 1), ("rosewater", 1), ("oil", 8)]),
}

SOURCE = ("Estimate: reference home recipe for one serving, grams x USDA FoodData Central energy values "
          "per ingredient (cooked weights), including cooking fat; reviewed 14 Nov 2026. Seller portions vary.")

if __name__ == "__main__":
    dishes = json.loads(Path("catalog/data/dishes.json").read_text(encoding="utf-8"))["dishes"]
    assert {d["code"] for d in dishes} == set(R)
    out = {}
    for code, (serving, items) in R.items():
        total = sum(KCAL[k] * g / 100 for k, g in items)
        out[code] = {"serving_size": serving, "calories_kcal": int(round(total / 5.0) * 5),
                     "recipe_grams": dict(items), "source": SOURCE}
    Path("catalog/data/nutrition.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for code, v in out.items():
        print(code, v["calories_kcal"], v["serving_size"])
