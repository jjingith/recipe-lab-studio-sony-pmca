"""Adobe-style flat widgets: the shared zoom/pan state, the preview plate, the bar readout, the
panel module, and the recipe parameter editor.
"""
import os

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from core import ranges as R
from core import style as ST
from core.recipe import Recipe
from .i18n import APP_VERSION, AUTHOR, GITHUB_URL, load_config, save_config, t
from .theme import COLORS

# field rows: (key, label-key, kind, extra)
#   kind: 'combo' (extra = [(value,text)]), 'spin' (extra = (lo,hi,step)), 'kelvin'
#   label-key is looked up in i18n; the hover tip is 'tip_field_' + key (both live in ui/i18n.py)
ROWS = [
    ("style",   "f_style",   "style",  None),
    ("sat",     "f_sat",     "adj",    None),
    ("con",     "f_con",     "adj",    None),
    ("sharp",   "f_sharp",   "adj",    None),
    ("pe",      "f_pe",      "pe",     None),
    ("sub",     "f_sub",     "sub",    None),
    ("wb_mode", "f_wb_mode", "wb",     None),
    ("kelvin",  "f_kelvin",  "kelvin", None),
    ("ab",      "f_ab",      "ab",     None),
    ("gm",      "f_gm",      "gm",     None),
    ("ev",      "f_ev",      "ev",     None),
    ("dro",     "f_dro",     "dro",    None),
]


def ndarray_to_qimage(rgb):
    a = np.clip(np.asarray(rgb, float), 0, 1)
    a = (a * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, 2)
    h, w = a.shape[:2]
    img = QtGui.QImage(a.tobytes(), w, h, 3 * w, QtGui.QImage.Format_RGB888)
    return img.copy()


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")


def dropped_images(event):
    """the image paths a drag carries, in order — anything that is not an image file is skipped"""
    out = []
    for url in event.mimeData().urls():
        path = url.toLocalFile()
        if path and path.lower().endswith(IMAGE_EXTS):
            out.append(path)
    return out


def clip_overlay(rgb, shadow_on=True, high_on=True):
    """an RGBA overlay marking clipping the way Lightroom's triangles do: near-black pixels in blue,
    near-white in red. Only the requested kinds are drawn; returns None when nothing is marked, so
    the caller can skip the draw."""
    if rgb is None or not (shadow_on or high_on):
        return None
    a = np.clip(np.asarray(rgb, float), 0.0, 1.0)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    shadow = (lum < 0.02) if shadow_on else None
    high = (lum > 0.98) if high_on else None
    if not ((shadow is not None and shadow.any()) or (high is not None and high.any())):
        return None
    h, w = lum.shape
    buf = np.zeros((h, w, 4), np.uint8)
    if shadow is not None:
        buf[shadow] = (40, 130, 255, 150)
    if high is not None:
        buf[high] = (255, 60, 40, 150)
    return QtGui.QImage(buf.tobytes(), w, h, 4 * w, QtGui.QImage.Format_RGBA8888).copy()


class ViewState(QtCore.QObject):
    """the zoom and pan the two preview plates share, so both always show the same region"""

    changed = QtCore.Signal()
    MIN_ZOOM = 1.0
    MAX_ZOOM = 16.0

    def __init__(self):
        super().__init__()
        self.zoom = 1.0
        self.pan = [0.0, 0.0]        # a fraction of the fitted image size, so it survives a resize
        self._views = []

    def attach(self, view):
        self._views.append(view)

    def reset(self):
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.notify()

    def zoom_at(self, view, pos, factor):
        """zoom about a point in `view`, keeping whatever sits under the cursor in place.

        with the image centred at C + pan*fw and a point at u, px = C + pan*fw + (u-0.5)*fw*z, so
        the pan that keeps u under px at the new zoom is pan' = f*(1-k) + k*pan, where k = z'/z and
        f = (px-C)/fw. (the visible consequence: zooming on the centre leaves pan untouched.)"""
        z = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        if z == self.zoom:
            return
        fw, fh = view.fitted_size()
        if not fw or not fh:
            return
        k = z / self.zoom
        cx, cy = view.width() / 2.0, view.height() / 2.0
        fx = (pos.x() - cx) / fw
        fy = (pos.y() - cy) / fh
        self.zoom = z
        self.pan[0] = fx * (1.0 - k) + k * self.pan[0]
        self.pan[1] = fy * (1.0 - k) + k * self.pan[1]
        self.notify()

    def pan_by(self, view, dx, dy):
        fw, fh = view.fitted_size()
        if not fw or not fh:
            return
        self.pan[0] += dx / fw
        self.pan[1] += dy / fh
        self.notify()

    def clamp(self):
        """limit the pan so no image edge comes inside the viewport of any visible view — an axis may
        pan only as far as its own overflow, so a letterboxed axis stays put"""
        lim = None
        for v in self._views:
            if not v.isVisible():
                continue
            fw, fh = v.fitted_size()
            if not fw or not fh:
                continue
            lx = max(0.0, (fw * self.zoom - v.width()) / (2.0 * fw))
            ly = max(0.0, (fh * self.zoom - v.height()) / (2.0 * fh))
            lim = (lx, ly) if lim is None else (min(lim[0], lx), min(lim[1], ly))
        if lim is None:
            return
        self.pan[0] = max(-lim[0], min(lim[0], self.pan[0]))
        self.pan[1] = max(-lim[1], min(lim[1], self.pan[1]))

    def notify(self):
        self.clamp()
        for v in self._views:
            v.update()
        self.changed.emit()


