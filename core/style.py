"""Build the target appearance a fit aims at — from a .cube, or from a photographer's portfolio.

Everything is expressed as a 16x16 Lab signature of the *reference frame* (the FACTORY (ST)
calibration shot), the same quantity core.model predicts, so target and prediction are directly
comparable.
"""
import os

import numpy as np
from PIL import Image, ImageFilter

from .colorlab import lab2rgb, rgb2lab
from .model import SAMPLES, SIG

REF_FRAME = os.path.join(SAMPLES, "01-factory-st.jpg")

_REF_CACHE = {}


def _to_signature(rgb):
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((SIG, SIG), Image.LANCZOS)
    return rgb2lab(np.asarray(im, float) / 255.0)


def reference_rgb(size=None):
    """the FACTORY (ST) calibration shot, decoded once per requested size"""
    if size not in _REF_CACHE:
        im = Image.open(REF_FRAME).convert("RGB")
        if size is not None:
            im = im.resize((size, size), Image.LANCZOS)
        _REF_CACHE[size] = np.asarray(im, float) / 255.0
    return _REF_CACHE[size]


def base_signature():
    """the reference frame's own appearance, as the model's zero point"""
    return _to_signature(reference_rgb())


def target_from_cube(cube):
    """apply the cube to the full-res reference frame, then reduce to the Lab signature"""
    return _to_signature(cube.apply(reference_rgb()))


def target_from_portfolio(paths, limit=24):
    """the average Lab signature of a set of photos.

    Caveat: absolute Lab is scene dependent, so this is a *statistical* target. It is at its best
    when the portfolio shares the camera's typical scene and lighting.
    """
    sigs, thumbs = [], []
    for p in list(paths)[:limit]:
        try:
            im = Image.open(p).convert("RGB")
        except OSError:
            continue
        im.thumbnail((512, 512), Image.LANCZOS)
        rgb = np.asarray(im, float) / 255.0
        sigs.append(_to_signature(rgb))
        thumbs.append(thumb_rgb(rgb))
    if not sigs:
        return None, None
    return np.mean(sigs, axis=0), np.mean(thumbs, axis=0)


def load_rgb(path, max_side=1600):
    """a photo as a float RGB array in [0,1], capped so the preview stays light"""
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    return np.asarray(im, float) / 255.0


def _fmt_shutter(v):
    if not v:
        return None
    v = float(v)
    if v >= 1.0:
        return ("%gs" % v)
    return "1/%ds" % round(1.0 / v)


def exif_summary(path):
    """the exposure metadata shown under the histogram, read from the file's own EXIF.

    Returns a dict with iso / shutter / aperture / focal, each a short formatted string or None when
    the file has no such tag — a RAW that PIL cannot open, or a PNG, comes back all None."""
    out = {"iso": None, "shutter": None, "aperture": None, "focal": None}
    if not path:
        return out
    try:
        with Image.open(path) as im:
            ex = im.getexif()
    except (OSError, ValueError):
        return out
    iso = ex.get(0x8827)
    if isinstance(iso, (tuple, list)):
        iso = iso[0] if iso else None
    if iso:
        out["iso"] = str(int(iso))
    out["shutter"] = _fmt_shutter(ex.get(0x829A))
    fnum = ex.get(0x829D)
    if fnum:
        out["aperture"] = "f/%g" % float(fnum)
    focal = ex.get(0x920A)
    if focal:
        out["focal"] = "%gmm" % float(focal)
    return out


def thumb_rgb(rgb, size=128):
    a = np.clip(np.asarray(rgb, float), 0, 1)
    im = Image.fromarray((a * 255 + 0.5).astype(np.uint8)).resize((size, size), Image.LANCZOS)
    return np.asarray(im, float) / 255.0


def target_from_pair(before_rgb, after_rgb):
    """the appearance to aim at, inferred from a before/after pair.

    A portfolio averages *absolute* Lab across scenes, so the scenes' own colour rides along with
    the look. A pair cancels that: it is the same scene, graded. The difference (after − before) is
    the look by itself, and carrying it onto the reference frame's own appearance gives a target the
    forward model can be compared with directly. The two frames must be the same scene from the same
    spot (one frame shot twice, or a virtual copy) — otherwise the difference is not a look.

    Returns (target_lab, look_lab, thumb).
    """
    look = _to_signature(after_rgb) - _to_signature(before_rgb)
    return base_signature() + look, look, thumb_rgb(after_rgb)


def signature_to_rgb(lab):
    return np.clip(lab2rgb(lab), 0, 1)


