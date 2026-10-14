"""Adobe-style dark theme: neutral greys, one blue accent, flat surfaces.

Modelled on Adobe's dark UI (Lightroom / Photoshop): an #1e1e1e canvas, #262626 panels, #3c3c3c
raised buttons, #d8d8d8 text and Spectrum blue #1473e6 as the only accent. Flat panels, 1px
hairlines, small radii — no glow, no scanlines, no gradients, no bevels.
"""

COLORS = {
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
}

UI_FONT = '"Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'


def qss():
    c = COLORS
    return f"""
* {{ font-family: {UI_FONT}; font-size: 12px; }}
QWidget {{ background: {c['bg']}; color: {c['text']}; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}

/* ---------------- labels ---------------- */
QLabel#AppTitle {{ font-size: 15px; color: #e8e8e8; }}
QLabel#ModTitle {{ font-size: 12px; color: #bcbcbc; }}
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
QPushButton:hover {{ background: #484848; }}
QPushButton:pressed {{ background: #2f2f2f; }}
QPushButton:disabled {{ background: {c['panel']}; color: #6a6a6a; border-color: {c['line']}; }}
QPushButton:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
    color: #ffffff;
}}
QPushButton:checked:hover {{ background: {c['accent_hi']}; border-color: {c['accent_hi']}; }}
QPushButton#Accent, QPushButton#Launch {{
    background: {c['accent']};
    border: 1px solid {c['accent']};
    color: #ffffff;
}}
QPushButton#Accent:hover, QPushButton#Launch:hover {{
    background: {c['accent_hi']};
    border-color: {c['accent_hi']};
}}
QPushButton#Accent:pressed, QPushButton#Launch:pressed {{
    background: {c['accent_lo']};
    border-color: {c['accent_lo']};
}}
QPushButton#Danger:hover {{ border-color: #a01808; color: #ff8a80; }}

/* ---------------- inputs ---------------- */
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background: {c['bg']};
    border: 1px solid {c['edge']};
    border-radius: 4px;
    padding: 4px 7px;
    min-height: 18px;
    color: {c['text']};
    selection-background-color: {c['accent']};
    selection-color: #ffffff;
}}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{ border-color: #6e6e6e; }}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{ border-color: {c['accent']}; }}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{ color: #6a6a6a; border-color: {c['line']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {c['panel']};
    border: 1px solid {c['edge']};
    selection-background-color: {c['accent']};
    selection-color: #ffffff;
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 15px; border: none; background: transparent; }}

/* ---------------- sliders ---------------- */
QSlider::groove:horizontal {{ height: 3px; background: #4b4b4b; border-radius: 1px; }}
QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 1px; }}
QSlider::handle:horizontal {{
    background: #e6e6e6;
    width: 12px; margin: -5px 0;
    border: 1px solid #8a8a8a;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{ background: #ffffff; border-color: {c['accent']}; }}

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
QRadioButton:disabled {{ color: #6a6a6a; }}

/* ---------------- menu bar / menus ---------------- */
QMenuBar {{ background: {c['panel']}; color: {c['text']}; border-bottom: 1px solid {c['line']}; }}
QMenuBar::item {{ background: transparent; padding: 4px 10px; border-radius: 3px; }}
QMenuBar::item:selected {{ background: {c['panel_hi']}; }}
QMenuBar::item:pressed {{ background: {c['accent']}; color: #ffffff; }}
QMenu {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['edge']}; padding: 4px; }}
QMenu::item {{ padding: 5px 24px; border-radius: 3px; }}
QMenu::item:selected {{ background: {c['accent']}; color: #ffffff; }}
QMenu::item:disabled {{ color: #6a6a6a; }}
QMenu::separator {{ height: 1px; background: {c['line']}; margin: 4px 6px; }}
QMenu::indicator {{ width: 14px; height: 14px; }}

/* ---------------- library list ---------------- */
QTreeWidget {{
    background: {c['bg']};
    border: 1px solid {c['line']};
    border-radius: 3px;
    outline: none;
    padding: 2px;
    color: {c['text']};
}}
QTreeWidget::item {{ height: 21px; padding: 0 4px; border-radius: 2px; }}
QTreeWidget::item:hover {{ background: {c['panel_hi']}; }}
QTreeWidget::item:selected {{ background: {c['accent']}; color: #ffffff; }}
QHeaderView::section {{ background: {c['panel']}; border: none; color: {c['muted']}; padding: 4px; }}

/* ---------------- misc ---------------- */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #5a5a5a; min-height: 26px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: #7a7a7a; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #5a5a5a; min-width: 26px; border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: #7a7a7a; }}
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
    background: #2b2b2b; color: {c['text']};
    border: 1px solid {c['edge']}; padding: 4px 8px;
}}
"""
