"""Recipe model + the Recipe Lab custom-recipe file format (version 1).

Read/write mirrors com.lutlab.pmca.RecipeFormatV1 and CustomRecipes exactly, so a file this
program produces is byte-identical to one the camera app would write, and a file it accepts is
one the camera app accepts (values outside the ranges make the camera skip the file silently).
"""
from dataclasses import dataclass, field, asdict
import os

from . import ranges as R


@dataclass
class Recipe:
    group: int = R.CUSTOM
    name: str = ""
    style: int = 1
    sat: int = 0
    con: int = 0
    sharp: int = 0
    wb_mode: int = R.WB_AUTO
    kelvin: int = 0
    ab: int = 0
    gm: int = 0
    pe: int = 0
    ev: int = 0
    dro: int = R.DRO_AUTO
    sub: int = 0

    # ---- derived / display helpers
    def is_effect(self):
        return self.pe != 0

    def is_custom(self):
        return self.group == R.CUSTOM

    def values(self):
        """the 12 settable fields in FIELDS order"""
        return [getattr(self, f) for f in R.FIELDS]

    def summary(self):
        """one-line description, in the style of Recipes.Recipe.summary()"""
        s = []
        if self.pe != 0:
            s.append(R.PE_LABEL[self.pe] if 0 <= self.pe < len(R.PE_LABEL) else "?%d" % self.pe)
            sv = R.sub_values(self.pe)
            if sv is not None and 0 <= self.sub < len(sv):
                s.append(sv[self.sub].replace("posterization-", ""))
        else:
            label = R.STYLE_LABEL[self.style] if 0 <= self.style < len(R.STYLE_LABEL) else "?%d" % self.style
            s.append("%s  %s%d/%s%d" % (label, "+" if self.sat > 0 else "", self.sat,
                                        "+" if self.con > 0 else "", self.con))
        if self.ev != 0:
            s.append(R.ev_label(self.ev))
        if self.dro != R.DRO_AUTO:
            s.append("DRO " + ("off" if self.dro == 0 else str(self.dro)))
        if self.wb_mode == R.WB_KELVIN:
            s.append("%dK" % self.kelvin)
        if self.ab != 0:
            s.append("A%d" % self.ab if self.ab > 0 else "B%d" % (-self.ab))
        if self.gm != 0:
            s.append("G%d" % self.gm if self.gm > 0 else "M%d" % (-self.gm))
        return "  ".join(s)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


# ------------------------------------------------------------ validation
def problem(r):
    """None when every value is one the store takes; else the first offender, as 'key value'"""
    if not R.style_known(r.style):
        return "style ?%d" % r.style
    if not R.in_range(r.sat, R.ADJ_MIN, R.ADJ_MAX):
        return "saturation %d" % r.sat
    if not R.in_range(r.con, R.ADJ_MIN, R.ADJ_MAX):
        return "contrast %d" % r.con
    if not R.in_range(r.sharp, R.ADJ_MIN, R.ADJ_MAX):
        return "sharpness %d" % r.sharp
    if not R.in_range(r.pe, R.PE_MIN, R.PE_MAX):
        return "effect ?%d" % r.pe
    sv = R.sub_values(r.pe)
    if sv is not None:
        if not R.in_range(r.sub, 0, len(sv) - 1):
            return "effect-option ?%d" % r.sub
    elif r.sub != 0:
        return "effect-option ?%d" % r.sub
    if r.wb_mode not in (0, R.WB_AUTO, R.WB_KELVIN):
        return "white-balance ?%d" % r.wb_mode
    if r.wb_mode == R.WB_KELVIN and not R.kelvin_ok(r.kelvin):
        return "white-balance %dK" % r.kelvin
    if not R.in_range(r.ab, R.AB_MIN, R.AB_MAX):
        return "amber-blue %d" % r.ab
    if not R.in_range(r.gm, R.GM_MIN, R.GM_MAX):
        return "green-magenta %d" % r.gm
    if not R.in_range(r.ev, R.EV_MIN, R.EV_MAX):
        return "exposure %d" % r.ev
    if not R.in_range(r.dro, 0, R.DRO_AUTO):
        return "dro %d" % r.dro
    return None


def name_problem(name, taken=(), self_name=None):
    """why a name cannot be used, or None; mirrors CustomRecipes.nameProblem"""
    n = (name or "").strip()
    if not n:
        return "name_empty"
    if len(n) > R.NAME_MAX:
        return "name_too_long"
    for c in n:
        if not R.name_char(c):
            return "name_bad_chars"
    low = n.lower()
    for t in taken:
        if t.lower() == low and (self_name is None or self_name.lower() != low):
            return "name_taken (%s)" % t
    return None