# ------------------------------------------------------------ simulating a recipe on a real photo
#
# The preview is an explicit *simulation*, not a transform learned from the calibration table, because
# that table cannot teach most of these fields. Over the 77 sampled recipe vectors:
#
#     sub     constant (one value)           pe      4 distinct values
#     wb_mode 2 distinct values              dro     4 distinct values
#     ev      only -1..+3 thirds             sharp   6 distinct values
#     kelvin  0 / 6000, 8 distinct values    ab, gm  6 distinct values each
#
# Fitting one affine matrix between the reference frame and the model's prediction (what this module
# used to do) therefore left most sliders doing nothing visible, and got the sign of some of them
# wrong: measured on a test image, ±5 stops of exposure moved mean luminance by 0.006, and the
# creative style moved it by 0.0002. A single linear map also cannot express a tone curve or a
# saturation that behaves differently in the highlights.
#
# So every field now drives a named, monotone operation, in the camera's own order:
#
#     white balance -> exposure -> DRO -> tone curve -> saturation -> picture effect -> sharpness
#
# The one part with real camera data behind it is the creative-style character: _style_stats measures
# each style's colour cast and chroma from the graded calibration shots. The residual readout of a fit
# is a separate quantity and still comes from core.model.

LUMA_W = np.array([0.2126, 0.7152, 0.0722], np.float32)   # float32 throughout: a preview is dragged live

NEUTRAL_K = 5600.0        # the colour temperature whose white-balance gain is 1
MONO_STYLE = 6            # creative style index of B&W
SEPIA_STYLE = 14

# DRO: off, level 1..5, auto
DRO_LEVEL = {0: 0.0, 1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 1.0, 6: 0.65}

SEPIA_TINT = np.array([1.12, 1.0, 0.82], np.float32)

# Picture Effect: sat = saturation multiplier, con = contrast bias in the -3..3 units of the slider,
# lift = a linear-light gain, fade = lifted blacks / lowered whites, vign = vignette strength,
# post = posterisation levels, blur = gaussian radius, band = the miniature's banded blur,
# mono = force B&W, tint = a per-channel cast.
EFFECTS = {
    0: {},
    1: dict(sat=1.15, con=0.2, vign=0.55),                # toy camera
    2: dict(sat=1.45, con=0.3),                           # pop colour
    3: dict(post=5),                                      # posterisation
    4: dict(sat=0.82, fade=0.10, tint=np.array([1.06, 0.99, 0.90])),   # retro
    5: dict(lift=0.35, con=-0.3, tint=np.array([0.97, 1.0, 1.06])),    # soft high key
    6: dict(sat=0.0),                                     # part colour (the hue is the sub value)
    7: dict(mono=True, con=0.5),                          # rough mono
    8: dict(blur=2.2),                                    # soft focus
    9: dict(lift=0.25, sat=1.25, con=0.35),               # hdr art
    10: dict(mono=True, tint=np.array([1.06, 1.0, 0.90])),  # rich tone mono
    11: dict(band=True),                                  # miniature
    12: dict(post=6, sat=1.3),                            # illustration
    13: dict(post=8, blur=1.2),                           # watercolour
}

# the sub parameters that are a colour choice rather than a mode (see core.ranges.sub_values)
SUB_TINTS = {
    (1, 1): np.array([0.94, 1.0, 1.10]),     # toy: cool
    (1, 2): np.array([1.10, 1.0, 0.92]),     # toy: warm
    (1, 3): np.array([0.95, 1.06, 0.95]),    # toy: green
    (1, 4): np.array([1.06, 0.94, 1.06]),    # toy: magenta
    (5, 0): np.array([0.96, 1.0, 1.08]),     # high key: blue
    (5, 1): np.array([1.07, 0.98, 1.02]),    # high key: pink
    (5, 2): np.array([0.96, 1.04, 0.96]),    # high key: green
}
# every per-channel multiplier is float32, so a preview stays float32 end to end
for _e in EFFECTS.values():
    if "tint" in _e:
        _e["tint"] = np.asarray(_e["tint"], np.float32)
for _k, _v in list(SUB_TINTS.items()):
    SUB_TINTS[_k] = np.asarray(_v, np.float32)

# sRGB <-> linear light, through a lookup table: the exact piecewise power law costs two pow() passes
# over the whole preview, which is too slow to drag a slider against, and 1024 steps is far finer than
# an 8-bit preview can show. Each direction gets its own table, uniform in *its own* input space, so a
# plain gather (see _lut) is exact enough — a table keyed on a non-uniform grid would need an interpolated
# search, which is what np.interp does and what made it the slowest part of the preview.
_LUT_N = 1024
_LUT_X = np.linspace(0.0, 1.0, _LUT_N)
_S2L = np.where(_LUT_X <= 0.04045, _LUT_X / 12.92, ((_LUT_X + 0.055) / 1.055) ** 2.4).astype(np.float32)
_L2S = np.where(_LUT_X <= 0.0031308, _LUT_X * 12.92,
                1.055 * np.maximum(_LUT_X, 0.0) ** (1.0 / 2.4) - 0.055).astype(np.float32)


