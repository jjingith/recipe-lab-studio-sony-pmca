"""Build the target appearance a fit aims at — from a .cube, or from a photographer's portfolio.

Everything is expressed as a 16x16 Lab signature of the *reference frame* (the FACTORY (ST)
calibration shot), the same quantity core.model predicts, so target and prediction are directly
comparable.
"""
import os

import numpy as np
from PIL import Image

from .colorlab import lab2rgb, rgb2lab
from .model import SAMPLES, SIG, SMALL

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


# ------------------------------------------------------------ a recipe applied to a real photo
def transform_from_model(model, params):
    """the affine sRGB mapping (4x3) that carries the reference frame to what the model predicts for
    params — one global colour shift, which is what can be carried onto an arbitrary photo"""
    ref = reference_rgb(SMALL).reshape(-1, 3)
    tgt = model.blend(params).reshape(-1, 3)
    if ref.shape[0] > 4096:                       # the fit needs no more than a few thousand samples
        step = ref.shape[0] // 4096 + 1
        ref, tgt = ref[::step], tgt[::step]
    a = np.hstack([ref, np.ones((ref.shape[0], 1))])
    m, *_ = np.linalg.lstsq(a, tgt, rcond=None)
    return m


def apply_look(model, params, rgb):
    """approximate a recipe on a real photo: fit the model's global colour shift on the reference
    frame, then apply it to the photo. An approximation of the camera's own pipeline, not the
    pipeline itself — the residual readout is what tells how far off it is."""
    m = transform_from_model(model, params)
    x = np.clip(np.asarray(rgb, float), 0, 1)
    shape = x.shape
    a = np.hstack([x.reshape(-1, 3), np.ones((x.shape[0] * x.shape[1], 1))])
    return np.clip(a @ m, 0, 1).reshape(shape)