class ImageView(QtWidgets.QWidget):
    """the preview plate: an RGB array on a canvas, zoomed by the wheel and panned by dragging.
    Also takes a dropped image file, and can tint clipped pixels for the LR-style warnings."""

    dropped = QtCore.Signal(list)

    def __init__(self, placeholder="NO IMAGE", state=None):
        super().__init__()
        self._img = None
        self._rgb = None
        self._ph = placeholder
        self.state = state or ViewState()
        if state is not None:
            state.attach(self)
        self.setMinimumSize(180, 140)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._drag = None
        self._clip_shadow = False
        self._clip_high = False
        self._overlay = None
        self._drop_hot = False

    def set_image(self, rgb):
        """keep the array as well as the QImage — the clipping overlay is computed from the array"""
        self._rgb = rgb
        self._img = None if rgb is None else ndarray_to_qimage(rgb)
        self._rebuild_overlay()
        self.update()

    def set_clip_flags(self, shadow_on, high_on):
        if (bool(shadow_on), bool(high_on)) == (self._clip_shadow, self._clip_high):
            return
        self._clip_shadow, self._clip_high = bool(shadow_on), bool(high_on)
        self._rebuild_overlay()
        self.update()

    def _rebuild_overlay(self):
        self._overlay = clip_overlay(self._rgb, self._clip_shadow, self._clip_high)

    # ------------------------------------------------------------ geometry
    def fitted_size(self):
        """the size the image takes at zoom 1 — squeezed to fit inside the plate"""
        if self._img is None:
            return 0.0, 0.0
        iw, ih = self._img.width(), self._img.height()
        if iw <= 0 or ih <= 0:
            return 0.0, 0.0
        s = min(self.width() / iw, self.height() / ih)
        return iw * s, ih * s

    def _draw_rect(self):
        fw, fh = self.fitted_size()
        if not fw or not fh:
            return QtCore.QRectF()
        w, h = fw * self.state.zoom, fh * self.state.zoom
        # the float centre, not QRect.center() — that truncates and would bias the clamp by a pixel
        cx = self.width() / 2.0 + self.state.pan[0] * fw
        cy = self.height() / 2.0 + self.state.pan[1] * fh
        return QtCore.QRectF(cx - w / 2.0, cy - h / 2.0, w, h)

    # ------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drop_hot = True
            self.update()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._drop_hot = False
        self.update()

    def dropEvent(self, e):
        if not e.mimeData().hasUrls():
            return
        e.acceptProposedAction()
        self._drop_hot = False
        self.update()
        self.dropped.emit(dropped_images(e))

    # ------------------------------------------------------------ interaction
    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if not dy or self._img is None:
            return
        self.state.zoom_at(self, e.position(), 1.25 ** (dy / 120.0))
        e.accept()

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton and self._img is not None:
            self._drag = e.position()
            self.setCursor(QtCore.Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is None:
            return
        p = e.position()
        self.state.pan_by(self, p.x() - self._drag.x(), p.y() - self._drag.y())
        self._drag = p

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton and self._drag is not None:
            self._drag = None
            self.unsetCursor()

    def mouseDoubleClickEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self.state.reset()

    # ------------------------------------------------------------ paint
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        r = self.rect()
        p.fillRect(r, QtGui.QColor(COLORS["canvas"]))
        if self._img is None:
            p.setPen(QtGui.QColor(COLORS["muted"]))
            p.drawText(r, QtCore.Qt.AlignCenter, self._ph)
        else:
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, self.state.zoom < 2.5)
            p.drawImage(self._draw_rect(), self._img)
            if self._overlay is not None:
                p.drawImage(self._draw_rect(), self._overlay)
        if self._drop_hot:
            p.setPen(QtGui.QPen(QtGui.QColor(COLORS["accent"]), 2, QtCore.Qt.DashLine))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRect(r.adjusted(2, 2, -3, -3))


