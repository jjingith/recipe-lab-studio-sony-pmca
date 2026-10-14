"""Minimal .cube reader + applier for 3D (and 1D) LUTs.

A .cube file is the interchange format most grading tools speak. Here it is used two ways:
  - as an exact target look to preview (apply the LUT to a photo),
  - as the signature a fitted RL recipe should approximate.
"""
import re

import numpy as np


class Cube:
    """a 3D LUT: data[c, i, j, k] = output channel c for input (r_i, g_j, b_k)"""

    def __init__(self, size, data, title=None, domain_min=None, domain_max=None):
        self.size = int(size)
        self.data = np.asarray(data, dtype=np.float64)          # (N, N, N, 3) in input order (r,g,b)
        self.title = title
        self.domain_min = np.asarray(domain_min if domain_min is not None else [0, 0, 0], float)
        self.domain_max = np.asarray(domain_max if domain_max is not None else [1, 1, 1], float)

    # ------------------------------------------------------------ parse
    @classmethod
    def load(cls, path):
        title = None
        size = None
        dmin, dmax = [0.0, 0.0, 0.0], [1.0, 1.0, 1.0]
        triplets = []
        size_1d = None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                up = line.upper()
                if up.startswith("TITLE"):
                    title = line.split(None, 1)[1].strip().strip('"') if len(line.split(None, 1)) > 1 else ""
                    continue
                if up.startswith("LUT_3D_SIZE"):
                    size = int(line.split()[1])
                    continue
                if up.startswith("LUT_1D_SIZE"):
                    size_1d = int(line.split()[1])
                    continue
                if up.startswith("DOMAIN_MIN"):
                    dmin = [float(x) for x in line.split()[1:4]]
                    continue
                if up.startswith("DOMAIN_MAX"):
                    dmax = [float(x) for x in line.split()[1:4]]
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        triplets.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    except ValueError:
                        pass
        if size is None and size_1d is None:
            raise ValueError("no LUT_3D_SIZE / LUT_1D_SIZE in %s" % path)
        data = np.array(triplets, dtype=np.float64)
        if size is not None:
            if data.shape[0] != size ** 3:
                raise ValueError("expected %d entries, found %d" % (size ** 3, data.shape[0]))
            # .cube lists R fastest, then G, then B
            data = data.reshape(size, size, size, 3)
        else:
            if data.shape[0] != size_1d:
                raise ValueError("expected %d entries, found %d" % (size_1d, data.shape[0]))
            # promote a 1D LUT to a 3D grid so the applier is uniform
            axis = [data[:, c] for c in range(3)]
            grid = np.stack(np.meshgrid(axis[0], axis[1], axis[2], indexing="ij"), -1)
            size = size_1d
            data = grid
        return cls(size, data, title, dmin, dmax)

    # ------------------------------------------------------------ apply
    def apply(self, rgb):
        """rgb float array (...,3) in [0,1] -> graded float array, trilinear within the cube's domain"""
        shape = rgb.shape
        x = np.clip(rgb, 0.0, 1.0).reshape(-1, 3)
        norm = (x - self.domain_min) / np.maximum(self.domain_max - self.domain_min, 1e-9)
        idx = np.clip(norm * (self.size - 1), 0, self.size - 1)
        out = _trilinear(self.data, idx)
        return np.clip(out, 0.0, 1.0).reshape(shape)

    def signature(self, size=16):
        """a compact Lab-shaped summary: apply to an identity grid and average — used for style targets"""
        grid = np.linspace(0.0, 1.0, size)
        Rg, Gg, Bg = np.meshgrid(grid, grid, grid, indexing="ij")
        out = self.apply(np.stack([Rg, Gg, Bg], -1))
        return out


_EXT = re.compile(r"\.cube$", re.I)


def _trilinear(data, idx, chunk=1 << 20):
    """sample a 3D LUT grid data[N,N,N,3] at float indices idx[M,3] (each in [0,N-1]); chunked so
    a full-resolution image does not blow up memory"""
    N = data.shape[0]
    m = idx.shape[0]
    out = np.empty((m, 3), float)
    for s in range(0, m, chunk):
        e = min(m, s + chunk)
        i = idx[s:e]
        i0 = np.floor(i).astype(np.intp)
        i1 = np.minimum(i0 + 1, N - 1)
        f = i - i0
        wx, wy, wz = f[:, 0:1], f[:, 1:2], f[:, 2:3]
        acc = np.zeros((e - s, 3), float)
        for dx in (0, 1):
            ax = i1[:, 0] if dx else i0[:, 0]
            wxx = wx if dx else (1 - wx)
            for dy in (0, 1):
                ay = i1[:, 1] if dy else i0[:, 1]
                wyy = wy if dy else (1 - wy)
                for dz in (0, 1):
                    az = i1[:, 2] if dz else i0[:, 2]
                    wzz = wz if dz else (1 - wz)
                    acc += (wxx * wyy * wzz) * data[ax, ay, az]
        out[s:e] = acc
    return out


def load_safe(path):
    try:
        return Cube.load(path), None
    except Exception as e:      # noqa: BLE001 - report any parse failure to the UI
        return None, str(e)
