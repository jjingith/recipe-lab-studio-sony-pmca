r"""Package Recipe Lab Studio into a standalone exe with PyInstaller.

Builds a single-file ``RecipeLabStudio.exe`` in the project root, so it can be run from E:\RecipeStudio
or dropped anywhere else. Its `library/` folder is created next to the exe, never inside it. The
data/ folder is bundled into the exe. Run from the project root:  python tools\build_exe.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    import PyInstaller.__main__ as pyi
    sep = ";" if os.name == "nt" else ":"
    args = [
        os.path.join(ROOT, "main.py"),
        "--name", "RecipeLabStudio",
        "--onefile",
        "--noconsole",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", os.path.join(ROOT, "data", "icon.ico"),   # the exe's own icon, as the shell shows it
        "--distpath", ROOT,
        "--workpath", os.path.join(ROOT, "build", "pyi"),
        "--specpath", os.path.join(ROOT, "build"),
        "--add-data", "%s%sdata" % (os.path.join(ROOT, "data"), sep),
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "skimage",
        "--exclude-module", "scipy",
        "--exclude-module", "rawpy",
        "--exclude-module", "exiv2",
    ]
    pyi.run(args)
    print("\nexe at:", os.path.join(ROOT, "RecipeLabStudio.exe"))


if __name__ == "__main__":
    sys.exit(main())
