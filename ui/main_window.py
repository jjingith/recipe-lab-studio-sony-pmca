"""Recipe Lab Studio main window.

Import a look (cube or portfolio), fit RL recipe parameters, compare the target against the recipe's
approximation on two preview plates, keep a PC master library, and sync the recipes to a mounted card.
"""
import json
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from core import card as CARD
from core import fit as FIT
from core import library as LIB
from core import ranges as R
from core import style as ST
from core.cube import load_safe
from core.model import Model, confidence
from core.recipe import Recipe
from .i18n import (AFDIAN_URL, APP_VERSION, AUTHOR, GITHUB_URL, LANG_LABEL, LANGUAGES,
                   get_language, load_config, save_config, set_language, t)
from .theme import COLORS, current_theme, qss, set_theme
from .widgets import (AboutDialog, BarReadout, DropButton, Histogram, IMAGE_EXTS, ImageView,
                      Module, ParamEditor, PortfolioDialog, ScoreStrip, SettingsDialog, SplitView,
                      ViewState)


class _WorkerSignals(QtCore.QObject):
    done = QtCore.Signal(object)
    error = QtCore.Signal(str)


class _Worker(QtCore.QRunnable):
    def __init__(self, fn, *a, **kw):
        super().__init__()
        self.fn, self.a, self.kw = fn, a, kw
        self.signals = _WorkerSignals()

    @QtCore.Slot()
    def run(self):
        try:
            self.signals.done.emit(self.fn(*self.a, **self.kw))
        except Exception as e:                       # noqa: BLE001 - surface to the UI
            self.signals.error.emit(str(e))


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resource(*parts):
    """a bundled file: from the source tree, or from PyInstaller's _internal folder"""
    base = getattr(sys, "_MEIPASS", ROOT)
    return os.path.join(base, *parts)


