# Mixin: pestaña Ubicación de Archivos (SMB / local).
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime

import qtawesome as qta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGroupBox, QMessageBox, QFileDialog,
    QTextEdit, QRadioButton, QButtonGroup
)

import core.snmp_engine as counter
from core.config import config as app_config

logger = logging.getLogger(__name__)



class StorageMixin:
    """Pestaña Almacenamiento — se mezcla con PrinterDashboard."""

    def create_storage_tab(self):
        """Crea pestaña de configuración de ubicación de archivos"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # ===== SECCIÓN 1: UBICACIÓN DE PRINTERS.JSON =====
        location_group = QGroupBox("Ubicación de printers.json")
        location_layout = QVBoxLayout()
        
        # Grupo de radio buttons MUTUAMENTE EXCLUYENTES
        self.location_group = QButtonGroup()
        
        # Opción Local (Radio Button)
        self.radio_local = QRadioButton("📁 Guardar localmente (en esta carpeta)")
        self.radio_local.setChecked(not app_config.get("use_smb", False))
        self.radio_local.toggled.connect(self.on_location_changed)
        self.location_group.addButton(self.radio_local, 0)  # 0 = Local
        location_layout.addWidget(self.radio_local)
        
        # Opción SMB/Red (Radio Button)
        self.radio_smb = QRadioButton("🌐 Guardar en carpeta compartida (SMB/Red)")
        self.radio_smb.setChecked(app_config.get("use_smb", False))
        self.radio_smb.toggled.connect(self.on_location_changed)
        self.location_group.addButton(self.radio_smb, 1)  # 1 = SMB
        location_layout.addWidget(self.radio_smb)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        # ===== SECCIÓN 2: CONFIGURACIÓN SMB =====
        smb_group = QGroupBox("Configuración de carpeta compartida (SMB/UNC)")
        smb_layout = QVBoxLayout()
        
        # Input para ruta UNC
        ruta_layout = QHBoxLayout()
        ruta_layout.addWidget(QLabel("Ruta UNC:"))
        self.smb_path_input = QLineEdit()
        self.smb_path_input.setText(app_config.get("smb_path", "\\\\192.168.1.241\\printers_snmp"))
        self.smb_path_input.setEnabled(app_config.get("use_smb", False))
        ruta_layout.addWidget(self.smb_path_input)
        smb_layout.addLayout(ruta_layout)
        
        # Botón para probar conexión
        test_layout = QHBoxLayout()
        btn_test = QPushButton("🔍 Probar Conexión")
        btn_test.setMinimumWidth(150)
        btn_test.clicked.connect(self.test_smb_connection)
        test_layout.addWidget(btn_test)
        
        self.test_status = QLabel("Estado: no probado")
        self.test_status.setStyleSheet("color: gray;")
        test_layout.addWidget(self.test_status)
        test_layout.addStretch()
        smb_layout.addLayout(test_layout)
        
        # Info de rutas
        info_layout = QHBoxLayout()
        info_label = QLabel("Ejemplo: \\\\192.168.1.123\\printers_snmp")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        info_layout.addWidget(info_label)
        smb_layout.addLayout(info_layout)
        
        smb_group.setLayout(smb_layout)
        layout.addWidget(smb_group)
        
        # ===== SECCIÓN 3: UBICACIÓN DE EXPORTACIÓN =====
        export_group = QGroupBox("Ubicación de Exportación")
        export_layout = QVBoxLayout()
        
        export_path_layout = QHBoxLayout()
        export_path_layout.addWidget(QLabel("Carpeta de exportación:"))
        self.export_path_input = QLineEdit()
        self.export_path_input.setText(str(self.export_path))
        self.export_path_input.setReadOnly(True)
        export_path_layout.addWidget(self.export_path_input)
        
        btn_browse = QPushButton("📂 Examinar")
        btn_browse.setMinimumWidth(100)
        btn_browse.clicked.connect(self.browse_export_path)
        export_path_layout.addWidget(btn_browse)
        
        export_layout.addLayout(export_path_layout)
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # ===== SECCIÓN 4: IMPORTAR/EXPORTAR JSON =====
        json_group = QGroupBox("Gestión de printers.json")
        json_layout = QHBoxLayout()
        
        btn_export_json_full = QPushButton("⬇️ Exportar JSON Completo")
        btn_export_json_full.setMinimumWidth(180)
        btn_export_json_full.clicked.connect(self.export_printers_json)
        json_layout.addWidget(btn_export_json_full)
        
        btn_import_json = QPushButton("⬆️ Importar JSON")
        btn_import_json.setMinimumWidth(180)
        btn_import_json.clicked.connect(self.import_printers_json)
        json_layout.addWidget(btn_import_json)
        
        json_group.setLayout(json_layout)
        layout.addWidget(json_group)
        
        # Botón guardar
        btn_save_storage = QPushButton("💾 Guardar Ubicación")
        btn_save_storage.setMinimumWidth(150)
        btn_save_storage.clicked.connect(self.save_storage_config)
        layout.addWidget(btn_save_storage)
        
        # Información actual
        info_group = QGroupBox("Información Actual")
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        self.update_storage_info()
        info_group.setLayout(QVBoxLayout())
        info_group.layout().addWidget(self.info_text)
        layout.addWidget(info_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def browse_export_path(self):
        """Permite seleccionar carpeta de exportación"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de exportación",
            str(self.export_path)
        )
        
        if folder:
            self.export_path = Path(folder)
            self.export_path_input.setText(str(self.export_path))
            QMessageBox.information(self, "Éxito", f"Carpeta de exportación actualizada")
    
    
    def on_location_changed(self):
        """Maneja cambios en la selección de ubicación"""
        use_smb = self.radio_smb.isChecked()
        self.smb_path_input.setEnabled(use_smb)
    
    def test_smb_connection(self):
        """Prueba la conexión a la ruta SMB"""
        smb_path = self.smb_path_input.text().strip()
        
        if not smb_path:
            QMessageBox.warning(self, "Error", "Ingresa una ruta UNC válida")
            return
        
        # Usar la ruta directamente (Windows debería resolverla)
        from pathlib import Path
        try:
            path_obj = Path(smb_path)
            if path_obj.exists():
                self.test_status.setText("Estado: ✓ Conexión OK")
                self.test_status.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(self, "Éxito", "Conexión a SMB establecida correctamente")
            else:
                self.test_status.setText("Estado: ✗ Ruta no accesible")
                self.test_status.setStyleSheet("color: red; font-weight: bold;")
                QMessageBox.warning(self, "Error", "La ruta no es accesible. Verifica:\n- Que la ruta sea correcta\n- Que la carpeta compartida esté activa\n- Tus permisos de acceso")
        except PermissionError:
            self.test_status.setText("Estado: ✗ Acceso denegado")
            self.test_status.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(self, "Error", "Acceso denegado a la ruta SMB")
        except Exception as e:
            self.test_status.setText("Estado: ✗ Error de conexión")
            self.test_status.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
    
    def save_storage_config(self):
        """Guarda la configuración de ubicación de archivos"""
        use_smb = self.radio_smb.isChecked()
        smb_path = self.smb_path_input.text().strip()
        
        if use_smb and not smb_path:
            QMessageBox.warning(self, "Error", "Ingresa una ruta UNC válida")
            return
        
        # Guardar en configuración
        app_config.set("use_smb", use_smb)
        if use_smb:
            app_config.set("smb_path", smb_path)
        
        # Actualizar contador.py
        counter.JSON_PATH = app_config.get_json_path()
        
        self.update_storage_info()
        QMessageBox.information(self, "Éxito", "Ubicación de archivos guardada")
    
    def update_storage_info(self):
        """Actualiza la información de ubicación mostrada"""
        use_smb = app_config.get("use_smb", False)
        json_path = app_config.get_json_path()
        
        info_text = f"Modo: {'🌐 RED (SMB)' if use_smb else '📁 LOCAL'}\n"
        info_text += f"Ruta: {json_path}\n"
        
        # Validar acceso
        try:
            from pathlib import Path
            if Path(json_path).parent.exists():
                info_text += "Estado: ✓ Accesible"
            else:
                info_text += "Estado: ✗ No accesible"
        except:
            info_text += "Estado: ✗ Error verificando acceso"
        
        self.info_text.setText(info_text)
    
