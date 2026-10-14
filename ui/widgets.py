"""Adobe-style flat widgets: the shared zoom/pan state, the preview plate, the bar readout, the
panel module, and the recipe parameter editor.
"""
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from core import ranges as R
from core.recipe import Recipe
from .i18n import APP_VERSION, AUTHOR, GITHUB_URL, t
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
    """the preview plate: an RGB array on a dark canvas, zoomed by the wheel and panned by dragging"""

    def __init__(self, placeholder="NO IMAGE", state=None):
        super().__init__()
        self._img = None
        self._ph = placeholder
        self.state = state or ViewState()
        if state is not None:
            state.attach(self)
        self.setMinimumSize(180, 140)
        self.setMouseTracking(True)
        self._drag = None

    def set_image(self, rgb):
        self._img = None if rgb is None else ndarray_to_qimage(rgb)
        self.update()

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
            return
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, self.state.zoom < 2.5)
        p.drawImage(self._draw_rect(), self._img)


class SplitView(QtWidgets.QWidget):
    """before/after wipe: one plate, the original left of a draggable line and the result right of it,
    sharing the same zoom and pan as the side-by-side plates"""

    GRAB = 9          # px each side of the line that grabs the divider instead of panning

    def __init__(self, state, placeholder="NO IMAGE"):
        super().__init__()
        self._src = None
        self._out = None
        self._ph = placeholder
        self.state = state
        state.attach(self)
        self.split = 0.5
        self.setMinimumSize(180, 140)
        self.setMouseTracking(True)
        self._drag = None
        self._hot = False

    def set_images(self, src_rgb, out_rgb):
        self._src = None if src_rgb is None else ndarray_to_qimage(src_rgb)
        self._out = None if out_rgb is None else ndarray_to_qimage(out_rgb)
        self.update()

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

    def _line_x(self):
        return self.split * self.width()

    def _near_line(self, pos):
        return self.comparable and abs(pos.x() - self._line_x()) <= self.GRAB

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
            self.setCursor(QtCore.Qt.SplitHCursor)
        else:
            self._drag = ("pan", p)
            self.setCursor(QtCore.Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        p = e.position()
        if self._drag is None:
            hot = self._near_line(p)
            if hot != self._hot:
                self._hot = hot
                self.setCursor(QtCore.Qt.SplitHCursor if hot else QtCore.Qt.ArrowCursor)
            return
        kind, anchor = self._drag
        if kind == "split":
            self.split = max(0.0, min(1.0, p.x() / max(1.0, float(self.width()))))
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
        p.fillRect(r, QtGui.QColor(COLORS["canvas"]))
        rect = self._draw_rect()
        if rect.isNull():
            p.setPen(QtGui.QColor(COLORS["muted"]))
            p.drawText(r, QtCore.Qt.AlignCenter, self._ph)
            return
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, self.state.zoom < 2.5)
        if self._out is not None:
            p.drawImage(rect, self._out)
        if self._src is None:
            return
        if not self.comparable:
            p.drawImage(rect, self._src)
            return
        x = self._line_x()
        # the original, clipped to the left of the divider
        p.save()
        p.setClipRect(QtCore.QRectF(0.0, 0.0, x, float(r.height())))
        p.drawImage(rect, self._src)
        p.restore()
        # the divider and its handle
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 130), 1))
        p.drawLine(QtCore.QPointF(x + 1.0, 0.0), QtCore.QPointF(x + 1.0, float(r.height())))
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 210), 1))
        p.drawLine(QtCore.QPointF(x, 0.0), QtCore.QPointF(x, float(r.height())))
        cy = r.height() / 2.0
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, 225))
        p.drawRoundedRect(QtCore.QRectF(x - 7.0, cy - 13.0, 14.0, 26.0), 3.0, 3.0)
        p.setPen(QtGui.QPen(QtGui.QColor(60, 60, 60, 220), 1))
        for dy in (-4.0, 0.0, 4.0):
            p.drawLine(QtCore.QPointF(x - 3.0, cy + dy), QtCore.QPointF(x + 3.0, cy + dy))
        # which half is which
        cap = QtCore.QRectF(r.left() + 7.0, r.top() + 5.0, r.width() - 14.0, 18.0)
        p.setPen(QtGui.QColor("#e8e8e8"))
        p.drawText(cap, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, t("label_src"))
        p.drawText(cap, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, t("label_result"))


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
        p.setBrush(QtGui.QColor("#3a3a3a"))
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

        outer.addStretch(1)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        b_ok = QtWidgets.QPushButton(t("btn_ok"))
        b_ok.setObjectName("Accent")
        b_ok.setToolTip(t("tip_ok"))
        b_ok.clicked.connect(self.accept)
        row.addWidget(b_ok)
        outer.addLayout(row)


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
