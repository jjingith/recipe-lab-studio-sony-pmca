"""Constant tables and value ranges, mirrored exactly from the Recipe Lab (RL fork) Java source.

Sources (do not diverge):
  E:\\pmca-lut-rl\\src\\com\\lutlab\\pmca\\Recipes.java   (STYLE_NAMES, PE_KEYS, GROUPS, subValues, evLabel)
  E:\\pmca-lut-rl\\src\\com\\lutlab\\pmca\\Params.java    (ROW_MIN / ROW_MAX, WB_AUTO / WB_KELVIN)
  E:\\pmca-lut-rl\\src\\com\\lutlab\\pmca\\CustomRecipes.java (DIR, EXT, TMP, MAX_BYTES, NAME_MAX, NAME_PUNCT)

The camera silently skips any .YML whose values fall outside these ranges, so every value
that leaves this program must be validated against them first.
"""

# ---- Creative Style: index = stored enum, value = runtime name (null = an enum the camera uses for something else)
STYLE_NAMES = [None, "standard", "vivid", "neutral", "portrait", "landscape", "mono", "clear",
               "deep", "light", "sunset", "night", "red-leaves", None, "sepia"]
STYLE_LABEL = ["?", "Standard", "Vivid", "Neutral", "Portrait", "Landscape", "B&W", "Clear",
               "Deep", "Light", "Sunset", "Night", "Autumn", "?", "Sepia"]

# ---- Picture Effect: stored byte = index in the runtime list
PE_KEYS = ["off", "toy-camera", "pop-color", "posterization", "retro-photo", "soft-high-key",
           "part-color", "rough-mono", "soft-focus", "hdr-art", "richtone-mono", "miniature",
           "illust", "watercolor"]
PE_LABEL = ["off", "Toy", "Pop", "Poster", "Retro", "High-key", "Part col", "HC mono", "Soft foc",
            "HDR art", "Rich mono", "Miniature", "Illust", "Watercol"]
PE_OFF, PE_TOY, PE_POP, PE_RETRO, PE_HIGHKEY, PE_HCMONO = 0, 1, 2, 4, 5, 7

# ---- DRO: 0 off, 1..5 level, 6 auto
DRO_OFF, DRO_AUTO = 0, 6

# ---- WB modes as stored: 1 auto, 14 colour temperature, 0 keep
WB_AUTO, WB_KELVIN = 1, 14

# ---- the 12 brand groups, in list order
GROUPS = ["Sony", "Fuji Sim", "Fuji Film", "Kodak", "Cine", "Ricoh GR", "Leica",
          "Hasselblad", "Canon / Nikon", "Pana / Olympus", "Other Stocks", "Ilford"]
CUSTOM = -2

# ---- row value ranges (Params.ROW_MIN / ROW_MAX); the custom-recipe fields reuse these
STYLE_MIN, STYLE_MAX = 1, 14
ADJ_MIN, ADJ_MAX = -3, 3            # saturation / contrast / sharpness
PE_MIN, PE_MAX = 0, len(PE_KEYS) - 1
AB_MIN, AB_MAX = -7, 7              # amber(+)/blue(-); green(+) / magenta(-)
GM_MIN, GM_MAX = -7, 7
EV_MIN, EV_MAX = -15, 15           # thirds of a stop
KELVIN_MIN, KELVIN_MAX = 25, 99    # stored units (x100 => 2500..9900)

# ---- the card's file system (Sony FUSE layer: DOS 8.3 names only, no fsync)
DIR = "RECIPES"
EXT = ".YML"
TMP = "SAVING.TMP"
MAX_BYTES = 8192
NAME_MAX = 24
NAME_PUNCT = " -.'()&+"
UNTITLED = "Untitled"

# ---- the field order of a recipe record; index used everywhere
FIELDS = ["style", "sat", "con", "sharp", "wb_mode", "kelvin", "ab", "gm", "pe", "ev", "dro", "sub"]


# ------------------------------------------------------------ helpers (pure, mirror the Java)
def style_known(v):
    return 1 <= v < len(STYLE_NAMES) and STYLE_NAMES[v] is not None


def kelvin_ok(k):
    """kelvin in stored units (already x100); must land in 2500..9900 in 100 steps"""
    return k % 100 == 0 and KELVIN_MIN <= k // 100 <= KELVIN_MAX


def in_range(v, lo, hi):
    return lo <= v <= hi


def sub_values(pe):
    """the sub-parameter names for an effect, or None when it has none — index = stored sub byte"""
    if pe == 5:      # soft-high-key tint
        return ["blue", "pink", "green"]
    if pe == 1:      # toy-camera tone
        return ["normal", "cool", "warm", "green", "magenta"]
    if pe == 6:      # part-colour hue
        return ["red", "green", "blue", "yellow"]
    if pe == 3:      # posterization mode
        return ["posterization-color", "posterization-bw"]
    return None


def name_char(c):
    return c.isascii() and (c.isalnum() or c in NAME_PUNCT)


def ev_label(ev):
    """ev in thirds -> '+0.7' / '0' / '-1'"""
    if ev == 0:
        return "0"
    a = abs(ev)
    frac = ".0" if a % 3 == 0 else ".3" if a % 3 == 1 else ".7"
    return ("+" if ev > 0 else "-") + str(a // 3) + frac


def ev_from_text(v):
    """'+0.7' -> 2, '-1' -> -3, '1.3' -> 4; None for anything else (mirrors CustomRecipes.thirds)"""
    import re
    if not re.fullmatch(r"[+-]?\d{1,2}(\.\d)?", v):
        return None
    neg = v.startswith("-")
    a = v.replace("+", "").replace("-", "")
    dot = a.find(".")
    if dot < 0:
        whole, fd = a, "0"
    else:
        whole, fd = a[:dot], a[dot + 1]
    frac = {"0": 0, "3": 1, "7": 2}.get(fd)
    if frac is None:
        return None
    t = int(whole) * 3 + frac
    return -t if neg else t


def index_of(names, v):
    """position of v in a table of runtime names, ignoring case; -1 for a name it does not hold"""
    low = v.lower()
    for i, n in enumerate(names):
        if n is not None and n.lower() == low:
            return i
    return -1