def _lut(v, table):
    """look a table up on its own uniform grid — a gather over 1024 steps runs over twice as fast as
    np.interp and agrees with it to better than 1e-7, far below what an 8-bit preview can show"""
    pos = np.clip(v, 0.0, 1.0) * (_LUT_N - 1)
    i0 = pos.astype(np.int32)
    frac = pos - i0.astype(np.float32)
    i1 = np.minimum(i0 + 1, _LUT_N - 1)
    return table[i0] * (1.0 - frac) + table[i1] * frac


def to_linear(x):
    return _lut(x, _S2L)


def to_srgb(x):
    return _lut(x, _L2S)


def temp_rgb(kelvin):
    """the colour of a blackbody at a temperature, in 0..1 (the usual Tanner Helland fit)"""
    t = float(kelvin) / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * (t - 60.0) ** -0.1332047592
    if t <= 66:
        g = 99.4708025861 * np.log(max(t, 1.0)) - 161.1195681661
    else:
        g = 288.1221695283 * (t - 60.0) ** -0.0755148492
    if t >= 66:
        b = 255.0
    elif t <= 19:
        b = 0.0
    else:
        b = 138.5177312231 * np.log(t - 10.0) - 305.0447927307
    return np.clip(np.array([r, g, b]), 1.0, 255.0).astype(np.float32) / 255.0


def wb_gains(kelvin, ab, gm):
    """the linear-light RGB gains of a colour temperature and the two tint axes.

    5600 K is the neutral point, so a recipe that leaves the kelvin unset (0) gets no cast at all."""
    gains = np.ones(3)
    if kelvin and float(kelvin) > 0:
        gains = temp_rgb(float(kelvin)) / temp_rgb(NEUTRAL_K)
    gains = gains / gains[1]                                   # green is the reference channel
    amber = 0.05 * float(ab)                                   # + amber / - blue
    green = 0.05 * float(gm)                                   # + green / - magenta
    gains = gains * np.array([1.0 + amber, 1.0 + green, 1.0 - amber])
    return np.clip(gains, 0.15, 3.0).astype(np.float32)


def dro_lift(lin, level):
    """DRO lifts the shadows with a gain that fades out before the midtones"""
    k = DRO_LEVEL.get(int(level), 0.0)
    if k <= 0:
        return lin
    w = np.clip(1.0 - lin / 0.22, 0.0, 1.0) ** 1.5
    return lin * (1.0 + 0.9 * k * w) + 0.006 * k * w


def tone(enc, con):
    """the contrast slider, as an S-curve above zero and a flattening below it, pivoting on mid grey"""
    s = float(np.clip(con, -3.0, 3.0)) / 3.0
    if abs(s) < 1e-6:
        return enc
    s_curve = enc * enc * (3.0 - 2.0 * enc)          # smoothstep: a real S around 0.5
    flat = 0.5 + (enc - 0.5) * 0.55                  # the same pivot, less contrast
    target = s_curve if s > 0 else flat
    return enc + abs(s) * 0.75 * (target - enc)


def saturate(enc, sat, mult=1.0):
    """scale chroma around each pixel's own luma; `mult` is the style's own saturation"""
    amount = max(0.0, mult * (1.0 + 0.28 * float(np.clip(sat, -3.0, 3.0))))
    luma = (enc * LUMA_W).sum(-1, keepdims=True)
    return luma + (enc - luma) * amount


def to_mono(enc, tint=None):
    """B&W, optionally toned"""
    out = np.repeat((enc * LUMA_W).sum(-1, keepdims=True), 3, axis=-1)
    return out if tint is None else out * tint


def posterize(enc, levels):
    q = max(2, int(levels)) - 1
    return np.round(enc * q) / q


def fade(enc, amount):
    """lifted blacks and lowered whites — the matte look of a faded print"""
    return enc * (1.0 - 2.0 * amount) + amount


def vignette(enc, strength):
    h, w = enc.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    d = np.sqrt(((yy - cy) / max(cy, 1.0)) ** 2 + ((xx - cx) / max(cx, 1.0)) ** 2) / np.sqrt(2.0)
    mask = 1.0 - strength * np.clip((d - 0.35) / 0.65, 0.0, 1.0) ** 1.6
    return enc * mask[..., None].astype(np.float32)