def _b64(data):
    """a QByteArray (the splitter state, the window geometry) as text for settings.json"""
    return bytes(data.toBase64()).decode("ascii")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("app_name"))
        self.resize(1400, 900)
        self.setStyleSheet(qss())

        self.library = LIB.Library().load()
        self.model = None
        self.card = None
        self.card_root = None
        self.builtins = json.load(open(_resource("data", "builtins.json"), encoding="utf-8"))

        self.target_lab = None
        self.target_cube = None
        self.target_thumb = None
        self.target_kind = None        # 'cube' | 'portfolio' | 'pair' — what the target came from
        self.target_pair_look = None   # the (after - before) Lab difference of a pair target
        self.base_lab = None           # the reference frame's own appearance, for the score bands
        self.src_image = None
        self.src_path = None           # the preview photo's path, for its EXIF metadata line
        self.result_image = None
        self.recipe = None
        self.portfolio_paths = []      # every photo imported as a colour target
        self.portfolio_selected = []   # the ticked subset a fit actually uses
        self.portfolio_dlg = None

        self.pool = QtCore.QThreadPool()
        self._workers = set()          # holds every running worker, see _run()
        self.view_state = ViewState()  # zoom/pan shared by the two preview plates
        self._build_ui()
        self._restore_workspace()
        self._refresh_tree()
        self._detect_card(quiet=True)
        self._start()

    # ================================================================ ui
    def _build_ui(self):
        self._build_menu()
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 8)
        root.setSpacing(11)
        root.addWidget(self._header())
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("MainSplit")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        left, center, right = self._left_panel(), self._center_panel(), self._right_panel()
        left.setMinimumWidth(240)
        center.setMinimumWidth(360)
        right.setMinimumWidth(300)
        self.splitter.addWidget(left)
        self.splitter.addWidget(center)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 6)
        self.splitter.setStretchFactor(2, 4)
        self.splitter.setSizes([330, 660, 440])
        root.addWidget(self.splitter, 1)
        self.setCentralWidget(central)

        bar = QtWidgets.QStatusBar()
        self.setStatusBar(bar)
        self.lbl_status = QtWidgets.QLabel(t("status_ready"))
        self.lbl_status.setObjectName("Screen")
        bar.addWidget(self.lbl_status, 1)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(150)
        self.progress.hide()
        bar.addPermanentWidget(self.progress)

    # ---------------------------------------------------------------- menu
    def _build_menu(self):
        bar = self.menuBar()

        m_lang = bar.addMenu(t("menu_language"))
        group = QtGui.QActionGroup(self)          # one checked at a time, like the CPU/GPU radio pair
        group.setExclusive(True)
        cur = get_language()
        for code in LANGUAGES:
            act = QtGui.QAction(LANG_LABEL[code], self)
            act.setCheckable(True)
            act.setChecked(code == cur)
            act.triggered.connect(lambda _=False, c=code: self._switch_language(c))
            group.addAction(act)
            m_lang.addAction(act)

        m_set = bar.addMenu(t("settings"))
        act_set = QtGui.QAction(t("settings_action"), self)
        act_set.triggered.connect(self._open_settings)
        m_set.addAction(act_set)

        m_about = bar.addMenu(t("menu_about"))
        act_about = QtGui.QAction(t("about_action"), self)
        act_about.triggered.connect(self._open_about)
        m_about.addAction(act_about)

        self.btn_theme = QtWidgets.QPushButton()
        self.btn_theme.setToolTip(t("tip_theme"))
        self.btn_theme.clicked.connect(self._toggle_theme)
        self._update_theme_btn()
        bar.setCornerWidget(self.btn_theme, QtCore.Qt.TopRightCorner)

    def _update_theme_btn(self):
        """the button names the mode it will switch *to*"""
        self.btn_theme.setText(t("theme_day") if current_theme() == "dark" else t("theme_night"))

    def _toggle_theme(self):
        nxt = "light" if current_theme() == "dark" else "dark"
        set_theme(nxt)
        save_config(theme=nxt)
        self.setStyleSheet(qss())
        self._update_theme_btn()
        self._refresh_tree()                    # the built-in rows carry an explicit muted colour
        self.view_state.notify()
        self._show_residual()
        self._refresh_hist()
        if self.portfolio_dlg is not None:
            self.portfolio_dlg.setStyleSheet(qss())

    def _switch_language(self, code):
        if code == get_language():
            return
        set_language(code)
        save_config(lang=code)
        QtWidgets.QMessageBox.information(self, t("restart_title"),
                                          t("restart_body", LANG_LABEL[code]))

    def _open_about(self):
        dlg = AboutDialog(self)
        dlg.setStyleSheet(qss())
        dlg.exec()

    # ---------------------------------------------------------------- header
    def _header(self):
        mod = Module(t("app_name"), t("tagline"))
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(14)

        b_cube = QtWidgets.QPushButton(t("btn_import_cube"))
        b_cube.setToolTip(t("tip_import_cube"))
        b_cube.clicked.connect(self._import_cube)
        row.addWidget(b_cube)

        self.btn_portfolio = DropButton(t("btn_portfolio"))
        self.btn_portfolio.setToolTip(t("tip_portfolio") + "\n" + t("tip_drop_portfolio"))
        self.btn_portfolio.clicked.connect(self._import_portfolio)
        self.btn_portfolio.dropped.connect(self._import_portfolio_paths)
        row.addWidget(self.btn_portfolio)

        b_pair = QtWidgets.QPushButton(t("btn_pair"))
        b_pair.setToolTip(t("tip_pair"))
        b_pair.clicked.connect(self._import_pair)
        row.addWidget(b_pair)

        self.btn_image = DropButton(t("btn_open_image"))
        self.btn_image.setToolTip(t("tip_open_image") + "\n" + t("tip_drop_preview"))
        self.btn_image.clicked.connect(self._load_image)
        self.btn_image.dropped.connect(self._load_image_paths)
        row.addWidget(self.btn_image)

        b_fit = QtWidgets.QPushButton(t("btn_fit"))
        b_fit.setObjectName("Accent")
        b_fit.setToolTip(t("tip_fit"))
        b_fit.clicked.connect(self._fit)
        row.addWidget(b_fit)

        b_det = QtWidgets.QPushButton(t("btn_detect"))
        b_det.setToolTip(t("tip_detect"))
        b_det.clicked.connect(lambda: self._detect_card())
        row.addWidget(b_det)

        row.addStretch(1)
        b_ws = QtWidgets.QPushButton(t("btn_save_ws"))
        b_ws.setToolTip(t("tip_save_ws"))
        b_ws.clicked.connect(self._save_workspace)
        row.addWidget(b_ws)
        mod.body.addLayout(row)
        return mod

    # ---------------------------------------------------------------- workspace
    def _save_workspace(self):
        save_config(workspace=_b64(self.splitter.saveState()),
                    geometry=_b64(self.saveGeometry()))
        self._status(t("ws_saved"))

    def _restore_workspace(self):
        cfg = load_config()
        geo = cfg.get("geometry")
        if geo:
            self.restoreGeometry(QtCore.QByteArray.fromBase64(geo.encode("ascii")))
        ws = cfg.get("workspace")
        if ws:
            self.splitter.restoreState(QtCore.QByteArray.fromBase64(ws.encode("ascii")))

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.setStyleSheet(qss())
        dlg.exec()

    # ---------------------------------------------------------------- left
    def _left_panel(self):
        mod = Module(t("mod_library"))
        self.mod_lib = mod

        head = QtWidgets.QHBoxLayout()
        self.lbl_card = QtWidgets.QLabel(t("card_none"))
        self.lbl_card.setObjectName("Muted")
        head.addWidget(self.lbl_card)
        head.addStretch(1)
        mod.body.addLayout(head)

        frow = QtWidgets.QHBoxLayout()
        self.ed_filter = QtWidgets.QLineEdit()
        self.ed_filter.setPlaceholderText(t("filter_ph"))
        self.ed_filter.setToolTip(t("tip_filter"))
        self.ed_filter.setClearButtonEnabled(True)
        self.ed_filter.textChanged.connect(self._refresh_tree)
        self.chk_fav = QtWidgets.QCheckBox(t("fav_only"))
        self.chk_fav.setToolTip(t("tip_fav_only"))
        self.chk_fav.toggled.connect(self._refresh_tree)
        frow.addWidget(self.ed_filter, 1)
        frow.addWidget(self.chk_fav)
        mod.body.addLayout(frow)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)
        self.tree.setToolTip(t("tip_tree"))
        self.tree.itemSelectionChanged.connect(self._on_tree_select)
        self.tree.itemDoubleClicked.connect(self._on_tree_double)
        mod.body.addWidget(self.tree, 1)

        row = QtWidgets.QHBoxLayout()
        for text, fn, danger, tip in [(t("btn_new"), self._new_recipe, False, t("tip_new")),
                                      (t("btn_dup"), self._duplicate, False, t("tip_dup")),
                                      (t("btn_del"), self._delete, True, t("tip_del"))]:
            b = QtWidgets.QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            if danger:
                b.setObjectName("Danger")
            row.addWidget(b)
        mod.body.addLayout(row)

        row3 = QtWidgets.QHBoxLayout()
        for text, fn, tip in [(t("btn_fav"), self._toggle_fav, t("tip_fav")),
                              (t("btn_tags"), self._edit_tags, t("tip_tags")),
                              (t("btn_dups"), self._find_duplicates, t("tip_dups")),
                              (t("btn_history"), self._show_history, t("tip_history"))]:
            b = QtWidgets.QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row3.addWidget(b)
        mod.body.addLayout(row3)

        row2 = QtWidgets.QHBoxLayout()
        b_push = QtWidgets.QPushButton(t("btn_push"))
        b_push.setObjectName("Launch")
        b_push.setToolTip(t("tip_push"))
        b_push.clicked.connect(self._push)
        b_pull = QtWidgets.QPushButton(t("btn_pull"))
        b_pull.setToolTip(t("tip_pull"))
        b_pull.clicked.connect(self._pull)
        b_rest = QtWidgets.QPushButton(t("btn_restore"))
        b_rest.setToolTip(t("tip_restore"))
        b_rest.clicked.connect(self._restore_card)
        self.chk_fit = QtWidgets.QCheckBox(t("chk_fit"))
        self.chk_fit.setToolTip(t("tip_chk_fit"))
        row2.addWidget(b_push)
        row2.addWidget(b_pull)
        row2.addWidget(b_rest)
        row2.addWidget(self.chk_fit)
        mod.body.addLayout(row2)
        return mod

    # ---------------------------------------------------------------- center
    def _center_panel(self):
        mod = Module(t("mod_preview"))
        self.mod_mon = mod

        self.btn_compare = QtWidgets.QPushButton(t("btn_compare"))
        self.btn_compare.setCheckable(True)
        self.btn_compare.setToolTip(t("tip_compare"))
        self.btn_compare.toggled.connect(self._toggle_compare)
        mod.add_head_widget(self.btn_compare)

        self.btn_orient = QtWidgets.QPushButton(t("btn_orient_h"))
        self.btn_orient.setToolTip(t("tip_orient"))
        self.btn_orient.clicked.connect(self._toggle_orient)
        self.btn_orient.hide()
        mod.add_head_widget(self.btn_orient)

        # -- the side-by-side plates
        pair = QtWidgets.QHBoxLayout()
        pair.setSpacing(11)
        left = QtWidgets.QVBoxLayout()
        lab_src = QtWidgets.QLabel(t("label_src"))
        lab_src.setObjectName("Stencil")
        left.addWidget(lab_src)
        self.view_src = ImageView(t("no_image"), self.view_state)
        self.view_src.setToolTip(t("tip_view") + "\n" + t("tip_drop_preview"))
        self.view_src.dropped.connect(self._load_image_paths)
        left.addWidget(self.view_src, 1)
        right = QtWidgets.QVBoxLayout()
        self.lbl_result = QtWidgets.QLabel(t("label_result"))
        self.lbl_result.setObjectName("Stencil")
        right.addWidget(self.lbl_result)
        self.view_out = ImageView(t("no_image"), self.view_state)
        self.view_out.setToolTip(t("tip_view") + "\n" + t("tip_drop_preview"))
        self.view_out.dropped.connect(self._load_image_paths)
        right.addWidget(self.view_out, 1)
        pair.addLayout(left, 1)
        pair.addLayout(right, 1)
        self.pair_widget = QtWidgets.QWidget()
        self.pair_widget.setLayout(pair)
        mod.body.addWidget(self.pair_widget, 1)

        # -- the wipe plate, shown instead of them when 对比视图 is on
        self.view_split = SplitView(self.view_state, t("no_image"))
        self.view_split.setToolTip(t("tip_split") + "\n" + t("tip_drop_preview"))
        self.view_split.dropped.connect(self._load_image_paths)
        self.view_split.hide()
        mod.body.addWidget(self.view_split, 1)

        meta = QtWidgets.QHBoxLayout()
        meta.setSpacing(11)
        self.lbl_residual = QtWidgets.QLabel(t("residual_none"))
        self.lbl_residual.setObjectName("Residual")
        meta.addWidget(self.lbl_residual)
        self.bar_residual = BarReadout()
        meta.addWidget(self.bar_residual, 1)
        self.lbl_target_name = QtWidgets.QLabel(t("target_none"))
        self.lbl_target_name.setObjectName("Muted")
        meta.addWidget(self.lbl_target_name)
        self.btn_view_ws = QtWidgets.QPushButton(t("btn_ws_view"))
        self.btn_view_ws.setToolTip(t("tip_ws_view"))
        self.btn_view_ws.clicked.connect(self._open_portfolio_view)
        self.btn_view_ws.hide()
        meta.addWidget(self.btn_view_ws)
        self.lbl_zoom = QtWidgets.QLabel("100%")
        self.lbl_zoom.setObjectName("Muted")
        self.lbl_zoom.setMinimumWidth(38)
        self.lbl_zoom.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        meta.addWidget(self.lbl_zoom)
        self.view_state.changed.connect(self._update_zoom)
        mod.body.addLayout(meta)

        self.score_strip = ScoreStrip()
        mod.body.addWidget(self.score_strip)

        crow = QtWidgets.QHBoxLayout()
        self.lbl_calib = QtWidgets.QLabel(t("calib_none"))
        self.lbl_calib.setObjectName("Muted")
        crow.addWidget(self.lbl_calib, 1)
        self.lbl_conf = QtWidgets.QLabel(t("conf_none"))
        self.lbl_conf.setObjectName("Muted")
        crow.addWidget(self.lbl_conf)
        mod.body.addLayout(crow)
        return mod

    def _update_zoom(self):
        self.lbl_zoom.setText("%d%%" % round(self.view_state.zoom * 100))

    def _toggle_compare(self, on):
        """swap the two plates for the single wipe plate (and back), then re-clamp the shared pan"""
        self.pair_widget.setVisible(not on)
        self.view_split.setVisible(on)
        self.btn_orient.setVisible(on)
        self.view_split.set_images(self.src_image, self.result_image)
        self.view_state.notify()

    def _toggle_orient(self):
        """flip the wipe divider between vertical and horizontal; the button names where it goes"""
        vertical = not self.view_split.vertical
        self.view_split.set_orientation(vertical)
        self.btn_orient.setText(t("btn_orient_h") if vertical else t("btn_orient_v"))

    # ---------------------------------------------------------------- right
    def _right_panel(self):
        mod = Module(t("mod_params"))
        self.mod_set = mod

        nrow = QtWidgets.QHBoxLayout()
        nm = QtWidgets.QLabel(t("name_label"))
        nm.setObjectName("Stencil")
        nrow.addWidget(nm)
        self.ed_name = QtWidgets.QLineEdit()
        self.ed_name.setMaxLength(R.NAME_MAX)
        self.ed_name.setPlaceholderText(t("name_ph", R.NAME_PUNCT))
        nrow.addWidget(self.ed_name, 1)
        mod.body.addLayout(nrow)

        self.editor = ParamEditor()
        self.editor.changed.connect(self._on_param_changed)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidget(self.editor)
        mod.body.addWidget(scroll, 1)

        self.lbl_summary = QtWidgets.QLabel("—")
        self.lbl_summary.setObjectName("Muted")
        self.lbl_summary.setWordWrap(True)
        mod.body.addWidget(self.lbl_summary)

        row = QtWidgets.QHBoxLayout()
        b_save = QtWidgets.QPushButton(t("btn_save"))
        b_save.setObjectName("Accent")
        b_save.setToolTip(t("tip_save"))
        b_save.clicked.connect(self._apply_to_library)
        b_reset = QtWidgets.QPushButton(t("btn_reset"))
        b_reset.setToolTip(t("tip_reset"))
        b_reset.clicked.connect(self._reset_editor)
        row.addWidget(b_save)
        row.addWidget(b_reset)
        mod.body.addLayout(row)

        self.hist = Histogram()
        self.hist.mode_changed.connect(self._on_hist_mode)
        self.hist.btn_shadow.toggled.connect(self._apply_clip)
        self.hist.btn_high.toggled.connect(self._apply_clip)
        mod.body.addWidget(self.hist)
        return mod

    # ================================================================ start
    def _start(self):
        self._status(t("start_status"))
        QtCore.QTimer.singleShot(200, self._ensure_model)
        QtCore.QTimer.singleShot(500, self._maybe_donate)

    def _maybe_donate(self):
        """the start-up reminder, unless the user has turned it off (settings or 「不再显示」)"""
        if not load_config().get("donate_popup", True):
            return
        box = QtWidgets.QDialog(self)
        box.setWindowTitle(t("donate_title"))
        box.setMinimumWidth(470)
        outer = QtWidgets.QVBoxLayout(box)
        outer.setContentsMargins(18, 16, 18, 14)
        outer.setSpacing(10)
        title = QtWidgets.QLabel(t("donate_title"))
        title.setObjectName("AppTitle")
        outer.addWidget(title)
        body = QtWidgets.QLabel(t("donate_body"))
        body.setObjectName("Muted")
        body.setWordWrap(True)
        outer.addWidget(body)
        chk = QtWidgets.QCheckBox(t("donate_chk_hide"))
        outer.addWidget(chk)
        row = QtWidgets.QHBoxLayout()
        b_open = QtWidgets.QPushButton(t("donate_btn_open"))
        b_open.setObjectName("Accent")
        b_open.setToolTip(AFDIAN_URL)
        b_open.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(AFDIAN_URL)))
        b_close = QtWidgets.QPushButton(t("donate_btn_close"))
        b_close.clicked.connect(box.accept)
        row.addWidget(b_open)
        row.addStretch(1)
        row.addWidget(b_close)
        outer.addLayout(row)
        box.setStyleSheet(qss())
        box.exec()
        if chk.isChecked():
            save_config(donate_popup=False)

    # ================================================================ workers
    def _run(self, fn, on_done, on_fail):
        """run fn on the pool and keep a python reference to the worker until it has finished.

        Qt owns the QRunnable while it executes, but the python wrapper is only referenced by a local
        variable; once that goes out of scope the wrapper (and its signal object) are collected while
        the thread is still running, and the next touch of that freed memory aborts the process with
        an access violation. So the set holds it until done/error has been delivered."""
        w = _Worker(fn)
        self._workers.add(w)
        w.signals.done.connect(on_done)
        w.signals.error.connect(on_fail)
        w.signals.done.connect(lambda *_: self._workers.discard(w))
        w.signals.error.connect(lambda *_: self._workers.discard(w))
        self.pool.start(w)
        return w

    # ================================================================ model
    def _ensure_model(self):
        if self.model is not None:
            return
        self._busy(True, t("model_busy"))
        self._run(lambda: Model.load(), self._model_ready,
                  lambda e: self._fail(t("model_fail_title"), e))

    def _model_ready(self, m):
        self.model = m
        self._busy(False)
        self._status(t("model_ready"))

    # ================================================================ tree
    def _refresh_tree(self, *_):
        q = self.ed_filter.text().strip().lower()
        fav_only = self.chk_fav.isChecked()
        self.tree.clear()
        groups = {i: None for i in range(len(R.GROUPS))}
        for i, g in enumerate(R.GROUPS):
            it = QtWidgets.QTreeWidgetItem([g])
            f = it.font(0)
            f.setBold(True)
            it.setFont(0, f)
            it.setData(0, QtCore.Qt.UserRole, ("group", i))
            self.tree.addTopLevelItem(it)
            groups[i] = it
        for idx, d in enumerate(self.builtins["recipes"]):
            summ = _builtin_summary(d)
            it = QtWidgets.QTreeWidgetItem([d["name"] + "   " + summ])
            it.setData(0, QtCore.Qt.UserRole, ("builtin", idx))
            it.setForeground(0, QtGui.QColor(COLORS["muted"]))
            it.setToolTip(0, t("builtin_tip", d["name"], summ))
            groups[d["group"]].addChild(it)
            it.setHidden(fav_only or bool(q) and q not in d["name"].lower())
        cust = QtWidgets.QTreeWidgetItem([t("custom_group", len(self.library.entries))])
        f = cust.font(0)
        f.setBold(True)
        cust.setFont(0, f)
        cust.setData(0, QtCore.Qt.UserRole, ("custgroup", None))
        self.tree.addTopLevelItem(cust)
        for r, file in self.library.entries:
            m = self.library.meta_for(file)
            tags = m.get("tags", [])
            label = "%s%s   %s" % ("★ " if m.get("fav") else "", r.name, r.summary())
            if tags:
                label += "   " + " ".join("#" + t for t in tags)
            it = QtWidgets.QTreeWidgetItem([label])
            it.setData(0, QtCore.Qt.UserRole, ("custom", file))
            it.setToolTip(0, "%s%s" % (r.name, ("\n" + t("tag_line", ", ".join(tags))) if tags else ""))
            match = (not fav_only or bool(m.get("fav"))) and (
                not q or q in r.name.lower() or any(q in t.lower() for t in tags))
            it.setHidden(not match)
            cust.addChild(it)
        cust.setExpanded(True)
        # while filtering, a group with nothing left to show disappears with its children
        filtering = bool(q) or fav_only
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            vis = any(not top.child(j).isHidden() for j in range(top.childCount()))
            top.setHidden(filtering and not vis)
        self.mod_lib.set_code(t("library_count", len(self.library.entries)))

    def _on_tree_select(self):
        items = self.tree.selectedItems()
        if not items:
            return
        kind, val = items[0].data(0, QtCore.Qt.UserRole)
        if kind == "builtin":
            self._set_editor(Recipe.from_dict({k: self.builtins["recipes"][val][k]
                                               for k in ("style", "sat", "con", "sharp", "wb_mode",
                                                         "kelvin", "ab", "gm", "pe", "ev", "dro", "sub")}),
                             name=self.builtins["recipes"][val]["name"])
        elif kind == "custom":
            r = self.library.find(val)
            if r:
                self._set_editor(r, file=val)

    def _on_tree_double(self, item, _col):
        kind, val = item.data(0, QtCore.Qt.UserRole)
        if kind == "builtin":
            self._duplicate()

    # ================================================================ editor
    def _set_editor(self, r, name=None, file=None):
        self.recipe = r
        self.current_file = file
        self.ed_name.setText(name if name is not None else r.name)
        self.editor.set_recipe(r)
        self.lbl_summary.setText(r.summary())
        self._render_preview()

    def _reset_editor(self):
        if self.recipe:
            self._set_editor(self.recipe, self.ed_name.text() or self.recipe.name,
                             getattr(self, "current_file", None))

    def _on_param_changed(self):
        if not self.recipe:
            return
        self.recipe = self.editor.recipe(name=self.ed_name.text())
        self.lbl_summary.setText(self.recipe.summary())
        self._render_recipe_preview()

    # ================================================================ import
    def _import_cube(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("dlg_cube"), "", t("flt_cube"))
        if not path:
            return
        cube, err = load_safe(path)
        if err:
            self._fail(t("cube_fail_title"), err)
            return
        self.target_cube = cube
        self.target_thumb = None
        self.target_kind = "cube"
        self.target_pair_look = None
        self.target_lab = ST.target_from_cube(cube)
        self._set_target_label(t("target_cube", os.path.basename(path), cube.size))
        self._render_preview()
        self._status(t("status_cube", os.path.basename(path)))
        if self.model and self.recipe:
            self._show_residual()

    def _import_portfolio(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, t("dlg_portfolio"), "", t("flt_img"))
        if files:
            self._import_portfolio_paths(files)

    def _import_portfolio_paths(self, paths):
        """a set of photos becomes the colour target; the browser opens so you can pick which count"""
        paths = [p for p in paths if p.lower().endswith(IMAGE_EXTS)]
        if not paths:
            self._status(t("drop_bad"))
            return
        lab, thumb = ST.target_from_portfolio(paths)
        if lab is None:
            self._fail(t("btn_portfolio"), t("portfolio_noimg"))
            return
        self.target_cube = None
        self.target_kind = "portfolio"
        self.target_pair_look = None
        self.target_lab = lab
        self.target_thumb = thumb
        self.portfolio_paths = list(paths)
        self.portfolio_selected = list(paths)
        self._set_target_label(t("target_portfolio", len(paths)))
        self._render_preview()
        self._status(t("status_portfolio", len(paths)))
        self._open_portfolio_view()

    def _open_portfolio_view(self):
        """show (or re-focus) the colour-target browser, in step with the current ticks"""
        if not self.portfolio_paths:
            return
        if self.portfolio_dlg is None:
            self.portfolio_dlg = PortfolioDialog(self.portfolio_paths, self)
            self.portfolio_dlg.setStyleSheet(qss())
            self.portfolio_dlg.selection_changed.connect(self._on_portfolio_selection)
        else:
            self.portfolio_dlg.sync(self.portfolio_selected)
        self.portfolio_dlg.show()
        self.portfolio_dlg.raise_()
        self.portfolio_dlg.activateWindow()

    def _on_portfolio_selection(self, paths):
        """re-take the signature from just the ticked photos — this is what a fit will aim at"""
        if not paths:
            return
        lab, thumb = ST.target_from_portfolio(paths)
        if lab is None:
            self._status(t("portfolio_noimg"))
            return
        self.portfolio_selected = list(paths)
        self.target_kind = "portfolio"
        self.target_lab = lab
        self.target_thumb = thumb
        self._set_target_label(t("target_portfolio", len(paths)))
        self._render_preview()

    def _import_pair(self):
        """estimate a look from a before/after pair: the same scene, graded — the difference is the
        look, which cancels whatever the scene itself looked like"""
        flt = t("flt_img")
        before, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("dlg_pair_before"), "", flt)
        if not before:
            return
        after, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("dlg_pair_after"), "", flt)
        if not after:
            return
        try:
            b = ST.load_rgb(before)
            a = ST.load_rgb(after)
        except Exception as e:                       # noqa: BLE001
            self._fail(t("pair_fail_title"), str(e))
            return
        lab, look, thumb = ST.target_from_pair(b, a)
        self.target_cube = None
        self.target_kind = "pair"
        self.target_lab = lab
        self.target_thumb = thumb
        self.target_pair_look = look
        self._set_target_label(t("target_pair", os.path.basename(before), os.path.basename(after)))
        self._render_preview()
        self._status(t("status_pair"))
        if self.model and self.recipe:
            self._show_residual()

    def _load_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("dlg_open_image"), "", t("flt_img_arw"))
        if path:
            self._load_image_paths([path])

    def _load_image_paths(self, paths):
        """a dropped (or picked) photo becomes the preview image; only image files are considered"""
        paths = [p for p in paths if p.lower().endswith(IMAGE_EXTS)]
        if not paths:
            self._status(t("drop_bad"))
            return
        path = paths[0]
        try:
            self.src_image = ST.load_rgb(path, 1600)
        except Exception as e:                       # noqa: BLE001
            self._fail(t("open_fail_title"), str(e))
            return
        self.src_path = path
        self.view_src.set_image(self.src_image)
        self.view_state.reset()
        self._render_preview()
        self._refresh_meta()

    # ================================================================ fit
    def _fit(self):
        if self.target_lab is None:
            self._fail(t("fit_title"), t("fit_need_target"))
            return
        if self.model is None:
            self._fail(t("fit_title"), t("fit_not_ready"))
            return
        allow_eff = self.chk_fit.isChecked()
        self._busy(True, t("fit_busy"))
        target = self.target_lab

        def done(res):
            params, resid = res
            self._busy(False)
            r = FIT.params_to_recipe(params, name=self._default_fit_name())
            self._set_editor(r)
            self._status(t("fit_done", resid))

        self._run(lambda: FIT.fit(self.model, target, allow_effects=allow_eff),
                  done, lambda e: self._fail(t("fit_fail_title"), e))

    def _default_fit_name(self):
        base = "Untitled"
        taken = self.library.taken_names()
        if base not in taken:
            return base
        for n in range(2, 100):
            if "%s %d" % (base, n) not in taken:
                return "%s %d" % (base, n)
        return base

    # ================================================================ preview
    def _set_target_label(self, text):
        self.lbl_target_name.setText(text)
        self.btn_view_ws.setVisible(self.target_kind == "portfolio" and bool(self.portfolio_paths))

    def _preview_image(self):
        """what the result plate shows: the photo on the bench whenever there is one — under the exact
        cube if one is loaded, else under the recipe's approximation, else unchanged; with no photo,
        the exact cube on the reference frame, else the portfolio thumbnail, else the recipe's blend"""
        if self.src_image is not None:
            if self.target_cube is not None:
                return self.target_cube.apply(self.src_image)
            if self.recipe is not None and self.model is not None:
                return ST.apply_look(self.model, self.recipe.values(), self.src_image)
            return self.src_image
        if self.target_cube is not None:
            return self.target_cube.apply(ST.reference_rgb())
        if self.target_thumb is not None:
            return self.target_thumb
        if self.recipe is not None and self.model is not None:
            return self.model.blend(self.recipe.values())
        return None

    def _update_out_label(self):
        if self.src_image is None:
            if self.target_cube is not None:
                txt = t("out_target_cube")
            elif self.target_kind == "pair":
                txt = t("out_pair")
            elif self.target_thumb is not None:
                txt = t("out_portfolio")
            else:
                txt = t("out_recipe")
        elif self.target_cube is not None:
            txt = t("out_cube_src")
        elif self.recipe is not None and self.model is not None:
            txt = t("out_recipe_src")
        else:
            txt = t("out_src")
        self.lbl_result.setText(txt)

    def _render_preview(self):
        out = self._preview_image()
        self.result_image = out
        self.view_out.set_image(out)
        self.view_split.set_images(self.src_image, out)
        self._update_out_label()
        self._show_residual()
        self._refresh_hist()

    def _render_recipe_preview(self):
        if self.recipe is None:
            return
        out = self._preview_image()
        if out is not None:
            self.result_image = out
            self.view_out.set_image(out)
            self.view_split.set_images(self.src_image, out)
            self._update_out_label()
        self._show_residual()
        self._refresh_hist()

    # ---------------------------------------------------------------- histogram
    def _on_hist_mode(self, _mode):
        self._refresh_hist()

    def _refresh_hist(self):
        """feed the plot: the original photo, or the graded result, whichever the switch asks for"""
        after = self.hist.after_mode
        if after and self.result_image is not None:
            rgb = self.result_image
        else:
            rgb = self.src_image
        self.hist.set_rgb(rgb)

    def _refresh_meta(self):
        """the preview photo's ISO / shutter / aperture / focal, straight from its EXIF"""
        if not self.src_path:
            self.hist.set_meta(t("meta_none"))
            return
        info = ST.exif_summary(self.src_path)
        vals = [info["iso"], info["shutter"], info["aperture"], info["focal"]]
        if not any(vals):
            self.hist.set_meta(t("meta_none"))
            return
        keys = ("meta_iso", "meta_shutter", "meta_aperture", "meta_focal")
        self.hist.set_meta(" · ".join(t(k, v if v else "—") for k, v in zip(keys, vals)))

    def _apply_clip(self, *_):
        shadow = self.hist.btn_shadow.isChecked()
        high = self.hist.btn_high.isChecked()
        for v in (self.view_src, self.view_out, self.view_split):
            v.set_clip_flags(shadow, high)

    def _show_residual(self):
        if self.target_lab is None or self.recipe is None or self.model is None:
            self.lbl_residual.setText(t("residual_none"))
            self.bar_residual.set_value(0.0)
            self.score_strip.clear()
            self.lbl_calib.setText(t("calib_none"))
            self.lbl_conf.setText(t("conf_none"))
            return
        vals = self.recipe.values()
        res = self.model.lab_residual(vals, self.target_lab)
        tol = 2.0
        col = COLORS["good"] if res <= tol else COLORS["warn"] if res <= 5 else COLORS["bad"]
        self.lbl_residual.setText(t("residual_fmt", col, res, tol))
        self.bar_residual.set_value(max(0.0, 1.0 - res / 10.0), col)
        if self.base_lab is None:                    # the reference frame's own appearance, once
            self.base_lab = ST.base_signature()
        self.score_strip.set_scores(self.model.breakdown(vals, self.target_lab, self.base_lab))
        c, _ = confidence(res)
        word = t("conf_high") if c >= 0.75 else t("conf_mid") if c >= 0.45 else t("conf_low")
        self.lbl_conf.setText(t("conf_fmt", word, round(c * 100)))
        self.lbl_calib.setText(t("calib_init"))

    # ================================================================ library ops
    def _new_recipe(self):
        r = Recipe(name=self._default_fit_name(), style=1, wb_mode=R.WB_AUTO, dro=R.DRO_AUTO)
        self._set_editor(r)

    def _duplicate(self):
        items = self.tree.selectedItems()
        if not items:
            return
        kind, val = items[0].data(0, QtCore.Qt.UserRole)
        if kind == "builtin":
            d = self.builtins["recipes"][val]
            r = Recipe.from_dict({k: d[k] for k in ("style", "sat", "con", "sharp", "wb_mode",
                                                    "kelvin", "ab", "gm", "pe", "ev", "dro", "sub")})
            r.name = (d["name"].replace("/", "-")[:20]).strip()
            r.group = R.CUSTOM
            self._set_editor(r)
            self._status(t("dup_builtin", d["name"]))
        elif kind == "custom":
            r = self.library.find(val)
            if r:
                import copy
                r2 = copy.deepcopy(r)
                base = r.name[:20]
                taken = self.library.taken_names()
                new = base + " 2"
                n = 2
                while new in taken:
                    n += 1
                    new = "%s %d" % (base, n)
                r2.name = new[:24]
                self._set_editor(r2)

    def _apply_to_library(self):
        if not self.recipe:
            self._fail(t("save_title"), t("save_no_recipe"))
            return
        r = self.editor.recipe(name=self.ed_name.text())
        self.recipe = r
        try:
            existing = getattr(self, "current_file", None)
            if existing and self.library.find(existing):
                self.current_file = self.library.update(r, existing, {"source": "edit"})
                self._status(t("saved_update", r.name))
            else:
                self.current_file = self.library.add(r, {"source": "new"})
                self._status(t("saved_add", r.name))
        except ValueError as e:
            self._fail(t("save_fail_title"), str(e))
            return
        self._refresh_tree()
        self._select_custom(self.current_file)

    def _delete(self):
        f = getattr(self, "current_file", None)
        if not f or not self.library.find(f):
            self._fail(t("del_title"), t("del_need_select"))
            return
        if QtWidgets.QMessageBox.question(self, t("del_title"),
                                          t("del_confirm", self.library.find(f).name)
                                          ) != QtWidgets.QMessageBox.Yes:
            return
        self.library.remove(f)
        self.current_file = None
        self._refresh_tree()
        self._status(t("del_done"))

    def _select_custom(self, file):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.data(0, QtCore.Qt.UserRole)[0] == "custgroup":
                for j in range(top.childCount()):
                    ch = top.child(j)
                    if ch.data(0, QtCore.Qt.UserRole)[1] == file:
                        self.tree.setCurrentItem(ch)
                        return

    # ================================================================ tags / favourites / history
    def _current_custom_file(self):
        items = self.tree.selectedItems()
        if not items:
            return None
        kind, val = items[0].data(0, QtCore.Qt.UserRole)
        return val if kind == "custom" else None

    def _toggle_fav(self):
        f = self._current_custom_file()
        if not f:
            self._fail(t("fav_title"), t("del_need_select"))
            return
        on = self.library.toggle_fav(f)
        self._refresh_tree()
        self._select_custom(f)
        self._status(t("fav_added" if on else "fav_removed", self.library.find(f).name))

    def _edit_tags(self):
        f = self._current_custom_file()
        if not f:
            self._fail(t("tags_title"), t("del_need_select"))
            return
        cur = ", ".join(self.library.tags_of(f))
        text, ok = QtWidgets.QInputDialog.getText(self, t("tags_title"), t("tags_prompt"), text=cur)
        if not ok:
            return
        self.library.set_tags(f, text.replace("，", ",").split(","))
        self._refresh_tree()
        self._select_custom(f)
        self._status(t("tags_done"))

    def _find_duplicates(self):
        groups = self.library.duplicates()
        if not groups:
            QtWidgets.QMessageBox.information(self, t("dups_title"), t("dups_none"))
            return
        lines = ["、".join("『%s』" % r.name for r, _ in g) for g in groups]
        msg = t("dups_confirm", len(groups), "\n".join(lines))
        if QtWidgets.QMessageBox.question(self, t("dups_title"), msg) != QtWidgets.QMessageBox.Yes:
            return
        removed = 0
        for g in groups:
            for _, f in g[1:]:
                self.library.remove(f)
                removed += 1
        self.current_file = None
        self._refresh_tree()
        self._status(t("dups_done", removed))

    def _show_history(self):
        f = self._current_custom_file()
        if not f:
            self._fail(t("history_title"), t("del_need_select"))
            return
        snaps = self.library.history(f)
        name = self.library.find(f).name
        if not snaps:
            QtWidgets.QMessageBox.information(self, t("history_dlg"), t("history_none", name))
            return
        items = ["v%d  （%s）" % (n, os.path.basename(p)) for n, p in snaps]
        pick, ok = QtWidgets.QInputDialog.getItem(
            self, t("history_dlg"), t("history_prompt", name, len(snaps)),
            items, len(items) - 1, False)
        if not ok:
            return
        idx = items.index(pick)
        self.library.restore(f, snaps[idx][1])
        self._refresh_tree()
        self._select_custom(f)
        self._on_tree_select()
        self._status(t("history_done", snaps[idx][0]))

    # ================================================================ card
    def _detect_card(self, quiet=False):
        found = CARD.detect()
        if not found:
            self.card = None
            self.lbl_card.setText(t("card_none"))
            if not quiet:
                self._status(t("card_none_status"))
            return
        root = found[0][0]
        self.card_root = root
        self.card = CARD.Card(root)
        entries, skipped = self.card.load()
        self.lbl_card.setText(t("card_found", root, len(entries)))
        if not quiet:
            msg = t("card_connected", root)
            if skipped:
                msg += t("card_skipped", len(skipped))
            self._status(msg)

    def _push(self):
        """push the library onto the card: check it is writable, show what will be replaced, back
        each replaced file up, then read every written file back"""
        if self.card is None:
            self._detect_card()
            if self.card is None:
                return
        if not self.library.entries:
            self._fail(t("push_title"), t("push_no_recipes"))
            return
        ok, why = self.card.writable()
        if not ok:
            self._fail(t("push_title"), t("push_not_writable", why))
            return
        rows = self.card.plan(self.library.entries)
        new = [r for r in rows if r["status"] == "new"]
        over = [r for r in rows if r["status"] == "overwrite"]
        same = [r for r in rows if r["status"] == "same"]
        need = sum(r["bytes"] for r in new + over)
        free = self.card.free_bytes()
        bakdir = os.path.join(self.card.root, R.DIR, CARD.BACKUP_DIR)
        msg = t("push_plan", len(rows), self.card_root, R.DIR, len(new), len(over), bakdir, len(same))
        if over:
            shown = "\n".join(t("push_over_row", r["recipe"].name, r["card_recipe"].summary())
                              for r in over[:8])
            msg += t("push_over_head") + shown
            if len(over) > 8:
                msg += t("push_over_more", len(over) - 8)
        if not new and not over:
            QtWidgets.QMessageBox.information(self, t("push_title"), t("push_nothing"))
            return
        if free is not None and need > free:
            msg += t("push_space_warn", need / 1024.0, free / 1024.0)
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle(t("push_dlg_title"))
        box.setIcon(QtWidgets.QMessageBox.Warning if over else QtWidgets.QMessageBox.Question)
        box.setText(msg)
        box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if box.exec() != QtWidgets.QMessageBox.Yes:
            return
        written, errors = self.card.push_all(rows)
        self._detect_card(quiet=True)
        if errors:
            self._fail(t("push_err_title"),
                       t("push_err_body", len(written),
                         "\n".join("· " + e for e in errors), bakdir, self.card_root, R.DIR))
            self._status(t("push_partial", len(written), len(errors)))
            return
        tail = t("push_tail_backup", bakdir) if over else t("push_tail_none")
        QtWidgets.QMessageBox.information(
            self, t("push_done_title"),
            t("push_done_body", len(written), self.card_root, R.DIR, tail))
        self._status(t("push_done_status", len(written), self.card_root))

    def _pull(self):
        if self.card is None:
            self._detect_card()
            if self.card is None:
                return
        entries, _ = self.card.load()
        if not entries:
            self._status(t("pull_none"))
            return
        added, errors = self.card.pull_all(self.library)
        self._refresh_tree()
        self._status(t("pull_done", len(added),
                       (t("err_prefix") + ": " + "; ".join(errors)) if errors else ""))

    def _restore_card(self):
        """put a backup from RECIPES/_backup back onto the card — the undo for a bad push"""
        if self.card is None:
            self._detect_card()
            if self.card is None:
                return
        backups = self.card.backups()
        if not backups:
            QtWidgets.QMessageBox.information(self, t("restore_title"),
                                              t("restore_none", CARD.BACKUP_DIR))
            return
        items = ["%s   ← %s" % (f, os.path.basename(p)) for f, p in backups]
        pick, ok = QtWidgets.QInputDialog.getItem(self, t("restore_title"),
                                                 t("restore_prompt"), items, 0, False)
        if not ok:
            return
        f = backups[items.index(pick)][0]
        self.card.restore_backup(f)
        self._detect_card(quiet=True)
        self._status(t("restore_done", f))

    # ================================================================ helpers
    def _status(self, text):
        self.lbl_status.setText(text)

    def _busy(self, on, text=""):
        self.progress.setVisible(on)
        if on and text:
            self._status(text)

    def _fail(self, title, text):
        self._busy(False)
        QtWidgets.QMessageBox.warning(self, title, text)
        self._status("%s: %s" % (title, text))


def _builtin_summary(d):
    """a short summary for a builtin recipe row"""
    s = []
    if d["pe"] != 0:
        s.append(R.PE_LABEL[d["pe"]])
    else:
        s.append(R.STYLE_LABEL[d["style"]])
        s.append("%+d/%+d" % (d["sat"], d["con"]))
    if d["ev"]:
        s.append(R.ev_label(d["ev"]))
    if d["wb_mode"] == R.WB_KELVIN:
        s.append("%dK" % d["kelvin"])
    return " ".join(s)
