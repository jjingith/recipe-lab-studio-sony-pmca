"""The offline forward model: RL recipe parameters -> appearance.

Built from the 77 calibration frames in data/calib/samples: one base image graded under 77
different recipes. We regress a linear map  params ->  Lab appearance  (the same feature vector
and ridge solve as the original fit4.py), cache it, and expose

  - signature(params): the 16x16 Lab appearance the reference frame would take
  - blend(params):     a low-res RGB image blended from the 77 real graded frames (for preview)

Honesty note: this only predicts the look *on the reference frame*. It cannot transfer a look to
an unrelated photo, which is why a fitted recipe is shown as approximation + residual, and a cube
or portfolio target is previewed exactly (see cube.py / style.py).
"""
import os
import re

import numpy as np
from PIL import Image

from . import ranges as R
from .colorlab import lab2rgb, rgb2lab

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "data", "calib", "samples")
CACHE = os.path.join(ROOT, "data", "model.npz")
SIG = 16          # signature grid
SMALL = 128       # blend preview size

# recipes in the table that have no calibration frame (added after the 77-frame shoot)
NO_SAMPLE = {"Kodak Aerocolor IV 2460", "Kodak 2383 print", "Foma Pan 100", "Tatsuo Suzuki B&W"}


def slug(name):
    # mirrors the RL fork's sample naming: "&"->"and", "+"->" plus ", then runs of
    # non-alphanumeric become a single "-":  "GR Hi-Contrast B&W" -> gr-hi-contrast-bandw
    s = name.lower().replace("+", " plus ").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def fvec(v):
    """params -> feature vector (27) ; the bias column is added by the model's X"""
    style, sat, con, sharp, wbm, kel, ab, gm, pe, ev, dro, sub = v
    f = [0.0] * 15
    if 0 <= int(style) < 15:
        f[int(style)] = 1.0
    wb = [0.0, 0.0, 0.0]
    wb[{0: 0, 1: 1, 14: 2}.get(int(wbm), 0)] = 1.0
    return np.array(f + [sat, con, sharp] + wb + [kel / 1000.0, ab, gm, pe, ev, dro], float)


def _feats(rgb):
    return rgb2lab(rgb).reshape(-1) / 50.0


def _solve(X, Y, lam=1e-3):
    return np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ Y)


