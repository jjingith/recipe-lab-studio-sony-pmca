"""Two Adobe-style themes — a dark one (default) and a light one — built from one palette dict.

Modelled on Adobe's UI (Lightroom / Photoshop): flat panels, 1px hairlines, small radii, no glow,
no scanlines, no gradients, no bevels, and Spectrum blue #1473e6 as the only accent in both themes.

COLORS is a single mutable dict. The widgets import it by reference, so a theme switch mutates it in
place and every paintEvent picks the new colours up without any widget being rebuilt; qss() reads the
same dict, so re-applying the stylesheet is all a switch takes (see set_theme / current_theme).
"""

DARK = {
    "bg":        "#1e1e1e",   # application canvas
    "panel":     "#262626",   # module background
    "panel_hi":  "#333333",   # hover / raised-inside-panel
    "raised":    "#3c3c3c",   # button face
    "line":      "#383838",   # hairline separators and panel edges
    "edge":      "#565656",   # control outlines
    "text":      "#d8d8d8",
    "muted":     "#9a9a9a",
    "accent":    "#1473e6",   # Spectrum blue
    "accent_hi": "#2680eb",
    "accent_lo": "#0d66d0",
    "good":      "#2d9d78",   # residual within tolerance
    "warn":      "#e6a23c",
    "bad":       "#e34850",
    "canvas":    "#101010",   # the image plate
    "title":     "#e8e8e8",   # app title
    "title2":    "#bcbcbc",   # module title
    "btn_hover": "#484848",
    "btn_press": "#2f2f2f",
    "disabled_text": "#6a6a6a",
    "on_accent": "#ffffff",   # text on an accent-filled control
    "input_hover_edge": "#6e6e6e",
    "slider_groove": "#4b4b4b",
    "slider_handle": "#e6e6e6",
    "slider_handle_edge": "#8a8a8a",
    "scroll_handle": "#5a5a5a",
    "scroll_handle_hi": "#7a7a7a",
    "bar_groove": "#3a3a3a",  # BarReadout empty groove
    "danger_edge": "#a01808",
    "danger_text": "#ff8a80",
    "tooltip_bg": "#2b2b2b",
    "cap_text":  "#e8e8e8",   # the before/after cap, drawn over the image so it stays light
}

LIGHT = {
    "bg":        "#f0f0f0",
    "panel":     "#fafafa",
    "panel_hi":  "#eaeaea",
    "raised":    "#ffffff",
    "line":      "#dcdcdc",
    "edge":      "#c2c2c2",
    "text":      "#2e2e2e",
    "muted":     "#707070",
    "accent":    "#1473e6",
    "accent_hi": "#2680eb",
    "accent_lo": "#0d66d0",
    "good":      "#2d9d78",
    "warn":      "#c07d18",
    "bad":       "#d13b43",
    "canvas":    "#d9d9d9",
    "title":     "#262626",
    "title2":    "#555555",
    "btn_hover": "#eeeeee",
    "btn_press": "#e0e0e0",
    "disabled_text": "#9a9a9a",
    "on_accent": "#ffffff",
    "input_hover_edge": "#8a8a8a",
    "slider_groove": "#cfcfcf",
    "slider_handle": "#ffffff",
    "slider_handle_edge": "#b0b0b0",
    "scroll_handle": "#c0c0c0",
    "scroll_handle_hi": "#a6a6a6",
    "bar_groove": "#dcdcdc",
    "danger_edge": "#c0392b",
    "danger_text": "#e34850",
    "tooltip_bg": "#ffffff",
    "cap_text":  "#e8e8e8",
}

COLORS = dict(DARK)
_current = "dark"


def set_theme(name):
    """switch the palette by mutating COLORS in place, so every widget holding a reference sees it.

    `name` is 'dark' or 'light'; anything else falls back to dark."""
    global _current
    _current = name if name in ("dark", "light") else "dark"
    COLORS.clear()
    COLORS.update(LIGHT if _current == "light" else DARK)


def current_theme():
    return _current


UI_FONT = '"Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'


