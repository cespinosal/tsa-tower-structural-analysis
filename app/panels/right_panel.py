import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QScrollArea, QDoubleSpinBox, QSpinBox, QComboBox, QFrame,
)
from PySide6.QtCore import Qt, Signal


# ── palette ───────────────────────────────────────────────────────────────────
_BG        = "#0a1018"
_BG_ROW    = "#0d1520"
_BG_INPUT  = "#151f2e"
_BORDER    = "#1e2f42"
_ACCENT    = "#1a7fe8"
_TXT_PRI   = "#c9d8e8"
_TXT_SEC   = "#5a7a96"
_TXT_DIM   = "#3d5870"

# ── shared styles ─────────────────────────────────────────────────────────────
_HDR_PANEL = (
    f"color:{_TXT_PRI}; font-size:13px; font-weight:600;"
    f" padding:10px 14px; background:#0c1622;"
    f" border-bottom:1px solid {_BORDER};"
)
_HDR_SECT = (
    f"color:{_TXT_PRI}; font-size:11px; font-weight:600; letter-spacing:0.5px;"
    f" padding:7px 14px 5px 14px; background:{_BG_ROW};"
    f" border-bottom:1px solid {_BORDER};"
)
_LBL  = f"color:{_TXT_SEC}; font-size:11px;"
_VAL  = f"color:{_TXT_PRI}; font-size:11px; font-weight:500;"
_DIM  = f"color:{_TXT_DIM}; font-size:10px;"

# Applied to all interactive inputs via setStyleSheet on individual widgets
_INPUT_CSS = f"""
    background: {_BG_INPUT};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    color: {_TXT_PRI};
    font-size: 11px;
    padding: 1px 4px;
    min-width: 0px;
"""
_INPUT_FOCUS = f"border-color: {_ACCENT};"


def _apply_input_style(w):
    cls = type(w).__name__
    w.setStyleSheet(f"""
        {cls} {{ {_INPUT_CSS} }}
        {cls}:focus {{ {_INPUT_CSS} {_INPUT_FOCUS} }}
        {cls}::up-button, {cls}::down-button {{
            width: 13px; background: #1e2f42; border: none;
        }}
        QComboBox QAbstractItemView {{
            background: {_BG_INPUT}; color: {_TXT_PRI};
            selection-background-color: {_ACCENT};
        }}
    """)


def _lbl(text: str, style: str = _LBL) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(style)
    return l


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{_BORDER}; background:{_BORDER}; max-height:1px;")
    return f


def _spin(val: float, lo: float, hi: float, dec: int = 1,
          suffix: str = " m", w: int = 68) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(lo, hi)
    sb.setDecimals(dec)
    sb.setValue(val)
    sb.setSuffix(suffix)
    sb.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
    sb.setFixedWidth(w)
    _apply_input_style(sb)
    return sb


def _ispin(val: int, lo: int, hi: int, w: int = 68) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(lo, hi)
    sb.setValue(val)
    sb.setFixedWidth(w)
    _apply_input_style(sb)
    return sb


# ── Section row ───────────────────────────────────────────────────────────────