class Model:
    def __init__(self):
        self.names = []            # the 77 sampled recipe names, in file order
        self.params = []           # their 12-field param vectors
        self.X = None
        self.Y = None
        self.W = None
        self.loo = None            # per-recipe Lab RMSE from leave-one-out
        self.img16 = None          # (77,16,16,3) sRGB
        self.imgsmall = None       # (77,128,128,3) sRGB

    # ------------------------------------------------------------ build / load
    @classmethod
    def load(cls, rebuild=False):
        m = cls()
        if not rebuild and os.path.exists(CACHE):
            z = np.load(CACHE, allow_pickle=True)
            m.names = list(z["names"])
            m.params = [list(p) for p in z["params"]]
            m.X, m.Y, m.W, m.loo = z["X"], z["Y"], z["W"], z["loo"]
            m.img16, m.imgsmall = z["img16"], z["imgsmall"]
            return m
        return m.build()

    def build(self):
        import json
        builtins = json.load(open(os.path.join(ROOT, "data", "builtins.json"), encoding="utf-8"))["recipes"]
        by_slug = {slug(d["name"]): d for d in builtins}
        files = sorted(f for f in os.listdir(SAMPLES) if f.lower().endswith(".jpg"))
        rows, imgs16, smalls = [], [], []
        for fn in files:
            base = fn[3:-4] if fn[2] == "-" else fn[:-4]        # strip "NN-" and ".jpg"
            d = by_slug.get(base)
            if d is None:
                raise RuntimeError("sample %s has no matching recipe (slug %s)" % (fn, base))
            v = [d[k] for k in R.FIELDS]
            rows.append((d["name"], v))
            im = np.asarray(Image.open(os.path.join(SAMPLES, fn)).convert("RGB"), float) / 255.0
            imgs16.append(np.asarray(Image.fromarray((im * 255).astype(np.uint8)).resize((SIG, SIG), Image.LANCZOS), float) / 255.0)
            smalls.append(np.asarray(Image.fromarray((im * 255).astype(np.uint8)).resize((SMALL, SMALL), Image.LANCZOS), float) / 255.0)

        self.names = [r[0] for r in rows]
        self.params = [r[1] for r in rows]
        self.img16 = np.stack(imgs16)
        self.imgsmall = np.stack(smalls)

        self.X = np.hstack([np.stack([fvec(v) for v in self.params]), np.ones((len(rows), 1))])
        self.Y = np.stack([_feats(im) for im in self.img16])
        self.W = _solve(self.X, self.Y)

        errs = []
        for i in range(len(rows)):
            keep = [j for j in range(len(rows)) if j != i]
            w = _solve(self.X[keep], self.Y[keep])
            pred = (self.X[i:i + 1] @ w)[0] * 50
            truth = self.Y[i] * 50
            errs.append(float(np.sqrt(((pred - truth) ** 2).reshape(-1, 3).mean(0).sum())))
        self.loo = np.array(errs)

        np.savez_compressed(CACHE, names=np.array(self.names, dtype=object),
                            params=np.array(self.params, float), X=self.X, Y=self.Y, W=self.W,
                            loo=self.loo, img16=self.img16, imgsmall=self.imgsmall)
        return self

    # ------------------------------------------------------------ predict
    def signature(self, params):
        """12-field params -> (SIG,SIG,3) Lab appearance of the reference frame (real Lab units)"""
        f = np.concatenate([fvec(params), [1.0]])
        lab50 = (f @ self.W).reshape(SIG, SIG, 3)
        return lab50 * 50.0

    def signature_rgb(self, params):
        """the predicted reference-frame signature as sRGB, for display"""
        return np.clip(lab2rgb(self.signature(params)), 0, 1)

    def blend(self, params, k=8):
        """a full (SMALL,SMALL) RGB image: an RBF blend of the k nearest real graded frames"""
        P = np.stack([fvec(v) for v in self.params])
        q = fvec(params)
        dist = np.linalg.norm(P - q, axis=1)
        order = np.argsort(dist)[:k]
        d = dist[order]
        w = np.exp(-(d / max(d[-1], 1e-6)) ** 2)
        w = w / w.sum()
        return np.clip(np.tensordot(w, self.imgsmall[order], axes=(0, 0)), 0, 1)

    def nearest(self, params, k=5):
        """the k sampled recipe names closest to params, with distances"""
        P = np.stack([fvec(v) for v in self.params])
        dist = np.linalg.norm(P - fvec(params), axis=1)
        order = np.argsort(dist)[:k]
        return [(self.names[i], float(dist[i])) for i in order]

    # ------------------------------------------------------------ diagnostics
    def loo_stats(self):
        return dict(mean=float(self.loo.mean()), median=float(np.median(self.loo)),
                    best=float(self.loo.min()), worst=float(self.loo.max()))

    def lab_residual(self, params, target_lab):
        """per-channel Lab RMSE between a recipe's predicted signature and a target signature"""
        pred = self.signature(params)
        return float(np.sqrt(((pred - target_lab) ** 2).reshape(-1, 3).mean(0).sum()))

    def breakdown(self, params, target_lab, base_lab=None, shadow=33.0, highlight=66.0):
        """the single Lab residual, split into the parts a photographer names.

        Every term is an RMS over the 16x16 signature grid, in Lab units, so it compares to the
        overall residual (and to the ≤2 tolerance) directly. The shadow / highlight bands are cut by
        the *base* frame's own luminance — the scene's regions, not the graded result — so a look
        that lifts shadows is measured where the shadows actually are. 'skin' is read only over the
        warm mid-tone window a face falls in; a frame with almost none of it reports None. 'tone' is
        the mean of the two bands. 'overall' is the single number the RESIDUAL row shows.
        """
        pred = self.signature(params)
        tgt = np.asarray(target_lab, float)
        ref = np.asarray(base_lab, float) if base_lab is not None else tgt
        d = pred - tgt
        dL, da, db = d[..., 0], d[..., 1], d[..., 2]
        dC = np.hypot(pred[..., 1], pred[..., 2]) - np.hypot(tgt[..., 1], tgt[..., 2])
        Lr = ref[..., 0]
        sh, hi = Lr < shadow, Lr > highlight
        skin = _skin_mask(ref)

        def rms(x):
            x = np.asarray(x, float)
            return float(np.sqrt(np.mean(x ** 2))) if x.size else None

        sh_v, hi_v = rms(dL[sh]), rms(dL[hi])
        bands = [v for v in (sh_v, hi_v) if v is not None]
        return {
            "light": rms(dL),
            "sat": rms(dC),
            "warm": rms(db),                       # blue(−) .. yellow(+): the warm / cool axis
            "skin": rms(np.stack([dL[skin], da[skin], db[skin]], -1).reshape(-1))
                    if int(skin.sum()) >= 8 else None,
            "tone": float(np.mean(bands)) if bands else None,
            "shadow": sh_v,
            "highlight": hi_v,
            "overall": self.lab_residual(params, tgt),
        }


def confidence(res, floor=10.0):
    """a fitted recipe's Lab residual -> (0..1 confidence, a word for it)"""
    c = max(0.0, min(1.0, 1.0 - float(res) / float(floor)))
    return c, ("高" if c >= 0.75 else "中" if c >= 0.45 else "低")


def _skin_mask(lab):
    """the warm mid-tone a/b window skin falls in — a crude locus, but enough to isolate a face-ish
    region of a 16x16 signature"""
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    return (L > 35.0) & (L < 85.0) & (a > 6.0) & (a < 30.0) & (b > 4.0) & (b < 35.0)
