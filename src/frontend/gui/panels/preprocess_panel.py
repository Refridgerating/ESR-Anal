"""Pre-processing panel for ESR-Lab GUI."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from backend.core.spectrum import ESRSpectrum
from ..plot_view import PlotView


class PreprocessPanel(QWidget):
    """Widget providing basic preprocessing controls."""

    def __init__(self, plot_view: PlotView, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plot_view = plot_view
        self.sp: ESRSpectrum | None = None

        layout = QVBoxLayout(self)

        # Baseline controls
        bl_group = QGroupBox("Baseline")
        bl_layout = QHBoxLayout()
        self.rb_poly = QRadioButton("Poly")
        self.rb_poly.setChecked(True)
        self.rb_spline = QRadioButton("Spline")
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 10)
        self.order_spin.setValue(2)
        self.btn_baseline = QPushButton("Apply")
        for w in (
            self.rb_poly,
            self.rb_spline,
            QLabel("Order"),
            self.order_spin,
            self.btn_baseline,
        ):
            bl_layout.addWidget(w)
        bl_group.setLayout(bl_layout)
        layout.addWidget(bl_group)

        # Phase controls
        ph_group = QGroupBox("Phase")
        ph_layout = QHBoxLayout()
        self.phase_slider = QSlider(Qt.Horizontal)
        self.phase_slider.setRange(-20, 20)
        self.btn_phase_auto = QPushButton("Auto")
        ph_layout.addWidget(self.phase_slider)
        ph_layout.addWidget(self.btn_phase_auto)
        ph_group.setLayout(ph_layout)
        layout.addWidget(ph_group)

        # Smoothing controls
        sm_group = QGroupBox("Smoothing")
        sm_layout = QHBoxLayout()
        self.win_spin = QSpinBox()
        self.win_spin.setRange(3, 101)
        self.win_spin.setSingleStep(2)
        self.win_spin.setValue(11)
        self.poly_spin = QSpinBox()
        self.poly_spin.setRange(1, 10)
        self.poly_spin.setValue(3)
        self.btn_smooth = QPushButton("Apply")
        for w in (
            QLabel("Window"),
            self.win_spin,
            QLabel("Poly"),
            self.poly_spin,
            self.btn_smooth,
        ):
            sm_layout.addWidget(w)
        sm_group.setLayout(sm_layout)
        layout.addWidget(sm_group)

        # Action buttons
        self.btn_integrate = QPushButton("Integrate → Absorption")
        self.btn_area = QPushButton("Compute Area (ROI)")
        layout.addWidget(self.btn_integrate)
        layout.addWidget(self.btn_area)
        layout.addStretch(1)

        # Connections
        self.btn_baseline.clicked.connect(self._apply_baseline)
        self.btn_smooth.clicked.connect(self._apply_smooth)
        self.phase_slider.valueChanged.connect(self._apply_phase)
        self.btn_phase_auto.clicked.connect(self._apply_phase_auto)
        self.btn_integrate.clicked.connect(self._integrate)
        self.btn_area.clicked.connect(self._area)

    def set_current_spectrum(self, sp: ESRSpectrum) -> None:
        """Assign the spectrum to be processed."""

        self.sp = sp

    # Callback helpers -------------------------------------------------
    def _apply_baseline(self) -> None:
        if self.sp is None:
            return
        method = "poly" if self.rb_poly.isChecked() else "spline"
        order = self.order_spin.value()
        self.sp.baseline(method=method, order=order)
        self.plot_view.plot_derivative(self.sp, clear=True)

    def _apply_smooth(self) -> None:
        if self.sp is None:
            return
        window = self.win_spin.value()
        if window % 2 == 0:
            window += 1
            self.win_spin.setValue(window)
        poly = self.poly_spin.value()
        self.sp.smooth(window=window, polyorder=poly)
        self.plot_view.plot_derivative(self.sp, clear=True)

    def _apply_phase(self) -> None:
        if self.sp is None:
            return
        rad = np.deg2rad(self.phase_slider.value())
        self.sp.phase_correct(rad)
        self.plot_view.plot_derivative(self.sp, clear=True)

    def _apply_phase_auto(self) -> None:
        if self.sp is None:
            return
        self.sp.phase_auto()
        if self.sp.meta.phase_rad is not None:
            self.phase_slider.setValue(int(np.rad2deg(self.sp.meta.phase_rad)))
        self.plot_view.plot_derivative(self.sp, clear=True)

    def _integrate(self) -> None:
        if self.sp is None:
            return
        self.sp.to_absorption()
        self.plot_view.plot_absorption(self.sp)

    def _area(self) -> None:
        if self.sp is None:
            return
        self.sp.to_absorption()
        area = self.sp.to_area()
        print(f"Area: {area}")

