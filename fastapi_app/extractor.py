"""
Rule-based extraction of item details from a spoken sentence.

No AI/LLM, no external API, no token needed. It understands the common ways
people say where they put something, e.g.

    "I have stored my key in the drawer in bedroom."
    "My passport is in the top drawer of the cupboard."
    "In the bedroom drawer I kept my black HDMI cable."

and never invents details: anything it can't find is returned as "".
Pure standard library, so it can be tested without FastAPI installed.
"""
import re
from difflib import get_close_matches
from typing import Dict, Iterable, List, Optional

# ---------------------------------------------------------------- vocabulary
VERBS = {
    "stored": "stored", "store": "stored", "put": "put", "placed": "placed",
    "place": "placed", "kept": "kept", "keep": "kept", "left": "left",
    "leave": "left", "hid": "hidden", "hidden": "hidden", "hide": "hidden",
    "tucked": "tucked", "stashed": "stashed", "saved": "saved",
    "parked": "parked", "stuffed": "stuffed",
}
VERB_ALT = "|".join(sorted(VERBS, key=len, reverse=True))

# Prepositions that locate something. "of" only joins parts ("top drawer of the cupboard").
PREP_ALT = r"on top of|in front of|next to|inside of|inside|underneath|under|behind|beside|near|above|below|into|in|on|at"
PREP_WITH_OF = PREP_ALT + r"|of"
PREP_CAPTURE = re.compile(rf"\b({PREP_WITH_OF})\b", re.IGNORECASE)

# Prepositions worth keeping in the location text ("Under the Bed"); "in/inside/at/of" are implied by the arrows.
KEEP_PREP = {
    "on top of": "On top of", "in front of": "In front of", "next to": "Next to",
    "underneath": "Under", "under": "Under", "behind": "Behind", "beside": "Beside",
    "near": "Near", "above": "Above", "below": "Below", "on": "On",
}

DETERMINERS = {"the", "a", "an", "my", "our", "your", "his", "her", "their", "this", "that",
               "these", "those", "some", "one"}
POSSESSIVES = {"my", "our", "your", "his", "her", "their"}
NAME_ADJECTIVES = {
    "black", "white", "red", "blue", "green", "yellow", "grey", "gray", "silver", "gold",
    "golden", "brown", "pink", "purple", "orange", "small", "big", "large", "tiny", "old",
    "new", "little", "long", "short",
}
ACRONYMS = {"hdmi", "usb", "usb-c", "tv", "pc", "sd", "ssd", "hdd", "id", "dvd", "cd", "led",
            "ac", "dc", "wifi", "wi-fi", "gps", "sim", "vga", "atm", "nfc"}
SMALL_WORDS = {"the", "of", "on", "in", "at", "a", "an", "and", "to", "for"}

CATEGORY_KEYWORDS = [
    ("Cables & Chargers", {"cable", "charger", "adapter", "adaptor", "cord", "hdmi", "usb", "plug",
                           "extension", "power bank", "powerbank", "wire"}),
    ("Keys & Accessories", {"key", "keychain", "wallet", "watch", "sunglasses", "glasses", "belt",
                            "purse", "umbrella", "lanyard"}),
    ("Electronics", {"laptop", "phone", "tablet", "camera", "headphone", "earphone", "earbud",
                     "remote", "battery", "speaker", "monitor", "router", "mouse", "keyboard",
                     "tv", "console", "drone", "printer", "pendrive", "pen drive"}),
    ("Documents", {"passport", "certificate", "document", "paper", "file", "deed", "receipt",
                   "license", "licence", "policy", "contract", "visa", "bill", "invoice",
                   "id card", "card", "will"}),
    ("Tools", {"hammer", "screwdriver", "drill", "wrench", "plier", "tape", "tool", "spanner",
               "saw", "toolbox", "screw", "nail", "bolt", "nut", "ladder"}),
    ("Clothing", {"jacket", "coat", "sweater", "shirt", "shoe", "boot", "scarf", "glove", "hat",
                  "cloth", "dress", "saree", "sari", "blanket", "sock", "cap", "suit"}),
    ("Kitchen", {"pan", "pot", "plate", "knife", "spoon", "cooker", "kettle", "mixer", "bottle",
                 "lunchbox", "flask", "cup", "mug", "bowl", "grinder"}),
    ("Medicine & Health", {"medicine", "pill", "first aid", "bandage", "thermometer", "inhaler",
                           "ointment", "syrup"}),
    ("Jewellery", {"ring", "necklace", "bracelet", "earring", "chain", "bangle", "pendant"}),
    ("Books & Stationery", {"book", "notebook", "pen", "pencil", "diary", "calculator", "stapler",
                            "marker"}),
]

QUESTION_START = re.compile(r"^\s*(where|what|how|who|when|why|which|can|could|do|does|did)\b", re.IGNORECASE)

