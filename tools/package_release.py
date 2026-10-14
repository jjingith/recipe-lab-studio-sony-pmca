r"""Package the GitHub release artifacts for Recipe Lab Studio.

Both are built from the one exe that tools\build_exe.py produced, and land in release\:

  RecipeLabStudio-<ver>-portable.zip   the green build: unzip anywhere and run. library\ and
                                       settings.json are created beside the exe, so the folder is
                                       self-contained and survives being moved.
  RecipeLabStudio-<ver>-Setup.exe      the installer: a first page carrying the free-of-charge /
                                       not-for-sale notice behind a tick box, a choice of installing
                                       for all users or just this one, optional Start Menu and
                                       desktop shortcuts (both on by default), and an uninstaller.

The installer is compiled by Inno Setup's ISCC. That compiler is not vendored here; _iscc() looks
for it in the usual places and, when it is missing, the script still builds the portable zip and
says which path it wanted. The version / publisher / repo URL come out of ui\i18n.py, so filling
those in there is all it takes to re-cut a release.

Run from the project root:  python tools\package_release.py
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE = os.path.join(ROOT, "release")
I18N = os.path.join(ROOT, "ui", "i18n.py")
ISS = os.path.join(ROOT, "tools", "installer.iss")
ISL_SRC = os.path.join(ROOT, "tools", "isl")


def _constant(src, name):
    m = re.search(r'^%s\s*=\s*"([^"]*)"' % re.escape(name), src, re.M)
    return m.group(1) if m else ""


def _iscc():
    """the Inno Setup compiler, wherever this machine happens to keep it"""
    for p in (os.environ.get("ISCC"),
              os.path.join(ROOT, "build", "inno", "ISCC.exe"),
              r"E:\pmca-toolchain\innosetup6\ISCC.exe",
              os.path.join(os.environ.get("TEMP", ""), "InnoSetup6", "ISCC.exe"),
              shutil.which("ISCC")):
        if p and os.path.exists(p):
            return p
    return None


def _sync_isl(iscc):
    """put the Chinese message files where ISCC looks for them (its own Languages subfolder)"""
    dst = os.path.join(os.path.dirname(iscc), "Languages")
    if not os.path.isdir(dst):
        return []
    copied = []
    for fn in sorted(os.listdir(ISL_SRC)):
        if fn.lower().endswith(".isl"):
            shutil.copyfile(os.path.join(ISL_SRC, fn), os.path.join(dst, fn))
            copied.append(fn)
    return copied


def _portable(version):
    name = "RecipeLabStudio-%s-portable" % version
    out = os.path.join(RELEASE, name + ".zip")
    exe = os.path.join(ROOT, "RecipeLabStudio.exe")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, "%s/RecipeLabStudio.exe" % name)
        readme = os.path.join(ROOT, "README.md")
        if os.path.exists(readme):
            z.write(readme, "%s/README.md" % name)
    return out


def _iss_string(v):
    """an ISPP string literal: quotes are dropped to apostrophes and a backslash is escaped, since
    these values (an author name, a URL) are only ever meant to read as plain text"""
    v = (v or "").replace("\\", "\\\\").replace('"', "'")
    return '"%s"' % " ".join(v.split())


def _installer(iscc, url, publisher, version):
    """compile tools\\installer.iss, handing the version / publisher / URL over as a generated
    #include rather than as /D arguments: a publisher name holding a space would not survive the
    ISCC command line, where the value has to be one whitespace-free token."""
    defs = os.path.join(ROOT, "build", "release_defines.iss")
    os.makedirs(os.path.dirname(defs), exist_ok=True)
    with open(defs, "w", encoding="utf-8") as f:
        f.write("#define MyAppVersion %s\n" % _iss_string(version))
        f.write("#define MyAppPublisher %s\n" % _iss_string(publisher or "jiajun zhou"))
        f.write("#define MyAppURL %s\n" % _iss_string(url or "https://github.com/"))
    r = subprocess.run([iscc, "/DRELEASE_DEFINES=%s" % defs, ISS],
                       capture_output=True, text=True)
    return r


def main():
    src = open(I18N, encoding="utf-8").read()
    version = _constant(src, "APP_VERSION") or "0"
    author = _constant(src, "AUTHOR")
    url = _constant(src, "GITHUB_URL")
    print("ui/i18n.py: version=%s  author=%r  url=%r" % (version, author, url))
    for label, v in (("AUTHOR", author), ("GITHUB_URL", url)):
        if v.startswith("<"):
            print("  ! %s is still the placeholder %r — the About box and the installer will show it"
                  % (label, v))

    if not os.path.exists(os.path.join(ROOT, "RecipeLabStudio.exe")):
        print("missing RecipeLabStudio.exe — run  python tools\\build_exe.py  first")
        return 1

    os.makedirs(RELEASE, exist_ok=True)
    zip_path = _portable(version)
    print("\nportable: %s  (%.1f MB)" % (zip_path, os.path.getsize(zip_path) / 1e6))

    iscc = _iscc()
    if not iscc:
        print("\ninstaller: SKIPPED — ISCC.exe not found.")
        print("  install Inno Setup, or unzip it and put ISCC.exe in build\\inno\\, or set ISCC=<path>")
        return 0
    print("\ninstaller compiler: %s" % iscc)
    isl = _sync_isl(iscc)
    if isl:
        print("  synced message files: %s" % ", ".join(isl))
    r = _installer(iscc, url, author, version)
    tail = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    for ln in tail[-8:]:
        print("  %s" % ln)
    if r.returncode != 0:
        print("  ISCC FAILED (%d):" % r.returncode)
        for ln in (r.stderr or "").splitlines():
            print("    %s" % ln)
        return 1
    out = os.path.join(RELEASE, "RecipeLabStudio-%s-Setup.exe" % version)
    if os.path.exists(out):
        print("\ninstaller: %s  (%.1f MB)" % (out, os.path.getsize(out) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
