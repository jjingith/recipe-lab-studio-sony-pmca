"""Self-contained sRGB <-> CIELAB (D65) conversion.

Replaces skimage.color, which pulls in a very large dependency for just two functions. The
constants and formulae are the standard ones skimage uses, so results match to floating error.
"""
import numpy as np

_M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]], float)
_M_XYZ2RGB = np.linalg.inv(_M_RGB2XYZ)
_WHITE = np.array([0.95047, 1.0, 1.08883], float)
_DELTA = 6.0 / 29.0


def _srgb_to_linear(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)


def _f(t):
    return np.where(t > _DELTA ** 3, np.cbrt(t), t / (3 * _DELTA ** 2) + 4.0 / 29.0)


def _f_inv(t):
    return np.where(t > _DELTA, t ** 3, 3 * _DELTA ** 2 * (t - 4.0 / 29.0))


def rgb2lab(rgb):
    """(...,3) sRGB in [0,1] -> (...,3) Lab (L 0..100, a/b ~ -128..127)"""
    a = np.asarray(rgb, float)
    lin = _srgb_to_linear(a)
    xyz = lin @ _M_RGB2XYZ.T
    xyz = xyz / _WHITE
    fx, fy, fz = _f(xyz[..., 0]), _f(xyz[..., 1]), _f(xyz[..., 2])
    lab = np.empty(a.shape[:-1] + (3,), float)
    lab[..., 0] = 116 * fy - 16
    lab[..., 1] = 500 * (fx - fy)
    lab[..., 2] = 200 * (fy - fz)
    return lab


def lab2rgb(lab):
    """(...,3) Lab -> (...,3) sRGB in [0,1]"""
    a = np.asarray(lab, float)
    fy = (a[..., 0] + 16) / 116.0
    fx = fy + a[..., 1] / 500.0
    fz = fy - a[..., 2] / 200.0
    xyz = np.stack([_f_inv(fx), _f_inv(fy), _f_inv(fz)], -1) * _WHITE
    lin = xyz @ _M_XYZ2RGB.T
    return np.clip(_linear_to_srgb(lin), 0.0, 1.0)