def _blur(rgb, radius):
    im = Image.fromarray((np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255.0


def _miniature(enc):
    """the miniature effect: keep a horizontal band sharp and blur away from it"""
    h = enc.shape[0]
    blurred = _blur(enc, max(1.6, h / 60.0))
    keep = np.clip(np.abs(np.linspace(0.0, 1.0, h)[:, None] - 0.5) / 0.30, 0.0, 1.0) ** 0.8
    m = keep[..., None].astype(np.float32)
    return enc * (1.0 - m) + blurred * m


def _part_colour(enc, sub):
    """part colour: keep the pixels near one hue, grey everything else"""
    r, g, b = enc[..., 0], enc[..., 1], enc[..., 2]
    if sub == 1:
        keep = g >= np.maximum(r, b)
    elif sub == 2:
        keep = b >= np.maximum(r, g)
    elif sub == 3:
        keep = np.minimum(r, g) >= b
    else:
        keep = r >= np.maximum(g, b)
    grey = np.repeat((enc * LUMA_W).sum(-1, keepdims=True), 3, axis=-1)
    return np.where(keep[..., None], enc, grey)


def unsharp(enc, sharp):
    """sharpness: unsharp mask above zero, a softening blur below it"""
    s = float(np.clip(sharp, -3.0, 3.0)) / 3.0
    if abs(s) < 1e-6:
        return enc
    if s > 0:
        return enc + 0.55 * s * (enc - _blur(enc, 1.3))
    return _blur(enc, 2.4 * -s)


_STYLE_CACHE = {}


def _style_stats(model):
    """per creative style, the colour cast and chroma measured from the graded calibration frames.

    Each sampled style appears among the 77 shots, so averaging the shots that share a style averages
    the other fields away and leaves that style's typical look. This is the one part of the simulation
    with real camera data behind it, which is why the creative styles differ from one another for a
    measured reason rather than a guessed one. The cast is normalised to keep its luminance."""
    cached = _STYLE_CACHE.get(id(model))
    if cached is not None:
        return cached[1]
    stats = {}
    if model is not None and getattr(model, "imgsmall", None) is not None:
        px = model.imgsmall.astype(np.float64)
        means = px.mean(axis=(1, 2))
        chroma = np.abs(px - (px * LUMA_W).sum(-1, keepdims=True)).mean(axis=(1, 2))
        all_lum = max(float((means * LUMA_W).sum(-1).mean()), 1e-6)
        all_chroma = max(float(chroma.mean()), 1e-6)
        by_style = {}
        for i, p in enumerate(model.params):
            by_style.setdefault(int(p[0]), []).append(i)
        for style, idx in by_style.items():
            mean = means[idx].mean(0)
            gains = mean / all_lum
            gains = gains / float(gains @ LUMA_W)          # keep the style's own luminance
            stats[style] = dict(gains=gains.astype(np.float32),
                                sat=float(chroma[idx].mean()) / all_chroma)
    _STYLE_CACHE[id(model)] = (model, stats)               # hold the model, so its id cannot be reused
    return stats


def apply_look(model, params, rgb):
    """simulate a recipe on a real photo, in the camera's own order of operations.

    An explicit simulation rather than a transform learned from the calibration table (see the note
    above): every field drives a named, monotone operation, so a slider always moves the picture the
    way its label says. The creative style's cast and chroma are measured from the real calibration
    frames; see _style_stats."""
    style = int(float(params[0]))
    sat, con, sharp = float(params[1]), float(params[2]), float(params[3])
    kel, ab, gm = float(params[5]), float(params[6]), float(params[7])
    pe = int(float(params[8]))
    ev, dro, sub = float(params[9]), int(float(params[10])), int(float(params[11]))

    eff = EFFECTS.get(pe, {})
    st = _style_stats(model).get(style, {})

    lin = to_linear(np.asarray(rgb, np.float32))
    lin = lin * wb_gains(kel, ab, gm)
    gains = st.get("gains")
    if gains is not None:
        lin = lin * gains                                  # the style's own colour cast
    lin = lin * 2.0 ** (ev / 3.0) * (1.0 + eff.get("lift", 0.0))
    lin = dro_lift(lin, dro)

    enc = to_srgb(lin) * eff.get("tint", 1.0) * SUB_TINTS.get((pe, sub), 1.0)
    enc = tone(enc, con + eff.get("con", 0.0))
    enc = saturate(enc, sat, float(st.get("sat", 1.0)) * eff.get("sat", 1.0))

    if eff.get("post"):
        enc = posterize(to_mono(enc) if (pe == 3 and sub == 1) else enc, eff["post"])
    if pe == 6:
        enc = _part_colour(enc, sub)
    if eff.get("vign"):
        enc = vignette(enc, eff["vign"])
    if eff.get("fade"):
        enc = fade(enc, eff["fade"])
    if eff.get("mono") or style == MONO_STYLE or style == SEPIA_STYLE or (pe == 3 and sub == 1):
        tint = SEPIA_TINT if style == SEPIA_STYLE else eff.get("tint")
        enc = to_mono(enc, tint)
    if eff.get("blur"):
        enc = _blur(enc, eff["blur"])
    if eff.get("band"):
        enc = _miniature(enc)
    return np.clip(unsharp(enc, sharp), 0.0, 1.0)