class SplitView(QtWidgets.QWidget):
    """before/after wipe: one plate, the original on one side of a draggable line and the result on
    the other, sharing the same zoom and pan as the side-by-side plates. The divider can be vertical
    (wipe left/right) or horizontal (wipe top/bottom)."""

    GRAB = 9          # px each side of the line that grabs the divider instead of panning

    dropped = QtCore.Signal(list)

    def __init__(self, state, placeholder="NO IMAGE"):
        super().__init__()
        self._src = None
        self._out = None
        self._src_rgb = None
        self._out_rgb = None
        self._overlay_src = None
        self._overlay_out = None
        self._ph = placeholder
        self.state = state
        state.attach(self)
        self.split = 0.5
        self.vertical = True          # True: vertical divider, the halves wipe left/right
        self.setMinimumSize(180, 140)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._drag = None
        self._hot = False
        self._clip_shadow = False
        self._clip_high = False
        self._drop_hot = False

    def set_images(self, src_rgb, out_rgb):
        self._src_rgb, self._out_rgb = src_rgb, out_rgb
        self._src = None if src_rgb is None else ndarray_to_qimage(src_rgb)
        self._out = None if out_rgb is None else ndarray_to_qimage(out_rgb)
        self._rebuild_overlays()
        self.update()

    def set_orientation(self, vertical):
        self.vertical = bool(vertical)
        self.update()

    def set_clip_flags(self, shadow_on, high_on):
        if (bool(shadow_on), bool(high_on)) == (self._clip_shadow, self._clip_high):
            return
        self._clip_shadow, self._clip_high = bool(shadow_on), bool(high_on)
        self._rebuild_overlays()
        self.update()

    def _rebuild_overlays(self):
        self._overlay_src = clip_overlay(self._src_rgb, self._clip_shadow, self._clip_high)
        self._overlay_out = clip_overlay(self._out_rgb, self._clip_shadow, self._clip_high)

    @property
    def comparable(self):
        return self._src is not None and self._out is not None

    # ------------------------------------------------------------ geometry (same contract as ImageView)
    def _ref(self):
        return self._src if self._src is not None else self._out

    def fitted_size(self):
        img = self._ref()
        if img is None:
            return 0.0, 0.0
        iw, ih = img.width(), img.height()
        if iw <= 0 or ih <= 0:
            return 0.0, 0.0
        s = min(self.width() / iw, self.height() / ih)
        return iw * s, ih * s

    def _draw_rect(self):
        fw, fh = self.fitted_size()
        if not fw or not fh:
            return QtCore.QRectF()
        w, h = fw * self.state.zoom, fh * self.state.zoom
        cx = self.width() / 2.0 + self.state.pan[0] * fw
        cy = self.height() / 2.0 + self.state.pan[1] * fh
        return QtCore.QRectF(cx - w / 2.0, cy - h / 2.0, w, h)

    def _line_pos(self):
        return self.split * (self.width() if self.vertical else self.height())

    def _near_line(self, pos):
        if not self.comparable:
            return False
        v = pos.x() if self.vertical else pos.y()
        return abs(v - self._line_pos()) <= self.GRAB

    def _split_cursor(self):
        return QtCore.Qt.SplitHCursor if self.vertical else QtCore.Qt.SplitVCursor

    # ------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drop_hot = True
            self.update()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._drop_hot = False
        self.update()

    def dropEvent(self, e):
        if not e.mimeData().hasUrls():
            return
        e.acceptProposedAction()
        self._drop_hot = False
        self.update()
        self.dropped.emit(dropped_images(e))

    # ------------------------------------------------------------ interaction
    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if not dy or self._ref() is None:
            return
        self.state.zoom_at(self, e.position(), 1.25 ** (dy / 120.0))
        e.accept()

    def mousePressEvent(self, e):
        if e.button() != QtCore.Qt.LeftButton or self._ref() is None:
            return
        p = e.position()
        if self._near_line(p):
            self._drag = ("split", p)                     # grab the divider
            self.setCursor(self._split_cursor())
        else:
            self._drag = ("pan", p)
            self.setCursor(QtCore.Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        p = e.position()
        if self._drag is None:
            hot = self._near_line(p)
            if hot != self._hot:
                self._hot = hot
                self.setCursor(self._split_cursor() if hot else QtCore.Qt.ArrowCursor)
            return
        kind, anchor = self._drag
        if kind == "split":
            if self.vertical:
                self.split = max(0.0, min(1.0, p.x() / max(1.0, float(self.width()))))
            else:
                self.split = max(0.0, min(1.0, p.y() / max(1.0, float(self.height()))))
            self.update()
        else:
            self.state.pan_by(self, p.x() - anchor.x(), p.y() - anchor.y())
            self._drag = ("pan", p)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton and self._drag is not None:
            self._drag = None
            self._hot = False
            self.unsetCursor()

    def mouseDoubleClickEvent(self, e):
        if e.button() != QtCore.Qt.LeftButton:
            return
        if self._near_line(e.position()):
            self.split = 0.5
            self.update()
        else:
            self.state.reset()

    # ------------------------------------------------------------ paint
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        r = self.rect()
        w, h = float(r.width()), float(r.height())
        p.fillRect(r, QtGui.QColor(COLORS["canvas"]))
        rect = self._draw_rect()
        if rect.isNull():
            p.setPen(QtGui.QColor(COLORS["muted"]))
            p.drawText(r, QtCore.Qt.AlignCenter, self._ph)
            return
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, self.state.zoom < 2.5)
        if self._out is not None:
            p.drawImage(rect, self._out)
            if self._overlay_out is not None:
                p.drawImage(rect, self._overlay_out)
        if self._src is None:
            return
        if not self.comparable:
            p.drawImage(rect, self._src)
            if self._overlay_src is not None:
                p.drawImage(rect, self._overlay_src)
            return
        pos = self._line_pos()
        # the original, clipped to its side of the divider — left when vertical, above when horizontal
        if self.vertical:
            clip = QtCore.QRectF(0.0, 0.0, pos, h)
            d1, d2 = QtCore.QPointF(pos + 1.0, 0.0), QtCore.QPointF(pos + 1.0, h)
            handle = QtCore.QRectF(pos - 7.0, h / 2.0 - 13.0, 14.0, 26.0)
        else:
            clip = QtCore.QRectF(0.0, 0.0, w, pos)
            d1, d2 = QtCore.QPointF(0.0, pos + 1.0), QtCore.QPointF(w, pos + 1.0)
            handle = QtCore.QRectF(w / 2.0 - 13.0, pos - 7.0, 26.0, 14.0)
        p.save()
        p.setClipRect(clip)
        p.drawImage(rect, self._src)
        if self._overlay_src is not None:
            p.drawImage(rect, self._overlay_src)
        p.restore()
        # the divider and its handle
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 130), 1))
        p.drawLine(d1, d2)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 210), 1))
        if self.vertical:
            p.drawLine(QtCore.QPointF(pos, 0.0), QtCore.QPointF(pos, h))
        else:
            p.drawLine(QtCore.QPointF(0.0, pos), QtCore.QPointF(w, pos))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, 225))
        p.drawRoundedRect(handle, 3.0, 3.0)
        p.setPen(QtGui.QPen(QtGui.QColor(60, 60, 60, 220), 1))
        cx, cy = handle.center().x(), handle.center().y()
        for d in (-4.0, 0.0, 4.0):
            if self.vertical:
                p.drawLine(QtCore.QPointF(pos - 3.0, cy + d), QtCore.QPointF(pos + 3.0, cy + d))
            else:
                p.drawLine(QtCore.QPointF(cx + d, pos - 3.0), QtCore.QPointF(cx + d, pos + 3.0))
        # which half is which
        cap = QtCore.QRectF(r.left() + 7.0, r.top() + 5.0, w - 14.0, 18.0)
        p.setPen(QtGui.QColor(COLORS["cap_text"]))
        p.drawText(cap, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, t("label_src"))
        p.drawText(cap, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, t("label_result"))
        if self._drop_hot:
            p.setPen(QtGui.QPen(QtGui.QColor(COLORS["accent"]), 2, QtCore.Qt.DashLine))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRect(r.adjusted(2, 2, -3, -3))


