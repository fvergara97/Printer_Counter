# Mixin: pestaña Configuración SNMP.
import logging

import qtawesome as qta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QSpinBox, QGroupBox, QRadioButton
)

import core.snmp_engine as counter

logger = logging.getLogger(__name__)



class SNMPConfigMixin:
    """Pestaña Configuración SNMP — se mezcla con PrinterDashboard."""

    def create_config_tab(self):
        """Crea pestaña de configuración SNMP"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Community String
        comm_layout = QHBoxLayout()
        comm_layout.addWidget(QLabel("Community String:"))
        self.community_input = QLineEdit()
        self.community_input.setText("public")
        comm_layout.addWidget(self.community_input)
        layout.addLayout(comm_layout)
        
        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (segundos):"))
        self.timeout_input = QSpinBox()
        self.timeout_input.setValue(1)
        self.timeout_input.setMinimum(1)
        self.timeout_input.setMaximum(10)
        timeout_layout.addWidget(self.timeout_input)
        layout.addLayout(timeout_layout)
        
        # Retries
        retries_layout = QHBoxLayout()
        retries_layout.addWidget(QLabel("Reintentos:"))
        self.retries_input = QSpinBox()
        self.retries_input.setValue(1)
        self.retries_input.setMinimum(0)
        self.retries_input.setMaximum(5)
        retries_layout.addWidget(self.retries_input)
        layout.addLayout(retries_layout)
        
        # Modo de consulta SNMP
        mode_group = QGroupBox("Modo de Consulta SNMP")
        mode_layout = QVBoxLayout()
        
        self.mode_sequential = QRadioButton("Secuencial (consulta impresora por impresora - máxima compatibilidad)")
        self.mode_parallel = QRadioButton("Paralelo (todas simultáneamente - optimizado)")
        
        mode_layout.addWidget(self.mode_sequential)
        mode_layout.addWidget(self.mode_parallel)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Botón guardar config
        btn_save_config = QPushButton()
        btn_save_config.setIcon(qta.icon('fa5s.save', color='white'))
        btn_save_config.setText("  Guardar Configuración")
        btn_save_config.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_save_config.clicked.connect(self.save_config)
        layout.addWidget(btn_save_config)
        
        # Info
        info_label = QLabel("Nota: Los cambios en Community, Timeout y Retries se aplicarán en la próxima consulta SNMP.")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
