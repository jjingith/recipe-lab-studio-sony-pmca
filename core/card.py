"""The camera's memory card, seen as a mounted mass-storage volume.

When the camera is set to Mass Storage the card mounts as a drive whose root holds DCIM/ and, for
RL custom recipes, RECIPES/. We detect such volumes, read and write RECIPES/*.YML, and diff them
against the PC library. (pmca-console remains the fallback when the card does not mount.)

Writing to a card is not like writing to a disk. A short or torn write is not reported by the write
call — the FUSE layer accepts it and the loss only turns up when the file is read again — and the
camera app silently skips any .YML it cannot parse. So every write here is: back the same-name file
up, write, then read the file back and parse it again. A push that cannot be verified raises.
"""
import ctypes
import os
import shutil
import string
from dataclasses import dataclass

from . import ranges as R
from . import recipe as RC

BACKUP_DIR = "_backup"      # inside RECIPES/ so it travels with the recipes; a folder, so load_dir skips it
PROBE = "WRITETST.TMP"      # an 8.3-compatible write probe


def recipes_dir(root):
    return os.path.join(root, R.DIR)


DRIVE_REMOTE = 4            # a mapped network share is never the camera's card


def _drive_type(root):
    """Windows' GetDriveType for a volume root, or 0 when it cannot be asked"""
    try:
        return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
    except Exception:
        return 0


def detect():
    """every mounted volume that looks like a camera card: [(drive, recipes_dir)]"""
    found = []
    for letter in string.ascii_uppercase:
        root = "%s:\\" % letter
        if _drive_type(root) == DRIVE_REMOTE:
            continue                       # the card is a local volume; a NAS mapping also holds a DCIM/ mirror
        try:
            if os.path.isdir(os.path.join(root, "DCIM")):
                found.append((root, recipes_dir(root)))
        except OSError:
            continue
    return found


def _recover(backup):
    """the sentence that tells the user how to undo a failed write"""
    if backup:
        return "\n\n原文件已备份到 %s，可复制回 RECIPES/ 恢复。" % backup
    return ""


@dataclass
class PushResult:
    """what one push did: where it landed, what it displaced, and whether it was read back OK"""
    file: str
    name: str
    backup: str = None
    verified: bool = False


