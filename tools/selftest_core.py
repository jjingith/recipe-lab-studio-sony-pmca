"""Round-trip self-test for the core recipe/cube layer.

Checks:
  1. every builtin recipe passes the strict range validation,
  2. write_v1 -> read_v1 reproduces the recipe (all 12 fields),
  3. the writer's padding / comment columns match the Java line() helper,
  4. a synthetic .cube parses and applies as expected,
  5. a card push backs a same-name file up, replaces it and reads it back,
  6. a before/after pair is inferred as a delta over the reference frame,
  7. the model's own prediction scores ~0 on every named term,
  8. the library's tags / favourites / search / history / duplicates behave.
Run:  python tools\\selftest_core.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core import ranges as R
from core import recipe as RC
from core import cube as CU

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILTINS = os.path.join(ROOT, "data", "builtins.json")


def test_builtins():
    data = json.load(open(BUILTINS, encoding="utf-8"))
    bad = 0
    for d in data["recipes"]:
        r = RC.Recipe.from_dict({k: d[k] for k in
                                 ("group", "name", "style", "sat", "con", "sharp",
                                  "wb_mode", "kelvin", "ab", "gm", "pe", "ev", "dro", "sub")})
        p = RC.problem(r)
        if p:
            bad += 1
            print("  FAIL range:", r.name, "->", p)
    print("builtins: %d recipes, %d invalid" % (len(data["recipes"]), bad))
    return bad == 0


def test_roundtrip():
    data = json.load(open(BUILTINS, encoding="utf-8"))
    bad = 0
    for d in data["recipes"]:
        r = RC.Recipe.from_dict({k: d[k] for k in
                                 ("group", "name", "style", "sat", "con", "sharp",
                                  "wb_mode", "kelvin", "ab", "gm", "pe", "ev", "dro", "sub")})
        # builtin names may exceed NAME_MAX / use '/', which no custom file can carry;
        # the custom format is exercised with a sanitized but still valid name
        r.name = ("C" + r.name.replace("/", "-"))[:24]
        text = RC.write_v1(r)
        back, err = RC.read_v1(text, RC.file_name(r.name, []))
        if err is not None:
            bad += 1
            print("  FAIL read:", r.name, "->", err)
            continue
        if back.values() != r.values() or back.name != r.name:
            bad += 1
            print("  FAIL mismatch:", r.name, r.values(), "!=", back.values())
    print("round-trip: %d recipes, %d mismatched" % (len(data["recipes"]), bad))
    return bad == 0


def test_columns():
    """every comment-carrying line must have its ' # ' at or after column 28 (0-based 28)"""
    r = RC.Recipe(name="Kodak 2383 print", group=R.CUSTOM, style=7, sat=0, con=0, sharp=1,
                   wb_mode=R.WB_AUTO, kelvin=0, ab=0, gm=-1, pe=0, ev=3, dro=6)
    text = RC.write_v1(r)
    ok = True
    for line in text.splitlines():
        if " # " in line and not line.startswith("#"):
            col = line.index(" # ")
            if col < 28:
                ok = False
                print("  FAIL column %d: %r" % (col, line))
    print("comment columns: %s" % ("ok" if ok else "too early"))
    return ok


def test_cube():
    n = 4
    grid = np.linspace(0, 1, n)
    Rg, Gg, Bg = np.meshgrid(grid, grid, grid, indexing="ij")
    data = np.stack([Rg, 1.0 - Gg, Bg], -1)               # a simple invert-green LUT
    lines = ["TITLE \"test\"", "LUT_3D_SIZE %d" % n]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                lines.append("%.6f %.6f %.6f" % (data[i, j, k, 0], data[i, j, k, 1], data[i, j, k, 2]))
    tmp = os.path.join(ROOT, "build", "test_cube.cube")
    open(tmp, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    c, err = CU.load_safe(tmp)
    if err:
        print("  FAIL cube load:", err)
        return False
    probe = np.array([[[0.2, 0.4, 0.6], [1.0, 1.0, 1.0], [0.0, 0.0, 0.0]]], float)
    out = c.apply(probe)
    expect = np.stack([probe[..., 0], 1.0 - probe[..., 1], probe[..., 2]], -1)
    err_max = float(np.abs(out - expect).max())
    ok = err_max < 1e-6 and np.isclose(c.data[2, 1, 3, 1], 1.0 - grid[1])
    print("cube apply max error: %.2e -> %s" % (err_max, "ok" if ok else "FAIL"))
    os.remove(tmp)
    return ok


def test_card_safety():
    """a push backs a same-name card file up, replaces it, and reads it back; the plan reports the
    conflict before anything is written, an identical push is skipped, and a backup rolls back"""
    import shutil
    import tempfile
    from core import card as CD

    root = tempfile.mkdtemp(prefix="rlcard_")
    try:
        os.makedirs(os.path.join(root, "DCIM"))
        d = os.path.join(root, R.DIR)
        os.makedirs(d)
        card = CD.Card(root)
        old = RC.Recipe(name="Test Look", group=R.CUSTOM, style=2, sat=1, con=0, sharp=0,
                        wb_mode=R.WB_AUTO, ev=0, dro=R.DRO_AUTO)
        RC.save_dir(d, old)
        new = RC.Recipe(name="Test Look", group=R.CUSTOM, style=2, sat=3, con=-1, sharp=1,
                        wb_mode=R.WB_AUTO, ev=2, dro=R.DRO_AUTO)
        rows = card.plan([(new, "TESTLOOK.YML")])
        if rows[0]["status"] != "overwrite":
            print("  FAIL card plan status:", rows[0]["status"])
            return False
        written, errors = card.push_all(rows)
        if errors or len(written) != 1:
            print("  FAIL card push:", errors)
            return False
        res = written[0]
        if not res.verified or not res.backup or not os.path.exists(res.backup):
            print("  FAIL card verify/backup:", res)
            return False
        back, err = RC.read_v1(open(os.path.join(d, res.file), encoding="utf-8").read(), res.file)
        was, werr = RC.read_v1(open(res.backup, encoding="utf-8").read(), os.path.basename(res.backup))
        if err or werr or back.values() != new.values() or was.values() != old.values():
            print("  FAIL card read-back:", err, werr)
            return False
        rows2 = card.plan([(new, "TESTLOOK.YML")])
        w2, e2 = card.push_all(rows2)
        if rows2[0]["status"] != "same" or w2 or e2:
            print("  FAIL card same-skip:", rows2[0]["status"], w2, e2)
            return False
        if not card.writable()[0]:
            print("  FAIL card writable probe")
            return False
        card.restore_backup(res.file)
        back2, _ = RC.read_v1(open(os.path.join(d, res.file), encoding="utf-8").read(), res.file)
        if back2.values() != old.values():
            print("  FAIL card restore values:", back2.values())
            return False
        print("card: plan + backup + read-back verify + same-skip + restore, ok")
        return True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pair():
    """a before/after pair becomes a delta carried onto the reference frame's own appearance"""
    from core import style as ST

    rng = np.random.default_rng(3)
    before = rng.random((32, 32, 3))
    after = np.clip(before * 0.9 + 0.05, 0, 1)
    lab, look, thumb = ST.target_from_pair(before, after)
    base = ST.base_signature()
    ok = (lab.shape == base.shape and look.shape == base.shape
          and thumb.shape == (128, 128, 3) and np.allclose(lab - base, look, atol=1e-9))
    print("pair target: %s (look mean %.3f, thumb %s)"
          % ("ok" if ok else "FAIL", float(look.mean()), thumb.shape))
    return ok


