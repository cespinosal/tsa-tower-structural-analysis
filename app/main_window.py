import sys
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QStatusBar, QFileDialog, QMessageBox
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
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


# ── colour palette (usada por GLOBAL_STYLE) ──────────────────────────────────
BG_DEEP    = "#0A1628"
BG_TOOLBAR = "#060F1C"
BORDER     = "#1E3A5F"
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