class DropButton(QtWidgets.QPushButton):
    """a push button that also accepts a dropped image (or set of images), highlighting while the
    drag hovers over it"""

    dropped = QtCore.Signal(list)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self._hot = False

    def _set_hot(self, on):
        if on == self._hot:
            return
        self._hot = on
        self.setProperty("dropHot", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_hot(True)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._set_hot(False)

    def dropEvent(self, e):
        if not e.mimeData().hasUrls():
            return
        e.acceptProposedAction()
        self._set_hot(False)
        self.dropped.emit(dropped_images(e))


class BarReadout(QtWidgets.QWidget):
    """a flat progress strip: the filled fraction in one colour, the rest an empty groove"""

    def __init__(self):
        super().__init__()
        self._v = 0.0
        self._col = None
        self.setFixedHeight(6)
        self.setMinimumWidth(70)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def set_value(self, v, col=None):
        v = 0.0 if v is None else float(max(0.0, min(1.0, v)))
        if v == self._v and col == self._col:
            return
        self._v = v
        self._col = col
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        r = self.rect()
        radius = max(2.0, r.height() / 2.0)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(COLORS["bar_groove"]))
        p.drawRoundedRect(QtCore.QRectF(r), radius, radius)
        w = r.width() * self._v
        if w > 0.5:
            p.setBrush(QtGui.QColor(self._col or COLORS["accent"]))
            p.drawRoundedRect(QtCore.QRectF(r.left(), r.top(), max(w, 2.0 * radius), r.height()),
                              radius, radius)


class ScoreStrip(QtWidgets.QWidget):
    """the residual split into the parts a photographer names: five mini bars with their values"""

    METRICS = [("light", "m_light", "md_light"),
               ("sat", "m_sat", "md_sat"),
               ("warm", "m_warm", "md_warm"),
               ("skin", "m_skin", "md_skin"),
               ("tone", "m_tone", "md_tone")]

    def __init__(self):
        super().__init__()
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self._cells = {}
        for key, label_key, desc_key in self.METRICS:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(3)
            label = t(label_key)
            lab = QtWidgets.QLabel(label + " —")
            lab.setObjectName("Stencil")
            lab.setToolTip(t(desc_key))
            bar = BarReadout()
            bar.setMinimumWidth(52)
            self._cells[key] = (lab, bar, label)
            col.addWidget(lab)
            col.addWidget(bar)
            row.addLayout(col, 1)
        self.clear()

    def clear(self):
        for lab, bar, base in self._cells.values():
            lab.setText(base + " —")
            bar.set_value(0.0, COLORS["muted"])

    def set_scores(self, scores):
        """scores: {key: value-in-Lab-units or None}; None shows a dash for a term the frame has
        no data for (e.g. no skin)"""
        for key, (lab, bar, base) in self._cells.items():
            v = scores.get(key)
            if v is None:
                lab.setText(base + " —")
                bar.set_value(0.0, COLORS["muted"])
            else:
                col = COLORS["good"] if v <= 2.0 else COLORS["warn"] if v <= 5.0 else COLORS["bad"]
                lab.setText("%s %.1f" % (base, v))
                bar.set_value(max(0.0, 1.0 - v / 10.0), col)
        self.setToolTip(t("score_tip"))