# ------------------------------------------------------------ file names (8.3)
def file_name(name, taken_files):
    """the 8.3 name a recipe is kept in: first eight [A-Z0-9] of the name + .YML, numeric suffix on clash"""
    b = "".join(c for c in name.upper() if c.isascii() and (c.isalpha() or c.isdigit()))
    base = b[:8] if b else "RECIPE"
    lower = {t.lower() for t in taken_files}
    f = base + R.EXT
    n = 2
    while f.lower() in lower:
        num = str(n)
        f = base[:max(0, 8 - len(num))] + num + R.EXT
        n += 1
    return f


def stem(file_name_):
    if not file_name_:
        return ""
    return file_name_[:-len(R.EXT)] if file_name_.lower().endswith(R.EXT.lower()) else file_name_


# ------------------------------------------------------------ write (RecipeFormatV1)
_HEADER = (
    "# Recipe Lab custom recipe. Keep it in the %s folder of a memory card, under a name of\n"
    "# up to eight letters or digits and .YML: the camera reads no longer file names. Its own name is below.\n"
    "# Edit with care: a value outside the range beside it makes the app skip this file.\n" % R.DIR
)


def _line(parts, key, value, comment=None):
    line = "%s: %s" % (key, value)
    if comment is not None:
        if len(line) < 28:
            line += " " * (28 - len(line))
        line += " # " + comment
    parts.append(line)


def _quoted(v):
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _signed(v):
    return "+%d" % v if v > 0 else str(v)


def write_v1(r, made_on=None):
    """the exact text RecipeFormatV1.write produces"""
    parts = [_HEADER]
    _line(parts, "format", "1")
    _line(parts, "name", _quoted(r.name))
    if made_on is not None and made_on.strip():
        _line(parts, "made-on", _quoted(made_on.strip()), "the camera it was saved on")
    _line(parts, "style", R.STYLE_NAMES[r.style], " ".join(R.STYLE_NAMES[i] for i in range(len(R.STYLE_NAMES)) if R.style_known(i)))
    _line(parts, "saturation", _signed(r.sat), "-3 .. +3")
    _line(parts, "contrast", _signed(r.con), "-3 .. +3")
    _line(parts, "sharpness", _signed(r.sharp), "-3 .. +3")
    _line(parts, "effect", R.PE_KEYS[r.pe], " ".join(R.PE_KEYS))
    sv = R.sub_values(r.pe)
    if sv is not None:
        _line(parts, "effect-option", sv[r.sub], " ".join(sv))
    wb = "%dK" % r.kelvin if r.wb_mode == R.WB_KELVIN else "auto" if r.wb_mode == R.WB_AUTO else "keep"
    _line(parts, "white-balance", wb, "auto, keep, or 2500K .. 9900K in 100K steps")
    _line(parts, "amber-blue", _signed(r.ab), "-7 (blue) .. +7 (amber)")
    _line(parts, "green-magenta", _signed(r.gm), "-7 (magenta) .. +7 (green)")
    _line(parts, "exposure", R.ev_label(r.ev), "-5.0 .. +5.0 in thirds: .0 .3 .7")
    dro = "auto" if r.dro == R.DRO_AUTO else "off" if r.dro == 0 else str(r.dro)
    _line(parts, "dro", dro, "off, auto, 1 .. 5")
    return "\n".join(parts) + "\n"


# ------------------------------------------------------------ read
def _parse_kv(text):
    """naive YAML: key: value, ignoring blanks and # comments. Values keep their quotes off."""
    kv = {}
    for raw in text.splitlines():
        line = raw.split(" # ", 1)[0] if " # " in raw else raw
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        kv[k.strip()] = v.strip()
    return kv


def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return v


def _integer(v):
    import re
    return int(v[1:] if v.startswith("+") else v) if re.fullmatch(r"[+-]?\d{1,3}", v) else None


