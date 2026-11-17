"""Run with:  python test_extract.py   (needs only Python, not FastAPI)"""
from extractor import extract_item

CASES = [
    # (sentence, expected name, expected location, expected category)
    ("I have stored my key in the drawer in bedroom.", "Key", "Bedroom \u2192 Drawer", "Keys & Accessories"),
    ("I put my black HDMI cable in the second drawer of the wardrobe in the bedroom",
     "HDMI Cable", "Bedroom \u2192 Wardrobe \u2192 Second Drawer", "Cables & Chargers"),
    ("My passport is in the top drawer of the cupboard", "Passport", "Cupboard \u2192 Top Drawer", "Documents"),
    ("In the kitchen cabinet I kept the spare keys", "Spare Keys", "Kitchen Cabinet", "Keys & Accessories"),
    ("I've left my winter jacket under the bed in the guest room", "Winter Jacket", "Guest Room \u2192 Under the Bed", "Clothing"),
    ("I stored a box of screws in the garage", "Box of Screws", "Garage", "Tools"),
    ("hammer is on the shelf in the store room", "Hammer", "Store Room \u2192 On the Shelf", "Tools"),
]

failed = 0
for sentence, name, location, category in CASES:
    r = extract_item(sentence)
    ok = (r["name"], r["location"], r["category"]) == (name, location, category)
    failed += not ok
    print(("PASS " if ok else "FAIL ") + sentence)
    print("     ", r)

# Unclear / empty input: nothing invented
for s in ["", "   ", "where is my key", "hello there", "key"]:
    r = extract_item(s)
    ok = r["name"] == "" and r["location"] == "" and r["category"] == ""
    failed += not ok
    print(("PASS " if ok else "FAIL ") + f"unclear: {s!r} ->", r)

# Reuses an existing category when one fits
r = extract_item("I put my key in the drawer in bedroom", ["Cables", "Keys", "Documents"])
ok = r["category"] == "Keys"
failed += not ok
print(("PASS " if ok else "FAIL ") + "existing category:", r["category"])

print("\nAll good." if not failed else f"\n{failed} FAILED")