# ------------------------------------------------------------ histogram
def _hist_bins(rgb):
    """256-bin R/G/B and luma histograms of an RGB array"""
    a = np.clip(np.asarray(rgb, float), 0.0, 1.0)
    v = (a * 255.0 + 0.5).astype(np.uint8)
    out = {}
    for i, key in enumerate(("r", "g", "b")):
        out[key] = np.bincount(v[..., i].ravel(), minlength=256).astype(np.float64)
    lum = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]) * 255.0 + 0.5
    out["l"] = np.bincount(lum.astype(np.uint8).ravel(), minlength=256).astype(np.float64)
    return out


class _HistPlot(QtWidgets.QWidget):
    """the plot itself: R/G/B added together in colour, luma drawn as a line on top"""

    CHANNELS = (("r", "#ff3b30"), ("g", "#32d74b"), ("b", "#0a84ff"))

    def __init__(self):
        super().__init__()
        self._bins = None
        self.setMinimumHeight(64)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setFixedHeight(78)

    def set_bins(self, bins):
        self._bins = bins
        self.update()

    def _path(self, arr, peak, w, h):
        path = QtGui.QPainterPath()
        path.moveTo(0.0, h)
        for i in range(256):
            path.lineTo(w * i / 255.0, h - min(1.0, arr[i] / peak) * h)
        path.lineTo(w, h)
        path.closeSubpath()
        return path

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        r = self.rect()
        w, h = float(r.width()), float(r.height())
        p.fillRect(r, QtGui.QColor(COLORS["canvas"]))
        p.setPen(QtGui.QPen(QtGui.QColor(COLORS["line"]), 1))
        for f in (0.25, 0.5, 0.75):
            x = w * f
            p.drawLine(QtCore.QPointF(x, 0.0), QtCore.QPointF(x, h))
        if self._bins is None:
            return
        peak = max(1.0, float(self._bins["l"].max()))
        p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        p.setPen(QtCore.Qt.NoPen)
        for key, col in self.CHANNELS:
            c = QtGui.QColor(col)
            c.setAlpha(82)
            p.setBrush(c)
            p.drawPath(self._path(self._bins[key], peak, w, h))
        p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
        p.setPen(QtGui.QPen(QtGui.QColor(COLORS["text"]), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawPath(self._path(self._bins["l"], peak, w, h))


class Histogram(QtWidgets.QWidget):
    """Lightroom's histogram block: the RGB plot, a before/after switch, the clipping toggles and the
    exposure metadata line underneath."""

    mode_changed = QtCore.Signal(str)          # 'before' | 'after'

    def __init__(self, parent=None):
        super().__init__(parent)
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(5)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        self.btn_mode = QtWidgets.QPushButton(t("hist_before"))
        self.btn_mode.setCheckable(True)
        self.btn_mode.setToolTip(t("tip_hist_switch"))
        self.btn_mode.toggled.connect(self._on_mode)
        row.addWidget(self.btn_mode)
        row.addStretch(1)
        self.btn_shadow = QtWidgets.QToolButton()
        self.btn_shadow.setText(t("clip_shadow"))
        self.btn_shadow.setCheckable(True)
        self.btn_shadow.setToolTip(t("tip_clip_shadow"))
        row.addWidget(self.btn_shadow)
        self.btn_high = QtWidgets.QToolButton()
        self.btn_high.setText(t("clip_high"))
        self.btn_high.setCheckable(True)
        self.btn_high.setToolTip(t("tip_clip_high"))
        row.addWidget(self.btn_high)
        col.addLayout(row)

        self.plot = _HistPlot()
        col.addWidget(self.plot)

        self.lbl_meta = QtWidgets.QLabel(t("meta_none"))
        self.lbl_meta.setObjectName("Muted")
        col.addWidget(self.lbl_meta)
        self._after = False

    @property
    def after_mode(self):
        return self._after

    def _on_mode(self, on):
        self._after = bool(on)
        self.btn_mode.setText(t("hist_after") if on else t("hist_before"))
        self.mode_changed.emit("after" if on else "before")

    def set_rgb(self, rgb):
        self.plot.set_bins(None if rgb is None else _hist_bins(rgb))

    def clear(self):
        self.plot.set_bins(None)

    def set_meta(self, text):
        self.lbl_meta.setText(text or t("meta_none"))


# ------------------------------------------------------------ portfolio browser
THUMB = 96


class _ThumbSignals(QtCore.QObject):
    one = QtCore.Signal(int, object)


class _ThumbTask(QtCore.QRunnable):
    """load a set of thumbnails one at a time, emitting each as it becomes ready — so a big set fills
    in progressively instead of freezing the window"""

    def __init__(self, paths, signals):
        super().__init__()
        self.paths = paths
        self.signals = signals

    @QtCore.Slot()
    def run(self):
        for i, p in enumerate(self.paths):
            try:
                rgb = ST.thumb_rgb(ST.load_rgb(p, 512), THUMB)
            except Exception:                  # noqa: BLE001 - an unreadable file just shows no icon
                continue
            self.signals.one.emit(i, rgb)


class PortfolioDialog(QtWidgets.QDialog):
    """the browser for a colour-target set: a thumbnail grid where each photo is ticked to say it
    takes part in the fit. Non-modal, so the main window stays usable while you tick."""

    selection_changed = QtCore.Signal(list)

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("portfolio_view_title"))
        self.resize(860, 600)
        self._paths = list(paths)
        self._guard = False

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        head = QtWidgets.QHBoxLayout()
        self.lbl_count = QtWidgets.QLabel("")
        head.addWidget(self.lbl_count)
        head.addStretch(1)
        b_all = QtWidgets.QPushButton(t("btn_all"))
        b_all.setToolTip(t("portfolio_pick_hint"))
        b_all.clicked.connect(lambda: self._set_all(True))
        b_none = QtWidgets.QPushButton(t("btn_none"))
        b_none.setToolTip(t("portfolio_pick_hint"))
        b_none.clicked.connect(lambda: self._set_all(False))
        head.addWidget(b_all)
        head.addWidget(b_none)
        outer.addLayout(head)

        hint = QtWidgets.QLabel(t("portfolio_pick_hint"))
        hint.setObjectName("Muted")
        outer.addWidget(hint)

        self.list = QtWidgets.QListWidget()
        self.list.setViewMode(QtWidgets.QListView.IconMode)
        self.list.setIconSize(QtCore.QSize(THUMB, THUMB))
        self.list.setGridSize(QtCore.QSize(THUMB + 28, THUMB + 46))
        self.list.setResizeMode(QtWidgets.QListView.Adjust)
        self.list.setMovement(QtWidgets.QListView.Static)
        self.list.setUniformItemSizes(True)
        self.list.setWordWrap(True)
        self.list.itemChanged.connect(self._on_item_changed)
        outer.addWidget(self.list, 1)

        self._items = []
        for p in self._paths:
            it = QtWidgets.QListWidgetItem(os.path.basename(p))
            it.setToolTip(p)
            it.setFlags(it.flags() | QtCore.Qt.ItemIsUserCheckable)
            it.setCheckState(QtCore.Qt.Checked)
            self.list.addItem(it)
            self._items.append(it)

        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        b_close = QtWidgets.QPushButton(t("about_close"))
        b_close.clicked.connect(self.close)
        row.addWidget(b_close)
        outer.addLayout(row)

        self._update_count()
        self._signals = _ThumbSignals()
        self._signals.one.connect(self._fill_thumb)
        self._pool = QtCore.QThreadPool()
        self._task = _ThumbTask(self._paths, self._signals)
        self._pool.start(self._task)

    # ------------------------------------------------------------ selection
    def selected_paths(self):
        return [p for p, it in zip(self._paths, self._items)
                if it.checkState() == QtCore.Qt.Checked]

    def sync(self, paths):
        """set the tick state from a list of paths, without emitting (the caller already knows)"""
        want = set(paths)
        self._guard = True
        for p, it in zip(self._paths, self._items):
            it.setCheckState(QtCore.Qt.Checked if p in want else QtCore.Qt.Unchecked)
        self._guard = False
        self._update_count()

    def _set_all(self, on):
        self._guard = True
        state = QtCore.Qt.Checked if on else QtCore.Qt.Unchecked
        for it in self._items:
            it.setCheckState(state)
        if not on and self._items:                 # never let the set go empty
            self._items[0].setCheckState(QtCore.Qt.Checked)
        self._guard = False
        self._update_count()
        self.selection_changed.emit(self.selected_paths())

    def _on_item_changed(self, item):
        if self._guard:
            return
        if not self.selected_paths():
            self._guard = True
            item.setCheckState(QtCore.Qt.Checked)
            self._guard = False
            QtWidgets.QMessageBox.information(self, t("portfolio_view_title"),
                                              t("portfolio_need_one"))
        self._update_count()
        self.selection_changed.emit(self.selected_paths())

    def _update_count(self):
        n = len(self.selected_paths())
        text = t("portfolio_view_count", n, len(self._paths))
        if n < 2:
            text += " " + t("portfolio_few_hint")
        self.lbl_count.setText(text)

    # ------------------------------------------------------------ thumbnails
    def _fill_thumb(self, i, rgb):
        if rgb is None or i >= len(self._items):
            return
        self._guard = True
        try:
            self._items[i].setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(ndarray_to_qimage(rgb))))
        finally:
            self._guard = False