def test_breakdown():
    """the model's own prediction has zero residual, so every named term is ~0 and confidence is 1"""
    from core.model import Model, confidence
    from core import style as ST

    m = Model.load()
    p = m.params[0]
    tgt = m.signature(p)
    sc = m.breakdown(p, tgt, ST.base_signature())
    worst = max(v for v in sc.values() if v is not None)
    c, word = confidence(0.0)
    ok = worst < 1e-6 and c == 1.0 and word == "高"
    print("breakdown: worst term %.2e, keys=%s, confidence=%s(%.0f%%)"
          % (worst, ",".join(sorted(k for k in sc)), word, c * 100))
    return ok


def test_library():
    """tags / favourites / search / history / duplicates, on a throwaway library"""
    import shutil
    import tempfile
    from core import library as LB

    d = tempfile.mkdtemp(prefix="rllib_")
    try:
        lib = LB.Library(d).load()
        r1 = RC.Recipe(name="Look One", group=R.CUSTOM, style=1, sat=2, dro=R.DRO_AUTO)
        f1 = lib.add(r1, {"source": "test"})
        lib.set_tags(f1, ["film", "warm", "film"])
        checks = [("tags dedup", lib.tags_of(f1) == ["film", "warm"]),
                  ("favourite", lib.toggle_fav(f1) and lib.is_fav(f1)),
                  ("search by tag", [f for _, f in lib.search("warm")] == [f1]),
                  ("search favourites", [f for _, f in lib.search("", fav_only=True)] == [f1])]
        r1b = RC.Recipe(name="Look One", group=R.CUSTOM, style=1, sat=-3, dro=R.DRO_AUTO)
        lib.update(r1b, f1)
        checks.append(("history kept", len(lib.history(f1)) == 1))
        checks.append(("fav survives edit", lib.meta_for(f1).get("fav") is True))
        r2 = RC.Recipe(name="Look Two", group=R.CUSTOM, style=1, sat=-3, dro=R.DRO_AUTO)
        lib.add(r2)
        dups = lib.duplicates()
        checks.append(("duplicate found", len(dups) == 1 and len(dups[0]) == 2))
        lib.restore(f1, lib.history(f1)[0][1])
        checks.append(("restore v1", lib.find(f1).values() == r1.values()))
        bad = [n for n, ok in checks if not ok]
        print("library: %d/%d ok%s" % (len(checks) - len(bad), len(checks),
                                       ("  FAIL: " + ", ".join(bad)) if bad else ""))
        return not bad
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    results = [test_builtins(), test_roundtrip(), test_columns(), test_cube(),
               test_card_safety(), test_pair(), test_breakdown(), test_library()]
    print("\nALL %s" % ("PASS" if all(results) else "FAIL"))
    sys.exit(0 if all(results) else 1)
