import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QTabBar, QStatusBar, QToolButton,
    QButtonGroup, QSizePolicy, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

from app.bridge import Bridge


class MainWebView(QWebEngineView):
    """QWebEngineView no abre ventanas con window.open() salvo que se implemente
    createWindow() — aquí se crea una ventana nueva e independiente (usada por el
    botón Ayuda para abrir Ayuda_TSA.html como una página aparte, no en un iframe)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._popups = []  # mantener referencias vivas; si no, Python las recolecta y la ventana se cierra sola

    def createWindow(self, _type):
        popup = QWebEngineView()
        popup.setWindowTitle("TSA — Ayuda")
        popup.resize(1200, 840)
        popup.show()
        self._popups.append(popup)
        return popup


# ── colour palette (SectionBuilder) ──────────────────────────────────────────
BG_DEEP    = "#0A1628"
BG_TOOLBAR = "#060F1C"
BG_PANEL   = "#0D1E35"
BG_TAB     = "#060F1C"
BORDER     = "#1E3A5F"
ACCENT     = "#00D4FF"
ACCENT_HVR = "#33DDFF"
BTN_PRI    = "#185FA5"
BTN_PRI_HV = "#1A6FBF"
TEXT_PRI   = "#E2E8F0"
TEXT_SEC   = "#94A3B8"


# ── global stylesheet ─────────────────────────────────────────────────────────
GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background: {BG_DEEP};
    color: {TEXT_PRI};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}}
QStatusBar {{
    background: {BG_TOOLBAR};
    color: {TEXT_SEC};
    border-top: 1px solid {BORDER};
    font-size: 11px;
    padding: 0 8px;
}}
QToolTip {{
    background: #1c2b3a;
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _btn(text: str, accent: bool = False, small: bool = False,
         checkable: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setCheckable(checkable)
    h = 26 if small else 30
    b.setFixedHeight(h)
    if accent:
        b.setStyleSheet(f"""
            QPushButton {{
                background: {BTN_PRI}; color: #fff;
                border: none; border-radius: 5px;
                padding: 0 14px; font-weight: 600; font-size: 12px;
            }}
            QPushButton:hover {{ background: {BTN_PRI_HV}; }}
            QPushButton:pressed {{ background: #104888; }}
        """)
    elif checkable:
        b.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SEC};
                border: 1px solid {BORDER}; border-radius: 4px;
                padding: 0 10px; font-size: 11px;
            }}
            QPushButton:checked {{
                background: #1a3050; color: {TEXT_PRI};
                border-color: {ACCENT};
            }}
            QPushButton:hover:!checked {{ background: #141e2c; color:{TEXT_PRI}; }}
        """)
    else:
        b.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SEC};
                border: 1px solid transparent;
                border-radius: 4px; padding: 0 10px;
            }}
            QPushButton:hover {{ color: {TEXT_PRI}; background: #141e2c; }}
            QPushButton:pressed {{ background: #1a2535; }}
        """)
    return b


def _icon_btn(symbol: str, tooltip: str = "", active: bool = False) -> QPushButton:
    b = QPushButton(symbol)
    b.setFixedSize(36, 36)
    b.setToolTip(tooltip)
    b.setCheckable(True)
    b.setChecked(active)
    b.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {'#5a8fc7' if active else TEXT_SEC};
            border: none; border-radius: 6px;
            font-size: 15px;
        }}
        QPushButton:checked {{
            background: #14243a;
            color: {ACCENT};
        }}
        QPushButton:hover:!checked {{ color: {TEXT_PRI}; background: #141e2c; }}
    """)
    return b


# ── top toolbar ───────────────────────────────────────────────────────────────

class TopBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.setStyleSheet(f"""
            TopBar {{
                background: {BG_TOOLBAR};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)

        # Logo
        logo = QLabel(
            "🏗 <span style='font-size:15px; font-weight:700; letter-spacing:1px;'>TSA</span>"
            "<br><span style='font-size:9px; font-weight:400; letter-spacing:1.2px;"
            f" color:{TEXT_SEC};'>TOWER STRUCTURAL ANALYSIS</span>"
        )
        logo.setTextFormat(Qt.TextFormat.RichText)
        logo.setStyleSheet(f"color:{TEXT_PRI};")
        lay.addWidget(logo)

        # Tower name
        tower_lbl = QLabel("  Tower 30  ▾")
        tower_lbl.setStyleSheet(f"""
            color:{TEXT_SEC}; font-size:12px;
            background:#121d2b; border:1px solid {BORDER};
            border-radius:5px; padding:3px 8px;
        """)
        lay.addWidget(tower_lbl)

        # Undo / Redo
        for sym in ("←", "→"):
            b = _btn(sym, small=True)
            b.setFixedWidth(28)
            lay.addWidget(b)

        # Run Analysis
        self.run_btn = _btn("▶  Ejecutar Análisis", accent=True)
        self.run_btn.setFixedHeight(32)
        lay.addWidget(self.run_btn)

        lay.addStretch()

        # SI / IMP toggles
        grp = QButtonGroup(self)
        for txt in ("SI", "IMP"):
            b = _btn(txt, checkable=True, small=True)
            b.setFixedWidth(36)
            grp.addButton(b)
            lay.addWidget(b)
        grp.buttons()[0].setChecked(True)

        # Results / Export / Share / Help
        for txt in ("Mostrar Resultados", "Exportar", "Compartir", "Ayuda"):
            lay.addWidget(_btn(txt, small=True))



# ── tab bar ───────────────────────────────────────────────────────────────────

class ModuleTabBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            ModuleTabBar {{
                background: {BG_TAB};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(48, 0, 8, 0)
        lay.setSpacing(0)

        tabs = [
            ("⬡  FEM",          True),
            ("⬡  Códigos",      False),
            ("  Cargas Viento", False),
            ("⬡  Antenas",      False),
            ("⬡  Escaleras",    False),
            ("⬡  Plataformas",  False),
        ]
        grp = QButtonGroup(self)
        for label, active in tabs:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(active)
            b.setFixedHeight(35)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {TEXT_SEC};
                    border: none;
                    border-bottom: 2px solid transparent;
                    padding: 0 14px;
                    font-size: 12px;
                }}
                QPushButton:checked {{
                    color: {TEXT_PRI};
                    border-bottom: 2px solid {ACCENT};
                    background: #0d1a28;
                }}
                QPushButton:hover:!checked {{
                    color: {TEXT_PRI};
                    background: #0b1520;
                }}
            """)
            grp.addButton(b)
            lay.addWidget(b)

        lay.addStretch()

        # Right-side viewer icons
        for sym, tip in [("🏷", "Etiquetas"), ("📈", "Gráficas"),
                          ("⊞", "Tabla"), ("⊙", "Vista"), ("⚙", "Config")]:
            b = _icon_btn(sym, tip)
            b.setFixedSize(30, 30)
            lay.addWidget(b)


# ── left sidebar ──────────────────────────────────────────────────────────────

class LeftSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(44)
        self.setStyleSheet(f"background:{BG_TOOLBAR}; border-right:1px solid {BORDER};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(2)

        icons = [
            ("🏠", "Inicio",        False),
            ("📡", "Torre",         True),
            ("🔧", "Análisis",      False),
            ("📊", "Optimización",  False),
            ("📋", "Reporte",       False),
            ("📍", "Ubicación",     False),
            ("🐛", "Debug",         False),
            ("⚡", "Config rápida", False),
        ]
        grp = QButtonGroup(self)
        for sym, tip, active in icons:
            b = _icon_btn(sym, tip, active)
            b.setFixedSize(36, 36)
            grp.addButton(b)
            lay.addWidget(b, alignment=Qt.AlignmentFlag.AlignHCenter)
            if tip == "Reporte":
                lay.addStretch()

        lay.addStretch()


# ── main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TSA – Tower Structural Analysis")
        self.resize(1280, 820)
        self.setStyleSheet(GLOBAL_STYLE)
        self._force_close = False  # True una vez confirmado/guardado — deja pasar el siguiente close()
        self._build_ui()
        self._setup_webchannel()
        self._load_viewer()
        self._connect_signals()

    # ── Confirmar guardado al cerrar la ventana ──────────────────────────────
    # closeEvent es síncrono pero runJavaScript es asíncrono — se ignora el primer
    # close, se consulta el estado "sin guardar" en JS, y solo si el usuario confirma
    # (o no había nada que guardar) se vuelve a llamar a close() con _force_close=True.
    def closeEvent(self, event):
        if self._force_close:
            event.accept()
            return
        event.ignore()
        self.web_view.page().runJavaScript(
            "typeof hasUnsavedChanges === 'function' ? hasUnsavedChanges() : false",
            self._on_dirty_check,
        )

    def _on_dirty_check(self, dirty: bool):
        if not dirty:
            self._force_close = True
            self.close()
            return
        # Botones con texto propio en español — los QMessageBox.StandardButton (Save/
        # Discard/Cancel) se traducen según el locale del sistema, no del idioma de la
        # app, así que en una máquina en inglés saldrían en inglés.
        box = QMessageBox(self)
        box.setWindowTitle("Guardar cambios")
        box.setText("Tienes cambios sin guardar. ¿Quieres guardarlos antes de salir?")
        btn_save = box.addButton("Guardar", QMessageBox.ButtonRole.AcceptRole)
        btn_discard = box.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_save)
        box.exec()
        clicked = box.clickedButton()
        if clicked == btn_cancel:
            return  # se queda abierta
        if clicked == btn_discard:
            self._force_close = True
            self.close()
            return
        self.web_view.page().runJavaScript(
            "typeof triggerSaveForClose === 'function' ? triggerSaveForClose() : false",
            self._on_save_done,
        )

    def _on_save_done(self, _result):
        # Se cierra de todas formas aunque el guardado falle/cancele (showSaveFilePicker
        # cancelado, etc.) — el usuario ya tomó la decisión de guardar; no lo bloqueamos
        # en un loop si el diálogo nativo no se completó.
        self._force_close = True
        self.close()

    def _build_ui(self):
        self.status_bar = QStatusBar()
        # Nunca se había adjuntado a la ventana con setStatusBar() — bridge.statusMessage
        # se disparaba hacia un widget huérfano que no se mostraba en ningún lado, así
        # que ningún mensaje de status (incluido el de guardar PDF) era visible. Bug
        # preexistente encontrado al diagnosticar el problema del PDF (2026-06-26).
        self.setStatusBar(self.status_bar)
        self.web_view = MainWebView()
        self.setCentralWidget(self.web_view)

    def _setup_webchannel(self):
        self.bridge = Bridge(self, page=self.web_view.page())
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject("bridge", self.bridge)

        # Allow local file pages to load remote CDN resources
        settings = self.web_view.page().settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

        # Manejar descargas (exportar STAAD, DXF, etc.)
        self.web_view.page().profile().downloadRequested.connect(self._on_download)

    def _on_download(self, download):
        suggested = download.suggestedFileName() or "export"
        ext = Path(suggested).suffix or ".txt"
        filters = {
            ".std": "STAAD.Pro (*.std)",
            ".dxf": "DXF (*.dxf)",
            ".csv": "CSV (*.csv)",
        }.get(ext.lower(), f"Archivo (*{ext})")

        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo", suggested, f"{filters};;Todos los archivos (*)")
        if path:
            download.setDownloadDirectory(str(Path(path).parent))
            download.setDownloadFileName(Path(path).name)
            download.accept()
        else:
            download.cancel()

    def _load_viewer(self):
        # sys._MEIPASS exists when frozen by PyInstaller (onefile or onedir)
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent  # project root in dev
        html_path = base / "app" / "web" / "viewer.html"
        self.web_view.load(QUrl.fromLocalFile(str(html_path)))

    def _connect_signals(self):
        self.bridge.statusMessage.connect(
            lambda msg: self.status_bar.showMessage(f"> {msg}"))
