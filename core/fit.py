"""Constrained search: fit RL recipe parameters to a target Lab appearance.

The search space is the one the 77 calibration frames actually cover (interpolation, not
extrapolation), and it hill-climbs from many random seeds exactly like the original fit4.py.
"""
import numpy as np

from . import ranges as R
from .model import fvec, SIG

# choices per field index (see ranges.FIELDS); the effect slot is off unless allow_effects
STYLES = [1, 2, 3, 4, 5, 7, 8, 9]        # skip mono/sepia/sunset/night/autumn (colour looks only)
ADJ = list(range(-3, 4))
WBS = [0, 1, 14]
KELVIN = [0] + list(range(2500, 7600, 100))
EFFECTS = [0, 4, 5]                       # only the effects that occur in the samples
EVS = list(range(-2, 4))
DRO = list(range(0, 7))


def _choices(allow_effects):
    return [
        STYLES, ADJ, ADJ, ADJ, WBS, KELVIN, ADJ, ADJ,
        EFFECTS if allow_effects else [0], EVS, DRO,
    ]


def fit(model, target_lab, allow_effects=False, seeds=60, rng_seed=11):
    """return (params, residual_lab). target_lab is (SIG,SIG,3) real Lab units."""
    ft = (np.asarray(target_lab, float) / 50.0).reshape(-1)
    W = model.W
    choices = _choices(allow_effects)

    def loss(v):
        f = np.concatenate([fvec(v), [1.0]])
        return float(np.mean((f @ W - ft) ** 2))

    rng = np.random.default_rng(rng_seed)
    best = None
    for _ in range(seeds):
        v = [int(rng.choice(choices[0])), 0, 0, 0, 1, 0, 0, 0,
             int(rng.choice(choices[8])), 0, 6, 0]
        cur = loss(v)
        moved = True
        while moved:
            moved = False
            for i, ch in enumerate(choices):
                base_i = v[i]
                for c in ch:
                    if c == base_i:
                        continue
                    v[i] = c
                    l = loss(v)
                    if l < cur - 1e-12:
                        cur, base_i, moved = l, c, True
                v[i] = base_i
        if best is None or cur < best[0]:
            best = (cur, list(v))

    params = best[1]
    residual = float(np.sqrt(best[0]) * 50)
    return params, residual


def params_to_recipe(params, name="", group=R.CUSTOM):
    """a Recipe from the 12 fitted fields"""
    from .recipe import Recipe
    return Recipe(group=group, name=name, **{k: int(x) for k, x in zip(R.FIELDS, params)})