class Card:
    def __init__(self, root):
        self.root = root.rstrip("\\/") + os.sep if root.endswith(("\\", "/")) else root
        # normalise "Y:\\" style roots
        if os.path.isdir(root):
            self.root = os.path.abspath(root)
        self.dir = recipes_dir(self.root)

    # ------------------------------------------------------------ read
    @property
    def present(self):
        return os.path.isdir(self.root)

    @property
    def backup_dir(self):
        return os.path.join(self.dir, BACKUP_DIR)

    def load(self):
        """(entries[(recipe,file)], skipped[strings])"""
        return RC.load_dir(self.dir)

    def _file_for_name(self, name):
        """the card file already holding a recipe of this name, or None"""
        low = (name or "").lower()
        for r, f in self.load()[0]:
            if r.name.lower() == low:
                return f
        return None

    def backups(self):
        """[(file, path)] — the copies taken before a push replaced a recipe"""
        out = []
        if not os.path.isdir(self.backup_dir):
            return out
        for fn in sorted(os.listdir(self.backup_dir), key=lambda s: s.lower()):
            p = os.path.join(self.backup_dir, fn)
            if os.path.isfile(p) and fn.lower().endswith(R.EXT.lower()):
                out.append((fn, p))
        return out

    # ------------------------------------------------------------ health
    def writable(self):
        """(ok, reason) — probe with a real write, because a write-protected card reports no error
        until the moment of writing"""
        try:
            os.makedirs(self.dir, exist_ok=True)
        except OSError as e:
            return False, "无法创建 RECIPES 文件夹：%s" % e
        probe = os.path.join(self.dir, PROBE)
        try:
            with open(probe, "w", encoding="utf-8") as f:
                f.write("probe")
            os.remove(probe)
            return True, None
        except OSError as e:
            return False, str(e)

    def free_bytes(self):
        try:
            where = self.dir if os.path.isdir(self.dir) else self.root
            return shutil.disk_usage(where).free
        except OSError:
            return None

    # ------------------------------------------------------------ write
    def plan(self, entries):
        """what pushing `entries` [(recipe, src)] would do, without doing any of it.

        Each row: recipe, src, status ('new' | 'same' | 'overwrite'), card_file, card_recipe, bytes.
        'overwrite' means a same-name recipe with a different look is already on the card — the one
        the user has to agree to before it is replaced, whose copy goes to RECIPES/_backup.
        """
        card = {}
        for r, f in self.load()[0]:
            card[r.name.lower()] = (r, f)
        rows = []
        for r, src in entries:
            cur = card.get(r.name.lower())
            if cur is None:
                status, card_recipe, card_file = "new", None, None
            elif cur[0].values() == r.values():
                status, card_recipe, card_file = "same", cur[0], cur[1]
            else:
                status, card_recipe, card_file = "overwrite", cur[0], cur[1]
            rows.append({"recipe": r, "src": src, "status": status,
                         "card_file": card_file, "card_recipe": card_recipe,
                         "bytes": len(RC.write_v1(r).encode("utf-8"))})
        return rows

    def _backup(self, file):
        """copy the card's current file aside before it is replaced; returns the copy path or None"""
        if not file:
            return None
        src = os.path.join(self.dir, file)
        if not os.path.exists(src):
            return None
        os.makedirs(self.backup_dir, exist_ok=True)
        dst = os.path.join(self.backup_dir, file)
        shutil.copy2(src, dst)
        return dst

    def restore_backup(self, file):
        """put a backed-up file back into RECIPES/; returns the restored path or None"""
        src = os.path.join(self.backup_dir, file)
        if not os.path.exists(src):
            return None
        dst = os.path.join(self.dir, file)
        shutil.copy2(src, dst)
        return dst

    def push(self, r, old_file=None, backup=True):
        """write one recipe onto the card and read it back to prove it landed.

        Raises ValueError when the recipe is out of range, OSError when the card refuses the write,
        and OSError also when the file does not read back as the recipe that was just written (a
        short write is invisible until the file is read again).
        """
        p = RC.problem(r)
        if p:
            raise ValueError("配方越界: %s" % p)
        if old_file is None:
            old_file = self._file_for_name(r.name)
        bak = self._backup(old_file) if (backup and old_file) else None
        fname = RC.save_dir(self.dir, r, old_file=old_file)
        path = os.path.join(self.dir, fname)
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            raise OSError("写入后回读失败（%s）：%s%s" % (fname, e, _recover(bak)))
        back, err = RC.read_v1(text, fname)
        if err is not None:
            raise OSError("写入校验失败：回读的 %s 无法解析（%s）%s" % (fname, err, _recover(bak)))
        if back.name != r.name or back.values() != r.values():
            raise OSError("写入校验失败：%s 的回读值与写入值不一致%s" % (fname, _recover(bak)))
        return PushResult(file=fname, name=back.name, backup=bak, verified=True)

    def push_all(self, rows, backup=True):
        """push the rows plan() produced; the already-identical ones are skipped.

        Returns (written[PushResult], errors[strings]). One row failing does not stop the rest —
        the errors carry the recovery hint, so the caller can show them together."""
        written, errors = [], []
        for row in rows:
            if row["status"] == "same":
                continue
            try:
                written.append(self.push(row["recipe"], old_file=row["card_file"], backup=backup))
            except (OSError, ValueError) as e:
                errors.append("%s: %s" % (row["recipe"].name, e))
        return written, errors

    def pull_all(self, library):
        """bring every card recipe into the library; returns (added, errors)"""
        entries, skipped = self.load()
        added, errors = [], list(skipped)
        for r, _ in entries:
            try:
                added.append(library.add(r, {"source": "card"}))
            except (OSError, ValueError) as e:
                errors.append("%s: %s" % (r.name, e))
        return added, errors

    def delete(self, file, backup=True):
        """remove one recipe from the card; the copy is kept in RECIPES/_backup first"""
        if backup:
            self._backup(file)
        path = os.path.join(self.dir, file)
        if os.path.exists(path):
            os.remove(path)


# ------------------------------------------------------------ diff
def diff(library_entries, card_entries):
    """compare the two by recipe name; returns dict with only-here / only-card / differing / same.

    A recipe present on both sides but with a different look is 'differing' — the library copy wins
    on push, the card copy wins on pull, and the user chooses in the UI."""
    lib = {r.name.lower(): (r, f) for r, f in library_entries}
    crd = {r.name.lower(): (r, f) for r, f in card_entries}
    out = {"only_library": [], "only_card": [], "differing": [], "same": []}
    for k, (r, f) in lib.items():
        if k not in crd:
            out["only_library"].append((r, f))
        elif r.values() == crd[k][0].values():
            out["same"].append((r, f))
        else:
            out["differing"].append((r, f, crd[k][0], crd[k][1]))
    for k, (r, f) in crd.items():
        if k not in lib:
            out["only_card"].append((r, f))
    return out
