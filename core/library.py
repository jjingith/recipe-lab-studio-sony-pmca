"""The PC master library: the source of truth for the user's own recipes.

RL keeps custom recipes only on the memory card (RECIPES/*.YML), so swapping cards loses them.
Here they live on disk as the same .YML files, plus an index.json holding the extra metadata the
file format has no room for (source cube/portfolio, fit residual, tags, group override).
"""
import json
import os
import shutil
import sys

from . import ranges as R
from . import recipe as RC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _home():
    """where the user's recipes live: next to the exe when frozen — a onefile build unpacks to a
    throwaway temp folder, so ROOT would take the library with it on every launch — and the project
    root when running from source"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return ROOT


DEFAULT_DIR = os.path.join(_home(), "library")
INDEX = "index.json"
HISTORY_DIR = ".history"        # a dot-folder: load_dir skips it, so kept versions never enter the library
HISTORY_KEEP = 20               # how many versions of one file to keep before the oldest are dropped


class Library:
    def __init__(self, directory=DEFAULT_DIR):
        self.dir = directory
        self.meta = {}
        self.entries = []       # [(recipe, file)]

    # ------------------------------------------------------------ io
    def load(self):
        os.makedirs(self.dir, exist_ok=True)
        self.entries, self.skipped = RC.load_dir(self.dir)
        idx_path = os.path.join(self.dir, INDEX)
        self.meta = {}
        if os.path.exists(idx_path):
            try:
                self.meta = json.load(open(idx_path, encoding="utf-8"))
            except (OSError, ValueError):
                self.meta = {}
        # drop meta for files that are gone
        files = {f for _, f in self.entries}
        for k in list(self.meta):
            if k not in files:
                del self.meta[k]
        return self

    def _save_index(self):
        tmp = os.path.join(self.dir, INDEX + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, ensure_ascii=False)
        os.replace(tmp, os.path.join(self.dir, INDEX))

    def meta_for(self, file):
        return self.meta.get(file, {})

    def taken_names(self, self_name=None):
        return [r.name for r, _ in self.entries if self_name is None or r.name.lower() != self_name.lower()]

    # ------------------------------------------------------------ crud
    def add(self, r, meta=None):
        """validate, name-check, write the .YML and record metadata; returns the file name"""
        p = RC.problem(r)
        if p:
            raise ValueError("recipe out of range: %s" % p)
        np_ = RC.name_problem(r.name, self.taken_names())
        if np_:
            raise ValueError("bad name: %s" % np_)
        file = RC.save_dir(self.dir, r)
        if meta:
            self.meta[file] = meta
            self._save_index()
        self.entries, _ = RC.load_dir(self.dir)
        return file

    def update(self, r, old_file, meta=None):
        np_ = RC.name_problem(r.name, self.taken_names(self_name=self._name_of(old_file)))
        if np_:
            raise ValueError("bad name: %s" % np_)
        p = RC.problem(r)
        if p:
            raise ValueError("recipe out of range: %s" % p)
        self._snapshot(old_file)                 # keep what the file held before this edit
        new_file = RC.save_dir(self.dir, r, old_file=old_file)
        if old_file in self.meta and new_file != old_file:
            self.meta[new_file] = self.meta.pop(old_file)
        if meta is not None:
            self.meta[new_file] = meta
        self._save_index()
        self.entries, _ = RC.load_dir(self.dir)
        return new_file

    def remove(self, file):
        self._snapshot(file)                     # a delete stays undoable through the history
        path = os.path.join(self.dir, file)
        if os.path.exists(path):
            os.remove(path)
        self.meta.pop(file, None)
        self._save_index()
        self.entries, _ = RC.load_dir(self.dir)

    def set_meta(self, file, meta):
        self.meta[file] = meta
        self._save_index()

    # ------------------------------------------------------------ tags & favourites
    def tags_of(self, file):
        return list(self.meta.get(file, {}).get("tags", []))

    def set_tags(self, file, tags):
        """replace a recipe's tags, stripped and de-duplicated, keeping first-seen order"""
        clean, seen = [], set()
        for t in tags:
            t = (t or "").strip()
            key = t.lower()
            if t and key not in seen:
                seen.add(key)
                clean.append(t)
        m = dict(self.meta.get(file, {}))
        if clean:
            m["tags"] = clean
        else:
            m.pop("tags", None)
        self.meta[file] = m
        self._save_index()

    def is_fav(self, file):
        return bool(self.meta.get(file, {}).get("fav"))

    def toggle_fav(self, file):
        m = dict(self.meta.get(file, {}))
        m["fav"] = not m.get("fav")
        self.meta[file] = m
        self._save_index()
        return bool(m["fav"])

    def all_tags(self):
        out = set()
        for m in self.meta.values():
            out.update(m.get("tags", []))
        return sorted(out, key=str.lower)

    def search(self, query="", fav_only=False):
        """the entries matching a query over name and tags, optionally only favourites"""
        q = (query or "").strip().lower()
        out = []
        for r, f in self.entries:
            m = self.meta.get(f, {})
            if fav_only and not m.get("fav"):
                continue
            if q and q not in r.name.lower() and not any(q in t.lower() for t in m.get("tags", [])):
                continue
            out.append((r, f))
        return out

    def duplicates(self):
        """groups of recipes that differ only in name — the same twelve values stored twice.

        add()/update() already forbid a repeated *name*, so these are distinct names with an
        identical look: the redundancy this reports."""
        groups = {}
        for r, f in self.entries:
            groups.setdefault(tuple(r.values()), []).append((r, f))
        return [g for g in groups.values() if len(g) > 1]

    # ------------------------------------------------------------ version history
    @property
    def history_dir(self):
        return os.path.join(self.dir, HISTORY_DIR)

    def _snapshot(self, file):
        """keep a copy of the file as it stands, before it changes; returns the copy path or None"""
        src = os.path.join(self.dir, file)
        if not file or not os.path.exists(src):
            return None
        os.makedirs(self.history_dir, exist_ok=True)
        stem = RC.stem(file)
        n = 1
        while os.path.exists(os.path.join(self.history_dir, "%s_v%d%s" % (stem, n, R.EXT))):
            n += 1
        dst = os.path.join(self.history_dir, "%s_v%d%s" % (stem, n, R.EXT))
        shutil.copy2(src, dst)
        self._prune_history(stem)
        return dst

    def _prune_history(self, stem, keep=HISTORY_KEEP):
        olds = []
        for fn in os.listdir(self.history_dir):
            if not fn.lower().startswith((stem.lower() + "_v")):
                continue
            try:
                olds.append((int(RC.stem(fn).rsplit("_v", 1)[1]), fn))
            except (ValueError, IndexError):
                continue
        olds.sort()
        for _, fn in olds[:-keep]:               # keep the newest `keep` versions
            os.remove(os.path.join(self.history_dir, fn))

    def history(self, file):
        """[(index, path)] — the kept versions of a file, oldest first"""
        if not os.path.isdir(self.history_dir):
            return []
        stem = RC.stem(file)
        out = []
        for fn in sorted(os.listdir(self.history_dir)):
            if not fn.lower().startswith(stem.lower() + "_v") or not fn.lower().endswith(R.EXT.lower()):
                continue
            try:
                out.append((int(RC.stem(fn).rsplit("_v", 1)[1]), os.path.join(self.history_dir, fn)))
            except (ValueError, IndexError):
                continue
        out.sort()
        return out

    def restore(self, file, snap_path):
        """roll a file back to a kept version; the current one is kept as a new version first"""
        self._snapshot(file)
        shutil.copy2(snap_path, os.path.join(self.dir, file))
        self.load()
        return file

    def _name_of(self, file):
        for r, f in self.entries:
            if f == file:
                return r.name
        return None

    def find(self, file):
        for r, f in self.entries:
            if f == file:
                return r
        return None

    # ------------------------------------------------------------ import/export (files)
    def import_file(self, path, meta=None):
        """bring one .YML in from elsewhere (e.g. pulled off a card)"""
        text = open(path, encoding="utf-8", errors="replace").read()
        r, err = RC.read_v1(text, os.path.basename(path))
        if err:
            raise ValueError(err)
        return self.add(r, meta)

    def export_file(self, file, dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.dir, file), os.path.join(dest_dir, file))
        return os.path.join(dest_dir, file)