class SectionRow(QWidget):
    def __init__(self, idx: int, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{_BG_ROW}; border-bottom:1px solid #111c28;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 5, 14, 5)
        lay.setSpacing(2)

        hdr = QLabel(f"Sección {idx + 1}")
        hdr.setStyleSheet(f"color:#6a90b2; font-size:10px; font-weight:600;")
        lay.addWidget(hdr)

        for code in ("M:", "D:", "H:"):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            row.addWidget(_lbl(code, f"color:{_TXT_DIM}; font-size:10px;"))
            row.addStretch()
            row.addWidget(_lbl("—", f"color:#3d5870; font-size:10px;"))
            lay.addLayout(row)


# ── Main panel ────────────────────────────────────────────────────────────────

class RightPanel(QWidget):
    configChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(272)
        self.setStyleSheet(f"background:{_BG};")
        self._build_ui()
        self._connect_signals()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_lbl("Panel de Información", _HDR_PANEL))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ border:none; background:{_BG}; }}"
            "QScrollBar:vertical { background:#0c1520; width:5px; }"
            "QScrollBar::handle:vertical { background:#263545; border-radius:2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
        )

        content = QWidget()
        content.setStyleSheet(f"background:{_BG};")
        content.setMaximumWidth(272)
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(self._build_geometry())
        cl.addWidget(_sep())
        cl.addWidget(self._build_sections())
        cl.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_geometry(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(_lbl("GEOMETRÍA DE LA TORRE", _HDR_SECT))

        body = QWidget()
        body.setStyleSheet(f"background:{_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 10, 14, 10)
        bl.setSpacing(10)

        # ── Dimension grid ────────────────────────────────────────────────
        # Uses QGridLayout so column widths are controlled precisely
        # Col 0 = label (fixed), Cols 1-3 = spinboxes (fixed 62px each)
        DIM_W = 62   # px per spinbox
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(0, 1)   # label column stretches
        grid.setColumnMinimumWidth(1, DIM_W)
        grid.setColumnMinimumWidth(2, DIM_W)
        grid.setColumnMinimumWidth(3, DIM_W)

        for col, txt in enumerate(("", "Base", "Cima", "Altura"), 0):
            l = _lbl(txt, _DIM)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(l, 0, col)

        self.base_spin   = _spin(4.0,  0.5,  99.9, w=DIM_W)
        self.top_spin    = _spin(2.0,  0.5,  99.9, w=DIM_W)
        self.height_spin = _spin(30.0, 1.0, 999.9, w=DIM_W)

        grid.addWidget(_lbl("Valor"), 1, 0)
        grid.addWidget(self.base_spin,   1, 1)
        grid.addWidget(self.top_spin,    1, 2)
        grid.addWidget(self.height_spin, 1, 3)

        bl.addLayout(grid)
        bl.addWidget(_sep())

        # ── Single-value rows ─────────────────────────────────────────────
        CTRL_W = 110   # width for single-row controls

        # Tower type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Triangular", "Cuadrada", "Arriostrada"])
        self.type_combo.setFixedWidth(CTRL_W)
        _apply_input_style(self.type_combo)
        bl.addLayout(self._row("Tipo sección:", self.type_combo))

        # Sections
        self.sections_spin = _ispin(8, 2, 40, w=CTRL_W)
        bl.addLayout(self._row("Secciones:", self.sections_spin))

        # Guyed-only (hidden by default)
        self._guyed_widget = self._build_guyed(CTRL_W)
        self._guyed_widget.hide()
        bl.addWidget(self._guyed_widget)

        # Weight (read-only)
        bl.addLayout(self._row("Peso total:", _lbl("0 kg", _VAL)))

        lay.addWidget(body)
        return w

    def _build_guyed(self, ctrl_w: int) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(10)
        lay.addWidget(_sep())

        self.shaft_spin = _spin(1.0, 0.3, 10.0, w=ctrl_w)
        lay.addLayout(self._row("Ancho fuste:", self.shaft_spin))

        self.guy_levels_spin = _ispin(3, 1, 10, w=ctrl_w)
        lay.addLayout(self._row("Niveles vientos:", self.guy_levels_spin))

        self.anchor_spin = _spin(15.0, 5.0, 200.0, w=ctrl_w)
        lay.addLayout(self._row("Radio anclaje:", self.anchor_spin))

        return w

    def _build_sections(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_lbl("DETALLE POR SECCIÓN", _HDR_SECT))

        self._sec_container = QWidget()
        self._sec_container.setStyleSheet(f"background:{_BG};")
        self._sec_lay = QVBoxLayout(self._sec_container)
        self._sec_lay.setContentsMargins(0, 0, 0, 0)
        self._sec_lay.setSpacing(0)
        self._update_section_rows(8)

        lay.addWidget(self._sec_container)
        return w

    @staticmethod
    def _row(label: str, widget: QWidget) -> QHBoxLayout:
        hl = QHBoxLayout()
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        hl.addWidget(_lbl(label))
        hl.addStretch()
        hl.addWidget(widget)
        return hl

    # ── signals ───────────────────────────────────────────────────────────────

    def _connect_signals(self):
        for sb in (self.base_spin, self.top_spin, self.height_spin,
                   self.shaft_spin, self.anchor_spin):
            sb.valueChanged.connect(self._emit_config)

        self.sections_spin.valueChanged.connect(
            lambda v: self._update_section_rows(v))
        self.sections_spin.valueChanged.connect(self._emit_config)
        self.guy_levels_spin.valueChanged.connect(self._emit_config)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

    def _on_type_changed(self):
        self._guyed_widget.setVisible(
            self.type_combo.currentText() == "Arriostrada")
        self._emit_config()

    def _update_section_rows(self, n: int):
        while self._sec_lay.count():
            item = self._sec_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i in range(n):
            self._sec_lay.addWidget(SectionRow(i))

    def _emit_config(self):
        _map = {"Triangular": "triangular", "Cuadrada": "square",
                "Arriostrada": "guyed"}
        self.configChanged.emit(json.dumps({
            "tower_type":    _map.get(self.type_combo.currentText(), "triangular"),
            "base_width":    self.base_spin.value(),
            "top_width":     self.top_spin.value(),
            "height":        self.height_spin.value(),
            "n_sections":    self.sections_spin.value(),
            "shaft_width":   self.shaft_spin.value(),
            "n_guy_levels":  self.guy_levels_spin.value(),
            "anchor_radius": self.anchor_spin.value(),
        }))