# ---------------------------------------------------------------- patterns
_LEAD = r"^(?:(?:okay|ok|so|well|um+|uh+|please|hey|note that|remember that)[,\s]+)*"
_SUBJ = r"(?:(?:i|we)(?:\s+(?:have|had|just|already|also|now))*\s+)?"
_SUBJ_REQUIRED = r"(?:i|we)(?:\s+(?:have|had|just|already|also|now))*\s+"
_ADV = r"(?:(?:just|already|also|now)\s+)?"
# Item ends at the first locating preposition ("of" is allowed inside an item: "box of screws").
_PATTERNS = [
    # I (have) stored my key in the drawer in bedroom
    re.compile(
        rf"{_LEAD}{_SUBJ}{_ADV}(?P<verb>{VERB_ALT})\s+(?:away\s+)?(?P<item>.+?)\s+(?P<loc>(?:{PREP_ALT})\s+.+)$",
        re.IGNORECASE),
    # In the bedroom drawer I kept my key
    re.compile(
        rf"{_LEAD}(?P<loc>(?:{PREP_ALT})\s+.+?),?\s+{_SUBJ_REQUIRED}{_ADV}(?P<verb>{VERB_ALT})\s+(?:away\s+)?(?P<item>.+)$",
        re.IGNORECASE),
    # My passport is (kept/stored) in the top drawer
    re.compile(
        rf"{_LEAD}(?P<item>.+?)\s+(?:is|are|was|were|should be)\s+(?:(?P<verb>{VERB_ALT})\s+)?(?P<loc>(?:{PREP_ALT})\s+.+)$",
        re.IGNORECASE),
]

# ---------------------------------------------------------------- helpers
def _clean(text: str) -> str:
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"\b(I|We|you|they)'ve\b", r"\1 have", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .!?,;:")


def _strip_leading(words: List[str], remove: Iterable[str]) -> List[str]:
    remove = set(remove)
    while words and words[0].lower() in remove:
        words = words[1:]
    return words


def _fix_word(word: str, first: bool, title: bool) -> str:
    low = word.lower()
    if low in ACRONYMS:
        return word.upper() if "-" not in word else word.upper().replace("USB-C", "USB-C")
    if word.isupper() and len(word) > 1:
        return word
    if any(c.isupper() for c in word[1:]):
        return word
    if title and low in SMALL_WORDS and not first:
        return low
    return word[:1].upper() + word[1:] if (title or first) else word


def _title(text: str) -> str:
    words = text.split()
    return " ".join(_fix_word(w, i == 0, True) for i, w in enumerate(words))


def _sentence(text: str) -> str:
    words = text.split()
    return " ".join(_fix_word(w, i == 0, False) if (i == 0 or w.lower() in ACRONYMS) else w
                    for i, w in enumerate(words))


def _singular_tokens(text: str) -> set:
    tokens = set()
    for w in re.findall(r"[a-z0-9\-]+", text.lower()):
        tokens.add(w)
        if len(w) > 3 and w.endswith("ies"):
            tokens.add(w[:-3] + "y")
        elif len(w) > 3 and w.endswith("es"):
            tokens.add(w[:-2])
        if len(w) > 3 and w.endswith("s"):
            tokens.add(w[:-1])
    return tokens


def _location_parts(loc: str) -> List[str]:
    matches = list(PREP_CAPTURE.finditer(loc))
    parts = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(loc)
        text = loc[m.end():end].strip(" ,.;")
        prep = re.sub(r"\s+", " ", m.group(1).lower())
        label = KEEP_PREP.get(prep)
        words = text.split()
        words = _strip_leading(words, POSSESSIVES if label else DETERMINERS)
        if not words:
            continue
        phrase = " ".join(words)
        parts.append(_title(f"{label} {phrase}" if label else phrase))
    parts.reverse()  # spoken order is inner -> outer; we store outer -> inner
    return parts


def _suggest_category(item_text: str) -> str:
    lowered = item_text.lower()
    tokens = _singular_tokens(item_text)
    for label, words in CATEGORY_KEYWORDS:
        for w in words:
            if (" " in w and w in lowered) or w in tokens:
                return label
    return ""


def _pick_existing(label: str, item_text: str, existing: Optional[List[str]]) -> str:
    existing = [c.strip() for c in (existing or []) if isinstance(c, str) and c.strip()]
    if not existing:
        return label
    by_lower = {c.lower(): c for c in existing}
    if label and label.lower() in by_lower:
        return by_lower[label.lower()]
    item_tokens = _singular_tokens(item_text)
    for c in existing:
        words = {w for w in _singular_tokens(c) if w not in {"and", "the", "other", "misc"}}
        if words & item_tokens:
            return c
    if label:
        close = get_close_matches(label.lower(), list(by_lower), n=1, cutoff=0.75)
        if close:
            return by_lower[close[0]]
    return label


# ---------------------------------------------------------------- main entry
def extract_item(transcript: str, categories: Optional[List[str]] = None) -> Dict[str, str]:
    empty = {"name": "", "description": "", "category": "", "location": ""}
    text = _clean(transcript)
    if not text:
        return empty

    match = None
    if not QUESTION_START.match(text):
        for pattern in _PATTERNS:
            match = pattern.match(text)
            if match:
                break

    if not match:
        # Couldn't understand the sentence: keep what the user said, invent nothing.
        return {**empty, "description": _sentence(text)}

    item_words = _strip_leading(match.group("item").split(), DETERMINERS)
    # Drop a trailing "away"/"safe" style filler.
    while item_words and item_words[-1].lower() in {"away", "safely", "somewhere"}:
        item_words.pop()
    loc_text = re.sub(r"\binto\b", "in", match.group("loc").strip(" ,."), flags=re.IGNORECASE)
    if not item_words:
        return {**empty, "description": _sentence(text)}

    item_text = " ".join(item_words)
    name_words = _strip_leading(item_words, NAME_ADJECTIVES) or item_words
    verb = VERBS.get((match.group("verb") or "").lower(), "kept")

    parts = _location_parts(loc_text)
    return {
        "name": _title(" ".join(name_words)),
        "description": f"{_sentence(item_text)} {verb} {loc_text[:1].lower() + loc_text[1:]}",
        "category": _pick_existing(_suggest_category(item_text), item_text, categories),
        "location": " \u2192 ".join(parts),
    }