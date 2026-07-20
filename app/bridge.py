import base64
import json
import os
import shutil
import sys
import tempfile
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog
from app.tower.model import TowerConfig
from app.tower.generator import generate_tower

DEFAULT_PROJECT_DIR = r"C:\Users\cespi\Downloads\TSA (Tower Structural Analysis)"


class Bridge(QObject):
    towerDataChanged = Signal(str)
    statusMessage = Signal(str)

    def __init__(self, parent=None, page=None):
        super().__init__(parent)
        self.config = TowerConfig()
        self._page = page

    @Slot(result=bool)
    def isDevMode(self) -> bool:
        return not getattr(sys, "frozen", False)

    @Slot(str, str)
    def previewReportInBrowser(self, html: str, suggested_name: str):
        # Manipular la página viva de la app dentro de QtWebEngine para imprimir
        # resultó frágil en MÁS DE UN intento (páginas duplicadas, márgenes de más,
        # footer mal anclado), tanto manipulando la página visible como con una
        # QWebEnginePage oculta + printToPdf() directo — el motor de impresión de
        # QtWebEngine no maneja bien este documento de 11 hojas sin importar cuánto se
        # ajuste el CSS. Se abre en el navegador real del sistema, donde el contenido
        # SÍ se renderiza correctamente — pedido explícito del usuario tras confirmar
        # la regresión del segundo intento (2026-06-26, revertido 2026-06-27, y se
        # intentó retomar con savePdfDirectly() pero el usuario pidió quitarlo de
        # nuevo).
        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix="tsa_report_"))
            tmp_path = tmp_dir / (suggested_name or "reporte.html")
            tmp_path.write_text(html, encoding="utf-8")
            webbrowser.open(tmp_path.as_uri())
        except Exception as exc:
            self.statusMessage.emit(f"Error al abrir la vista previa: {exc}")

    @Slot(str, str)
    def exportMemoriaPdf(self, html: str, suggested_name: str):
        # 1 — Escribir HTML a temporal (WeasyPrint necesita la ruta del archivo para
        #     resolver rutas relativas; además el HTML supera el límite de setHtml()).
        tmp_dir  = Path(tempfile.mkdtemp(prefix="tsa_pdf_"))
        tmp_html = tmp_dir / "reporte.html"
        tmp_pdf  = tmp_dir / suggested_name
        tmp_html.write_text(html, encoding="utf-8")

        self.statusMessage.emit("Generando PDF…  (puede tardar unos segundos)")

        # 2 — Generar PDF con WeasyPrint (renderizador propio, no Chromium headless).
        try:
            from weasyprint import HTML as WP
            WP(filename=str(tmp_html)).write_pdf(str(tmp_pdf))
        except Exception as exc:
            self.statusMessage.emit(f"Error al generar PDF: {exc}")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return

        # 3 — Abrir el PDF en el visor del sistema (vista previa real del resultado).
        try:
            os.startfile(str(tmp_pdf))
        except Exception:
            pass

        # 4 — Diálogo para guardar la copia permanente (mientras el visor está abierto).
        path, _ = QFileDialog.getSaveFileName(
            None, "Guardar Memoria de Cálculo",
            str(Path(DEFAULT_PROJECT_DIR) / suggested_name),
            "PDF (*.pdf)")

        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            shutil.copy2(str(tmp_pdf), path)
            self.statusMessage.emit(f"PDF guardado: {path}")
        else:
            self.statusMessage.emit("PDF generado — no se guardó copia permanente.")

        # No borrar tmp_dir inmediatamente: el visor de PDF aún puede estar leyendo
        # el archivo. El SO limpiará los temporales.

    @Slot(str, str)
    def saveDocx(self, b64: str, suggested_name: str):
        path, _ = QFileDialog.getSaveFileName(
            None, "Guardar Memoria de Cálculo",
            str(Path(DEFAULT_PROJECT_DIR) / suggested_name),
            "Word (*.docx)")
        if not path:
            self.statusMessage.emit("Exportación Word cancelada.")
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        try:
            Path(path).write_bytes(base64.b64decode(b64))
            self.statusMessage.emit(f"Word guardado: {path}")
            os.startfile(path)
        except Exception as exc:
            self.statusMessage.emit(f"Error al guardar Word: {exc}")

    @Slot(str, str, result=str)
    def saveProjectDialog(self, json_str: str, suggested_name: str) -> str:
        path, _ = QFileDialog.getSaveFileName(
            None, "Guardar proyecto",
            str(Path(DEFAULT_PROJECT_DIR) / suggested_name),
            "TSA Project (*.tsa)")
        if not path:
            return json.dumps({"cancelled": True})
        if not path.lower().endswith(".tsa"):
            path += ".tsa"
        try:
            Path(path).write_text(json_str, encoding="utf-8")
            return json.dumps({"cancelled": False, "path": path, "filename": Path(path).name})
        except Exception as exc:
            return json.dumps({"cancelled": False, "error": str(exc)})

    @Slot(str, str, result=str)
    def writeProjectFile(self, path: str, json_str: str) -> str:
        try:
            Path(path).write_text(json_str, encoding="utf-8")
            return json.dumps({"ok": True})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    @Slot(result=str)
    def openProjectDialog(self) -> str:
        path, _ = QFileDialog.getOpenFileName(
            None, "Abrir proyecto", DEFAULT_PROJECT_DIR,
            "TSA Project (*.tsa)")
        if not path:
            return json.dumps({"cancelled": True})
        try:
            content = Path(path).read_text(encoding="utf-8")
            return json.dumps({"cancelled": False, "path": path, "filename": Path(path).name, "content": content})
        except Exception as exc:
            return json.dumps({"cancelled": False, "error": str(exc)})

    @Slot()
    def viewerReady(self):
        self.regenerate()

    @Slot(str)
    def updateConfig(self, json_str: str):
        try:
            self.config.update(json.loads(json_str))
            self.regenerate()
        except Exception as exc:
            self.statusMessage.emit(f"Error: {exc}")

    def regenerate(self):
        nodes, members = generate_tower(self.config)
        payload = {
            "nodes":   [{"x": n.x, "y": n.y, "z": n.z} for n in nodes],
            "members": [{"node_i": m.node_i, "node_j": m.node_j, "type": m.member_type}
                        for m in members],
        }
        self.towerDataChanged.emit(json.dumps(payload))
        self.statusMessage.emit(
            f"Torre generada  |  Nodos: {len(nodes)}  |  "
            f"Elementos: {len(members)}  |  Altura: {self.config.height:.1f} m"
        )