def qss():
    c = COLORS
    return f"""
* {{ font-family: {UI_FONT}; font-size: 12px; }}
QWidget {{ background: {c['bg']}; color: {c['text']}; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}

/* ---------------- labels ---------------- */
QLabel#AppTitle {{ font-size: 15px; color: {c['title']}; }}
QLabel#ModTitle {{ font-size: 12px; color: {c['title2']}; }}
QLabel#ModNum {{ font-size: 11px; color: {c['muted']}; }}
QLabel#Stencil {{ font-size: 11px; color: {c['muted']}; }}
QLabel#Muted {{ font-size: 11px; color: {c['muted']}; }}
QLabel#Residual {{ font-size: 12px; }}
QLabel#Screen {{ font-size: 12px; color: {c['text']}; }}

/* ---------------- panels ---------------- */
QFrame#Module {{
    background: {c['panel']};
    border: 1px solid {c['line']};
    border-radius: 3px;
}}
QFrame#PanelRule {{ background: {c['line']}; border: none; }}

/* ---------------- buttons ---------------- */
QPushButton {{
    background: {c['raised']};
    border: 1px solid {c['edge']};
    border-radius: 4px;
    padding: 5px 12px;
    color: {c['text']};
}}
QPushButton:hover {{ background: {c['btn_hover']}; }}
QPushButton:pressed {{ background: {c['btn_press']}; }}
QPushButton:disabled {{ background: {c['panel']}; color: {c['disabled_text']}; border-color: {c['line']}; }}
QPushButton:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
    color: {c['on_accent']};
}}
QPushButton:checked:hover {{ background: {c['accent_hi']}; border-color: {c['accent_hi']}; }}
QPushButton[dropHot="true"] {{ border-color: {c['accent']}; }}
QPushButton#Accent, QPushButton#Launch {{
    background: {c['accent']};
    border: 1px solid {c['accent']};
    color: {c['on_accent']};
}}
QPushButton#Accent:hover, QPushButton#Launch:hover {{
    background: {c['accent_hi']};
    border-color: {c['accent_hi']};
}}
QPushButton#Accent:pressed, QPushButton#Launch:pressed {{
    background: {c['accent_lo']};
    border-color: {c['accent_lo']};
}}
QPushButton#Danger:hover {{ border-color: {c['danger_edge']}; color: {c['danger_text']}; }}
QToolButton {{
    background: {c['raised']};
    border: 1px solid {c['edge']};
    border-radius: 4px;
    padding: 3px 8px;
    color: {c['text']};
}}
QToolButton:hover {{ background: {c['btn_hover']}; }}
QToolButton:pressed {{ background: {c['btn_press']}; }}
QToolButton:checked {{ background: {c['accent']}; border-color: {c['accent']}; color: {c['on_accent']}; }}
QToolButton#ThemeToggle {{
    background: transparent;
    border: none;
    border-radius: 3px;
    padding: 2px;
}}
QToolButton#ThemeToggle:hover {{ background: {c['panel_hi']}; }}

/* ---------------- inputs ---------------- */
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background: {c['bg']};
    border: 1px solid {c['edge']};
    border-radius: 4px;
    padding: 4px 7px;
    min-height: 18px;
    color: {c['text']};
    selection-background-color: {c['accent']};
    selection-color: {c['on_accent']};
}}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{ border-color: {c['input_hover_edge']}; }}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{ border-color: {c['accent']}; }}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{ color: {c['disabled_text']}; border-color: {c['line']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {c['panel']};
    border: 1px solid {c['edge']};
    selection-background-color: {c['accent']};
    selection-color: {c['on_accent']};
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 15px; border: none; background: transparent; }}

/* ---------------- sliders ---------------- */
QSlider::groove:horizontal {{ height: 3px; background: {c['slider_groove']}; border-radius: 1px; }}
QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 1px; }}
QSlider::handle:horizontal {{
    background: {c['slider_handle']};
    width: 12px; margin: -5px 0;
    border: 1px solid {c['slider_handle_edge']};
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{ background: {c['on_accent']}; border-color: {c['accent']}; }}

/* ---------------- check boxes ---------------- */
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 13px; height: 13px;
    background: {c['bg']};
    border: 1px solid {c['edge']};
    border-radius: 2px;
}}
QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; }}
QCheckBox::indicator:hover {{ border-color: {c['accent_hi']}; }}

/* ---------------- radio buttons ---------------- */
QRadioButton {{ spacing: 6px; }}
QRadioButton::indicator {{
    width: 13px; height: 13px;
    background: {c['bg']};
    border: 1px solid {c['edge']};
    border-radius: 7px;
}}
QRadioButton::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; }}
QRadioButton::indicator:hover {{ border-color: {c['accent_hi']}; }}
QRadioButton::indicator:disabled {{ background: {c['panel']}; border-color: {c['line']}; }}
QRadioButton:disabled {{ color: {c['disabled_text']}; }}

/* ---------------- menu bar / menus ---------------- */
QMenuBar {{ background: {c['panel']}; color: {c['text']}; border-bottom: 1px solid {c['line']}; }}
QMenuBar::item {{ background: transparent; padding: 4px 10px; border-radius: 3px; }}
QMenuBar::item:selected {{ background: {c['panel_hi']}; }}
QMenuBar::item:pressed {{ background: {c['accent']}; color: {c['on_accent']}; }}
QMenu {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['edge']}; padding: 4px; }}
QMenu::item {{ padding: 5px 24px; border-radius: 3px; }}
QMenu::item:selected {{ background: {c['accent']}; color: {c['on_accent']}; }}
QMenu::item:disabled {{ color: {c['disabled_text']}; }}
QMenu::separator {{ height: 1px; background: {c['line']}; margin: 4px 6px; }}
QMenu::indicator {{ width: 14px; height: 14px; }}

/* ---------------- library list ---------------- */
QTreeWidget, QListWidget {{
    background: {c['bg']};
    border: 1px solid {c['line']};
    border-radius: 3px;
    outline: none;
    padding: 2px;
    color: {c['text']};
}}
QTreeWidget::item, QListWidget::item {{ height: 21px; padding: 0 4px; border-radius: 2px; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {c['panel_hi']}; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {c['accent']}; color: {c['on_accent']}; }}
QHeaderView::section {{ background: {c['panel']}; border: none; color: {c['muted']}; padding: 4px; }}

/* ---------------- splitter ---------------- */
QSplitter::handle {{ background: {c['bg']}; }}
QSplitter::handle:hover {{ background: {c['edge']}; }}

/* ---------------- misc ---------------- */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c['scroll_handle']}; min-height: 26px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {c['scroll_handle_hi']}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {c['scroll_handle']}; min-width: 26px; border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['scroll_handle_hi']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QStatusBar {{ background: {c['panel']}; color: {c['muted']}; border-top: 1px solid {c['line']}; }}
QStatusBar::item {{ border: none; }}
QProgressBar {{
    background: {c['bg']};
    border: 1px solid {c['line']};
    border-radius: 3px;
    text-align: center;
    color: {c['muted']};
}}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}

QToolTip {{
    background: {c['tooltip_bg']}; color: {c['text']};
    border: 1px solid {c['edge']}; padding: 4px 8px;
}}
"""
