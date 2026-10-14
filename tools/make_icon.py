r"""Build data/icon.ico from the recipe-lab launcher artwork.

The picture is the fork's cassette-futurism launcher (res/drawable-xxhdpi/ic_launcher.png, redrawn
in commit 2ee9d3f), kept beside the source as data/icon.png at its native 144px. Windows wants one
.ico holding several sizes - Explorer's 16px list view and a 256px preview are the same file - so
the master is first lifted to 256px and the .ico writer then derives every size in SIZES from it
with Lanczos, which is the only resampling Pillow's ICO plugin offers.

Run from the project root:  python tools\make_icon.py
"""
import os
import struct
import sys

# what the shell asks a .ico for: list view, small/large tiles, task bar, Explorer, jumbo preview
SIZES = [16, 24, 32, 48, 64, 96, 128, 144, 256]
MASTER_PX = 256                 # the frame every other size is resampled down from

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "data", "icon.png")
OUT = os.path.join(ROOT, "data", "icon.ico")


def _frames_in(path):
    """the sizes actually stored, read straight from the ICONDIR table (Pillow's own info['sizes']
    only reports the frames it happens to expose, so it is not a trustworthy check)"""
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack_from("<H", data, 4)[0]
    out = []
    for i in range(n):
        w, h = data[6 + i * 16], data[7 + i * 16]
        out.append(256 if w == 0 else w)
    return out


def main():
    from PIL import Image
    if not os.path.exists(MASTER):
        print("missing master: %s" % MASTER)
        return 1
    src = Image.open(MASTER).convert("RGBA")
    if src.width != src.height:
        print("master is not square: %dx%d" % (src.width, src.height))
        return 1
    base = src if src.width == MASTER_PX else src.resize((MASTER_PX, MASTER_PX), Image.LANCZOS)
    base.save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print("wrote %s (from %dx%d master)" % (OUT, src.width, src.height))
    print("frames:", _frames_in(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