def read_v1(text, file_name_):
    """(recipe, None) or (None, reason); mirrors RecipeFormatV1.read"""
    kv = _parse_kv(text)
    name = _unquote(kv.get("name", "")) if kv.get("name") else ""
    if not name:
        name = stem(file_name_)
    np_ = name_problem(name, (), None)
    if np_:
        return None, np_

    style = R.STYLE_MIN
    if "style" in kv:
        style = R.index_of(R.STYLE_NAMES, kv["style"])
        if style < 0:
            return None, "style %s" % kv["style"]

    adj = [0, 0, 0]
    for i, key in enumerate(("saturation", "contrast", "sharpness")):
        if key in kv:
            n = _integer(kv[key])
            if n is None or not R.in_range(n, R.ADJ_MIN, R.ADJ_MAX):
                return None, "%s %s" % (key, kv[key])
            adj[i] = n

    pe = 0
    if "effect" in kv:
        pe = R.index_of(R.PE_KEYS, kv["effect"])
        if pe < 0:
            return None, "effect %s" % kv["effect"]

    sub = 0
    sv = R.sub_values(pe)
    if sv is not None and "effect-option" in kv:
        sub = R.index_of(sv, kv["effect-option"])
        if sub < 0:
            return None, "effect-option %s" % kv["effect-option"]

    wb, kelvin = R.WB_AUTO, 0
    if "white-balance" in kv:
        import re
        w = kv["white-balance"].lower().replace(" ", "")
        if w == "auto":
            wb = R.WB_AUTO
        elif w == "keep":
            wb = 0
        elif re.fullmatch(r"\d{4}k?", w) and R.kelvin_ok(int(w.replace("k", ""))):
            wb = R.WB_KELVIN
            kelvin = int(w.replace("k", ""))
        else:
            return None, "white-balance %s" % kv["white-balance"]

    fine = [0, 0]
    for i, key in enumerate(("amber-blue", "green-magenta")):
        if key in kv:
            n = _integer(kv[key])
            if n is None or not R.in_range(n, R.AB_MIN, R.AB_MAX):
                return None, "%s %s" % (key, kv[key])
            fine[i] = n

    ev = 0
    if "exposure" in kv:
        t = R.ev_from_text(kv["exposure"])
        if t is None or not R.in_range(t, R.EV_MIN, R.EV_MAX):
            return None, "exposure %s" % kv["exposure"]
        ev = t

    dro = R.DRO_AUTO
    if "dro" in kv:
        d = kv["dro"].lower()
        if d == "auto":
            dro = R.DRO_AUTO
        elif d == "off":
            dro = 0
        elif d in ("1", "2", "3", "4", "5"):
            dro = int(d)
        else:
            return None, "dro %s" % kv["dro"]

    r = Recipe(group=R.CUSTOM, name=name.strip(), style=style, sat=adj[0], con=adj[1], sharp=adj[2],
               wb_mode=wb, kelvin=kelvin, ab=fine[0], gm=fine[1], pe=pe, ev=ev, dro=dro, sub=sub)
    p = problem(r)
    return (None, p) if p else (r, None)


# ------------------------------------------------------------ folder load / save
def load_dir(directory):
    """every .YML in a folder, A-Z by name; returns (entries[(recipe, file)], skipped[strings])"""
    entries, skipped = [], []
    if not directory or not os.path.isdir(directory):
        return entries, skipped
    by_name = {}
    for fn in sorted(os.listdir(directory), key=lambda s: s.lower()):
        path = os.path.join(directory, fn)
        if fn.startswith(".") or not fn.lower().endswith(R.EXT.lower()) or not os.path.isfile(path):
            continue
        if os.path.getsize(path) > R.MAX_BYTES:
            skipped.append("%s: too large" % fn)
            continue
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            skipped.append("%s: %s" % (fn, e))
            continue
        r, err = read_v1(text, fn)
        if err is None and r.name.lower() in by_name:
            err = "duplicate name (also in %s)" % by_name[r.name.lower()]
        if err is not None:
            skipped.append("%s: %s" % (fn, err))
            continue
        by_name[r.name.lower()] = fn
        entries.append((r, fn))
    entries.sort(key=lambda e: e[0].name.lower())
    return entries, skipped


def save_dir(directory, r, made_on=None, old_file=None):
    """write r into directory (creating it), replacing old_file; returns the file name it landed in"""
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    taken = []
    for n in os.listdir(directory):
        if old_file is None or n.lower() != old_file.lower():
            taken.append(n)
    fname = file_name(r.name, taken)
    tmp = os.path.join(directory, R.TMP)
    target = os.path.join(directory, fname)
    if os.path.exists(tmp):
        os.remove(tmp)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(write_v1(r, made_on))
        f.flush()
        os.fsync(f.fileno())
    if os.path.exists(target):
        os.remove(target)
    os.replace(tmp, target)
    return fname