class Module(QtWidgets.QFrame):
    """a flat panel: a title row, a hairline rule and the body. Content goes into `self.body`"""

    def __init__(self, title, code=""):
        super().__init__()
        self.setObjectName("Module")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(9)
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)
        self.title = QtWidgets.QLabel(title)
        self.title.setObjectName("ModTitle")
        head.addWidget(self.title)
        self.code = QtWidgets.QLabel(code)
        self.code.setObjectName("ModNum")
        head.addWidget(self.code)
        self.head = head
        head.addStretch(1)
        outer.addLayout(head)
        rule = QtWidgets.QFrame()
        rule.setObjectName("PanelRule")
        rule.setFixedHeight(1)
        outer.addWidget(rule)
        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body, 1)

    def set_code(self, text):
        self.code.setText(text)

    def add_head_widget(self, w):
        """put a control in the title row, past the stretch — so it sits at the panel's right edge"""
        self.head.insertWidget(self.head.count() - 1, w)


class ParamEditor(QtWidgets.QWidget):
    """the 12 recipe fields as a form; emits changed() with the current Recipe"""

    changed = QtCore.Signal()

    def __init__(self, recipe=None):
        super().__init__()
        self._r = recipe
        self._rows = {}
        self._building = False
        self._build()

    # ------------------------------------------------------------ build
    def _build(self):
        form = QtWidgets.QFormLayout(self)
        form.setLabelAlignment(QtCore.Qt.AlignRight)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setContentsMargins(2, 2, 2, 2)
        form.setSpacing(7)
        for key, label_key, kind, _ in ROWS:
            lab = QtWidgets.QLabel(t(label_key))
            lab.setObjectName("Stencil")
            lab.setToolTip(t("tip_field_" + key))
            w = self._make_widget(kind)
            w.setObjectName(key)
            self._rows[key] = w
            form.addRow(lab, w)
        self.set_recipe(self._r)

    def _make_widget(self, kind):
        if kind == "style":
            cb = QtWidgets.QComboBox()
            for i in range(len(R.STYLE_NAMES)):
                if R.style_known(i):
                    cb.addItem(R.STYLE_LABEL[i], i)
            cb.currentIndexChanged.connect(self._emit)
            return cb
        if kind == "pe":
            cb = QtWidgets.QComboBox()
            for i, lab in enumerate(R.PE_LABEL):
                cb.addItem(lab, i)
            cb.currentIndexChanged.connect(self._pe_changed)
            return cb
        if kind == "sub":
            return QtWidgets.QComboBox()
        if kind == "wb":
            cb = QtWidgets.QComboBox()
            cb.addItem(t("wb_auto"), R.WB_AUTO)
            cb.addItem(t("wb_kelvin"), R.WB_KELVIN)
            cb.addItem(t("wb_keep"), 0)
            cb.currentIndexChanged.connect(self._wb_changed)
            return cb
        if kind == "kelvin":
            sp = QtWidgets.QSpinBox()
            sp.setRange(R.KELVIN_MIN * 100, R.KELVIN_MAX * 100)
            sp.setSingleStep(100)
            sp.setSuffix(" K")
            sp.valueChanged.connect(self._emit)
            return sp
        if kind == "dro":
            cb = QtWidgets.QComboBox()
            cb.addItem(t("dro_off"), R.DRO_OFF)
            cb.addItem(t("dro_auto"), R.DRO_AUTO)
            for n in range(1, 6):
                cb.addItem("Lv%d" % n, n)
            cb.currentIndexChanged.connect(self._emit)
            return cb
        if kind == "ev":
            sp = QtWidgets.QSpinBox()
            sp.setRange(R.EV_MIN, R.EV_MAX)
            sp.setSingleStep(1)
            sp.valueChanged.connect(self._ev_changed)
            return sp
        if kind == "ab":
            sp = QtWidgets.QSpinBox()
            sp.setRange(R.AB_MIN, R.AB_MAX)
            sp.valueChanged.connect(self._emit)
            return sp
        if kind == "gm":
            sp = QtWidgets.QSpinBox()
            sp.setRange(R.GM_MIN, R.GM_MAX)
            sp.valueChanged.connect(self._emit)
            return sp
        if kind == "adj":
            sp = QtWidgets.QSpinBox()
            sp.setRange(R.ADJ_MIN, R.ADJ_MAX)
            sp.valueChanged.connect(self._emit)
            return sp
        return QtWidgets.QLineEdit()

    # ------------------------------------------------------------ set / get
    def set_recipe(self, r):
        self._building = True
        self._r = r
        if r is None:
            for w in self._rows.values():
                w.setEnabled(False)
            self._building = False
            return
        for w in self._rows.values():
            w.setEnabled(True)
        self._select(self._rows["style"], r.style)
        for k in ("sat", "con", "sharp"):
            self._rows[k].setValue(r.__getattribute__(k))
        self._select(self._rows["pe"], r.pe)
        self._rebuild_sub(r.pe, r.sub)
        self._select(self._rows["wb_mode"], r.wb_mode)
        self._rows["kelvin"].setValue(r.kelvin if r.kelvin else 5600)
        self._rows["kelvin"].setEnabled(r.wb_mode == R.WB_KELVIN)
        self._rows["ab"].setValue(r.ab)
        self._rows["gm"].setValue(r.gm)
        self._rows["ev"].setValue(r.ev)
        self._update_ev_suffix(r.ev)
        self._select(self._rows["dro"], r.dro)
        self._refresh_sub_enabled(r.pe)
        self._building = False

    def _select(self, combo, value):
        i = combo.findData(value)
        combo.setCurrentIndex(i if i >= 0 else 0)

    def _rebuild_sub(self, pe, sub):
        cb = self._rows["sub"]
        cb.blockSignals(True)
        cb.clear()
        sv = R.sub_values(pe)
        if sv:
            for i, name in enumerate(sv):
                cb.addItem(name.replace("posterization-", ""), i)
            cb.setCurrentIndex(min(max(sub, 0), len(sv) - 1))
        cb.blockSignals(False)
        cb.setEnabled(bool(sv))

    def _refresh_sub_enabled(self, pe):
        self._rows["sub"].setEnabled(bool(R.sub_values(pe)))

    def _update_ev_suffix(self, ev):
        self._rows["ev"].setSuffix("  (" + R.ev_label(ev) + ")")

    # ------------------------------------------------------------ reactions
    def _ev_changed(self, v):
        self._update_ev_suffix(v)
        self._emit()

    def _wb_changed(self):
        wb = self._rows["wb_mode"].currentData()
        self._rows["kelvin"].setEnabled(wb == R.WB_KELVIN)
        self._emit()

    def _pe_changed(self):
        pe = self._rows["pe"].currentData()
        self._rebuild_sub(pe, 0)
        self._emit()

    def _emit(self):
        if self._building:
            return
        self.changed.emit()

    # ------------------------------------------------------------ read out
    def recipe(self, name=None, group=R.CUSTOM):
        r = self._r or None
        return Recipe(
            group=r.group if r else group,
            name=name if name is not None else (r.name if r else ""),
            style=self._rows["style"].currentData(),
            sat=self._rows["sat"].value(),
            con=self._rows["con"].value(),
            sharp=self._rows["sharp"].value(),
            wb_mode=self._rows["wb_mode"].currentData(),
            kelvin=self._rows["kelvin"].value() if self._rows["wb_mode"].currentData() == R.WB_KELVIN else 0,
            ab=self._rows["ab"].value(),
            gm=self._rows["gm"].value(),
            pe=self._rows["pe"].currentData(),
            ev=self._rows["ev"].value(),
            dro=self._rows["dro"].currentData(),
            sub=self._rows["sub"].currentData() or 0,
        )


