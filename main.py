import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import QCoreApplication, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap


def _register_file_association():
    if sys.platform != 'win32':
        return
    try:
        import winreg, os
        exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        # En modo dev el ejecutable es python.exe y no tiene el ícono incrustado.
        # Se usa el .ico directamente cuando no está frozen.
        if getattr(sys, 'frozen', False):
            icon_ref = f'"{exe}",0'
        else:
            _ico = Path(__file__).parent / 'assets' / 'icon.ico'
            icon_ref = f'"{_ico.resolve()}"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\TSA.Project') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, 'TSA Project File')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\TSA.Project\DefaultIcon') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, icon_ref)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\TSA.Project\shell\open\command') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, f'"{exe}" "%1"')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.TSA') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, 'TSA.Project')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.tsa') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, 'TSA.Project')
        # .tsax — perfiles compuestos exportados desde SectionBuilder para importar en TSA.
        # NO .tsx — choca con la extensión estándar de TypeScript/React.
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\TSA.Profile') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, 'TSA Profile File')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\TSA.Profile\DefaultIcon') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, icon_ref)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\TSA.Profile\shell\open\command') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, f'"{exe}" "%1"')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.tsax') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, 'TSA.Profile')
        # Limpieza: quitar la asociación .tsx que se había registrado antes de este
        # cambio — no debe quedar pisando la extensión estándar de TypeScript/React.
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.tsx')
        except OSError:
            pass
        try:
            from ctypes import windll
            windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass
    except Exception:
        pass


def _assets_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).parent / "assets"


def main():
    QCoreApplication.setApplicationName("TSA - Tower Structural Analysis")
    _register_file_association()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    assets = _assets_path()

    # Ícono de la aplicación
    icon_path = assets / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Splash screen con QSplashScreen (nativo, sin overhead de WebEngine)
    # En modo dev (no frozen) se omite para agilizar la revisión.
    splash_path = assets / "splash.png"
    splash = None
    if getattr(sys, 'frozen', False) and splash_path.exists():
        pix = QPixmap(str(splash_path))
        # Ajustar al 90 % de la altura disponible si es muy grande
        screen_h = QApplication.primaryScreen().availableGeometry().height()
        max_h = int(screen_h * 0.90)
        if pix.height() > max_h:
            pix = pix.scaledToHeight(max_h, Qt.TransformationMode.SmoothTransformation)
        splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        app.processEvents()

    # Crear ventana principal MIENTRAS el splash está visible
    from app.main_window import MainWindow
    main_win = MainWindow()
    if icon_path.exists():
        main_win.setWindowIcon(QIcon(str(icon_path)))
    app._main_window = main_win

    if splash:
        # Mostrar main_win y cerrar splash después de 3 s
        QTimer.singleShot(3000, lambda: (splash.finish(main_win), main_win.show()))
    else:
        main_win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
