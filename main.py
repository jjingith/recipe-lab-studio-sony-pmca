"""Recipe Lab Studio — entry point.

A desktop tool for the Recipe Lab camera app: import a look (.cube or a photographer's portfolio),
fit RL recipe parameters to it, preview the target against the recipe's approximation, keep a PC
master library, and push/pull the recipes to a mounted camera card.

Run:  python main.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _icon():
    """the bundled launcher icon: from the source tree, or from PyInstaller's _MEIPASS folder"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "data", "icon.png")


def _taskbar_identity():
    """Give the process its own Windows task-bar identity (AppUserModelID). Without one the shell
    falls back to the host interpreter's identity, so a window started through python.exe keeps
    showing python's own icon in the task bar; an explicit id makes the shell use this app's."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jjingith.RecipeLabStudio")
    except Exception:
        pass


def main():
    from PySide6 import QtCore, QtGui, QtWidgets
    from ui.i18n import init_language, load_config
    from ui.main_window import MainWindow
    from ui.theme import set_theme

    _taskbar_identity()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Recipe Lab Studio")
    if os.path.exists(_icon()):
        app.setWindowIcon(QtGui.QIcon(_icon()))
    # Qt formats spin-box numbers with the system locale's native digits; on a zh_CN Windows that
    # yields CJK numerals (〇, 〡, 〥 …) instead of 0-9. Pin number formatting to ASCII digits.
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
    # the UI language: the saved choice, else the system's own (uses QLocale.system(), which the
    # setDefault above does not affect)
    init_language()
    # the saved theme (the light/dark switch in the menu bar writes it); dark is the default
    set_theme(load_config().get("theme", "dark"))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