class SettingsDialog(QtWidgets.QDialog):
    """program settings. Today the only entry is the image-processing mode: CPU soft decode is the
    one implementation, and the GPU hardware option is shown greyed as a placeholder for later."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(440)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

        head = QtWidgets.QLabel(t("settings_sec"))
        head.setObjectName("ModTitle")
        outer.addWidget(head)
        note = QtWidgets.QLabel(t("settings_note"))
        note.setObjectName("Muted")
        note.setWordWrap(True)
        outer.addWidget(note)

        group = QtWidgets.QButtonGroup(self)
        self.rb_cpu = QtWidgets.QRadioButton(t("settings_cpu"))
        self.rb_cpu.setToolTip(t("settings_cpu_tip"))
        self.rb_cpu.setChecked(True)
        self.rb_gpu = QtWidgets.QRadioButton(t("settings_gpu"))
        self.rb_gpu.setToolTip(t("settings_gpu_tip"))
        self.rb_gpu.setEnabled(False)
        group.addButton(self.rb_cpu)
        group.addButton(self.rb_gpu)
        outer.addWidget(self.rb_cpu)
        outer.addWidget(self.rb_gpu)

        hint = QtWidgets.QLabel(t("settings_hint"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        self.chk_donate = QtWidgets.QCheckBox(t("settings_donate"))
        self.chk_donate.setToolTip(t("settings_donate_tip"))
        self.chk_donate.setChecked(bool(load_config().get("donate_popup", True)))
        outer.addWidget(self.chk_donate)

        outer.addStretch(1)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        b_ok = QtWidgets.QPushButton(t("btn_ok"))
        b_ok.setObjectName("Accent")
        b_ok.setToolTip(t("tip_ok"))
        b_ok.clicked.connect(self.accept)
        row.addWidget(b_ok)
        outer.addLayout(row)

    def accept(self):
        save_config(donate_popup=self.chk_donate.isChecked())
        super().accept()


class AboutDialog(QtWidgets.QDialog):
    """the About box: version, the copyright holder, the free-of-charge notice and the release URL.

    The holder's name and the repository URL live in ui/i18n.py (AUTHOR / GITHUB_URL) — fill them in
    before publishing; a placeholder prints as-is so it is obvious it still needs replacing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("about_title"))
        self.setMinimumWidth(480)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(9)

        title = QtWidgets.QLabel(t("app_name"))
        title.setObjectName("AppTitle")
        outer.addWidget(title)
        ver = QtWidgets.QLabel(t("about_version", APP_VERSION))
        ver.setObjectName("Muted")
        outer.addWidget(ver)

        who = QtWidgets.QLabel(t("about_role") + ": " + AUTHOR)
        outer.addWidget(who)
        rights = QtWidgets.QLabel(t("about_rights", AUTHOR))
        rights.setObjectName("Muted")
        outer.addWidget(rights)

        free_title = QtWidgets.QLabel(t("about_free_title"))
        free_title.setObjectName("ModTitle")
        outer.addWidget(free_title)
        free_body = QtWidgets.QLabel(t("about_free_body"))
        free_body.setObjectName("Muted")
        free_body.setWordWrap(True)
        outer.addWidget(free_body)

        repo_title = QtWidgets.QLabel(t("about_repo"))
        repo_title.setObjectName("ModTitle")
        outer.addWidget(repo_title)
        repo = QtWidgets.QLabel()
        if GITHUB_URL.startswith("http"):
            repo.setText('<a href="%s">%s</a>' % (GITHUB_URL, GITHUB_URL))
            repo.setOpenExternalLinks(True)
        else:
            repo.setText(GITHUB_URL)
        repo.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        repo.setWordWrap(True)
        outer.addWidget(repo)

        outer.addStretch(1)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        b_ok = QtWidgets.QPushButton(t("about_close"))
        b_ok.setObjectName("Accent")
        b_ok.clicked.connect(self.accept)
        row.addWidget(b_ok)
        outer.addLayout(row)
