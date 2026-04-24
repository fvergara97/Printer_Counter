# Mixin: diálogos Agregar Modelo y Editar Modelo.
import json
import logging

import qtawesome as qta
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QMessageBox, QDialog, QCheckBox, QFrame
)
from PyQt5.QtCore import Qt

import core.snmp_engine as counter

logger = logging.getLogger(__name__)



class ModelDialogsMixin:
    """Diálogos de gestión de modelos — se mezcla con PrinterDashboard."""

    def add_model(self):
        """Abre diálogo para agregar nuevo modelo"""
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("Agregar Modelo")
        dialog.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout()
        
        # Marca
        layout.addWidget(QLabel("Marca:"))
        input_marca = QLineEdit()
        layout.addWidget(input_marca)
        
        # Nombre Modelo
        layout.addWidget(QLabel("Nombre del Modelo:"))
        input_modelo = QLineEdit()
        layout.addWidget(input_modelo)
        
        # OID Contador
        layout.addWidget(QLabel("OID Contador:"))
        input_oid_contador = QLineEdit()
        layout.addWidget(input_oid_contador)
        
        # OID Tóner Actual
        layout.addWidget(QLabel("OID Tóner Actual (opcional):"))
        input_oid_toner_actual = QLineEdit()
        layout.addWidget(input_oid_toner_actual)
        
        # OID Tóner Máximo
        layout.addWidget(QLabel("OID Tóner Máximo (opcional):"))
        input_oid_toner_maximo = QLineEdit()
        layout.addWidget(input_oid_toner_maximo)
        
        # OID Modelo Tóner / Entrada manual
        label_toner_model = QLabel("OID Modelo Tóner (opcional):")
        layout.addWidget(label_toner_model)
        input_oid_modelo_toner = QLineEdit()
        input_oid_modelo_toner.setPlaceholderText("Ej: 1.3.6.1.2.1.43.11.1.1.6.1.1")
        layout.addWidget(input_oid_modelo_toner)
        
        # Separador visual
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #bdc3c7; margin: 2px 0px;")
        layout.addWidget(sep)
        
        # Checkbox para habilitar entrada manual
        chk_manual = QCheckBox("📝 Ingresar modelo de tóner manualmente (para impresoras que no lo publican por SNMP)")
        chk_manual.setStyleSheet("font-weight: bold; color: #e65100; padding: 2px;")
        layout.addWidget(chk_manual)
        
        label_manual = QLabel("Nombre del modelo de tóner:")
        label_manual.setVisible(False)
        layout.addWidget(label_manual)
        input_toner_model_manual = QLineEdit()
        input_toner_model_manual.setPlaceholderText("Ej: TK-3182, TN-850, CF226A...")
        input_toner_model_manual.setVisible(False)
        input_toner_model_manual.setStyleSheet("background-color: #fff8e1; border: 1px solid #e65100;")
        layout.addWidget(input_toner_model_manual)
        
        def toggle_toner_manual(checked):
            input_oid_modelo_toner.setEnabled(not checked)
            input_oid_modelo_toner.setStyleSheet("background-color: #eeeeee; color: gray;" if checked else "")
            label_toner_model.setText("OID Modelo Tóner (deshabilitado — usando entrada manual):" if checked else "OID Modelo Tóner (opcional):")
            label_manual.setVisible(checked)
            input_toner_model_manual.setVisible(checked)
        
        chk_manual.toggled.connect(toggle_toner_manual)
        
        # Botones
        button_layout = QHBoxLayout()
        btn_ok = QPushButton()
        btn_ok.setIcon(qta.icon('fa5s.check', color='white'))
        btn_ok.setText("  Guardar")
        btn_ok.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_cancel = QPushButton()
        btn_cancel.setIcon(qta.icon('fa5s.times', color='white'))
        btn_cancel.setText("  Cancelar")
        btn_cancel.setStyleSheet("background-color: #757575; color: white; font-weight: bold; padding: 8px;")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            marca = input_marca.text().strip()
            modelo = input_modelo.text().strip()
            oid_contador = input_oid_contador.text().strip()
            oid_toner_actual = input_oid_toner_actual.text().strip()
            oid_toner_maximo = input_oid_toner_maximo.text().strip()
            usar_manual = chk_manual.isChecked()
            oid_modelo_toner = "" if usar_manual else input_oid_modelo_toner.text().strip()
            toner_model_manual = input_toner_model_manual.text().strip() if usar_manual else ""
            
            # Validar
            if not marca or not modelo or not oid_contador:
                QMessageBox.warning(self, "Error", "Marca, Modelo y OID Contador son obligatorios")
                return
            
            # Validar que OIDs de tóner vayan juntos
            if (oid_toner_actual and not oid_toner_maximo) or (oid_toner_maximo and not oid_toner_actual):
                QMessageBox.warning(
                    self,
                    "Error",
                    "OID Tóner Actual y OID Tóner Máximo deben ingresarse juntos o no ingresarse"
                )
                return
            
            if usar_manual and not toner_model_manual:
                QMessageBox.warning(self, "Error", "Ingresa el nombre manual del modelo de tóner")
                return
            
            # Guardar en JSON
            data = counter.load_json(display=False)
            if data is None:
                data = {}
            
            if "_modelos" not in data:
                data["_modelos"] = {}
            
            # Normalizar marca para búsqueda case-insensitive
            marca_key_existing = next(
                (k for k in data["_modelos"] if k.lower() == marca.lower()), None
            )
            if marca_key_existing is None:
                data["_modelos"][marca] = {}
                marca_key_existing = marca
            
            # Verificar si el modelo ya existe (case-insensitive)
            modelos_marca_dict = data["_modelos"][marca_key_existing]
            modelo_key_existing = next(
                (k for k in modelos_marca_dict if k.lower() == modelo.lower()), None
            )
            if modelo_key_existing is not None:
                QMessageBox.warning(
                    self,
                    "Modelo Duplicado",
                    f"⚠️ El modelo ya existe:\n\n"
                    f"Marca: {marca_key_existing}\n"
                    f"Modelo: {modelo_key_existing}\n\n"
                    "Si deseas modificarlo, usa el botón \"Editar\"."
                )
                return
            
            modelo_data = {
                "oid_contador": oid_contador,
                "oid_nombre": oid_contador,
                "oid_toner_actual": oid_toner_actual,
                "oid_toner_maximo": oid_toner_maximo,
                "oid_modelo_toner": oid_modelo_toner,
            }
            if usar_manual:
                modelo_data["toner_model_manual"] = toner_model_manual
            
            data["_modelos"][marca_key_existing][modelo] = modelo_data
            
            try:
                with open(counter.JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                QMessageBox.information(self, "Éxito", f"Modelo {modelo} agregado correctamente")
                self.load_models()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
    
    def edit_model(self):
        """Edita el modelo seleccionado"""
        row = self.models_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un modelo para editar")
            return
        
        # Obtener datos actuales
        marca = self.models_table.item(row, 0).text()
        modelo = self.models_table.item(row, 1).text()
        oid_contador = self.models_table.item(row, 2).text()
        oid_toner_actual = self.models_table.item(row, 3).text()
        oid_toner_maximo = self.models_table.item(row, 4).text()
        
        # Leer todo desde JSON directamente (evita leer el emoji '📝' de la tabla)
        data_actual = counter.load_json(display=False) or {}
        modelo_data_actual = data_actual.get("_modelos", {}).get(marca, {}).get(modelo, {})
        oid_modelo_toner = modelo_data_actual.get("oid_modelo_toner", "")
        toner_manual_actual = modelo_data_actual.get("toner_model_manual", "")
        tiene_manual = bool(toner_manual_actual)
        
        # Diálogo de edición
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("Editar Modelo")
        dialog.setGeometry(200, 200, 600, 480)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Marca:"))
        input_marca = QLineEdit()
        input_marca.setText(marca)
        input_marca.setReadOnly(True)
        layout.addWidget(input_marca)
        
        layout.addWidget(QLabel("Nombre del Modelo:"))
        input_modelo = QLineEdit()
        input_modelo.setText(modelo)
        input_modelo.setReadOnly(True)
        layout.addWidget(input_modelo)
        
        layout.addWidget(QLabel("OID Contador:"))
        input_oid_contador = QLineEdit()
        input_oid_contador.setText(oid_contador)
        layout.addWidget(input_oid_contador)
        
        layout.addWidget(QLabel("OID Tóner Actual (opcional):"))
        input_oid_toner_actual = QLineEdit()
        input_oid_toner_actual.setText(oid_toner_actual)
        layout.addWidget(input_oid_toner_actual)
        
        layout.addWidget(QLabel("OID Tóner Máximo (opcional):"))
        input_oid_toner_maximo = QLineEdit()
        input_oid_toner_maximo.setText(oid_toner_maximo)
        layout.addWidget(input_oid_toner_maximo)
        
        # OID Modelo Tóner / Entrada manual
        label_toner_model = QLabel("OID Modelo Tóner (deshabilitado — usando entrada manual):" if tiene_manual else "OID Modelo Tóner (opcional):")
        layout.addWidget(label_toner_model)
        input_oid_modelo_toner = QLineEdit()
        input_oid_modelo_toner.setText(oid_modelo_toner)
        input_oid_modelo_toner.setEnabled(not tiene_manual)
        if tiene_manual:
            input_oid_modelo_toner.setStyleSheet("background-color: #eeeeee; color: gray;")
        layout.addWidget(input_oid_modelo_toner)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #bdc3c7; margin: 2px 0px;")
        layout.addWidget(sep)
        
        chk_manual = QCheckBox("📝 Ingresar modelo de tóner manualmente (para impresoras que no lo publican por SNMP)")
        chk_manual.setStyleSheet("font-weight: bold; color: #e65100; padding: 2px;")
        chk_manual.setChecked(tiene_manual)
        layout.addWidget(chk_manual)
        
        label_manual = QLabel("Nombre del modelo de tóner:")
        label_manual.setVisible(tiene_manual)
        layout.addWidget(label_manual)
        input_toner_model_manual = QLineEdit()
        input_toner_model_manual.setPlaceholderText("Ej: TK-3182, TN-850, CF226A...")
        input_toner_model_manual.setText(toner_manual_actual)
        input_toner_model_manual.setVisible(tiene_manual)
        input_toner_model_manual.setStyleSheet("background-color: #fff8e1; border: 1px solid #e65100;")
        layout.addWidget(input_toner_model_manual)
        
        def toggle_toner_manual(checked):
            input_oid_modelo_toner.setEnabled(not checked)
            input_oid_modelo_toner.setStyleSheet("background-color: #eeeeee; color: gray;" if checked else "")
            label_toner_model.setText("OID Modelo Tóner (deshabilitado — usando entrada manual):" if checked else "OID Modelo Tóner (opcional):")
            label_manual.setVisible(checked)
            input_toner_model_manual.setVisible(checked)
        
        chk_manual.toggled.connect(toggle_toner_manual)
        
        button_layout = QHBoxLayout()
        btn_ok = QPushButton()
        btn_ok.setIcon(qta.icon('fa5s.check', color='white'))
        btn_ok.setText("  Guardar")
        btn_ok.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_cancel = QPushButton()
        btn_cancel.setIcon(qta.icon('fa5s.times', color='white'))
        btn_cancel.setText("  Cancelar")
        btn_cancel.setStyleSheet("background-color: #757575; color: white; font-weight: bold; padding: 8px;")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            oid_contador_new = input_oid_contador.text().strip()
            oid_toner_actual_new = input_oid_toner_actual.text().strip()
            oid_toner_maximo_new = input_oid_toner_maximo.text().strip()
            usar_manual = chk_manual.isChecked()
            oid_modelo_toner_new = "" if usar_manual else input_oid_modelo_toner.text().strip()
            toner_model_manual_new = input_toner_model_manual.text().strip() if usar_manual else ""
            
            # Validar
            if not oid_contador_new:
                QMessageBox.warning(self, "Error", "OID Contador es obligatorio")
                return
            
            if (oid_toner_actual_new and not oid_toner_maximo_new) or (oid_toner_maximo_new and not oid_toner_actual_new):
                QMessageBox.warning(
                    self,
                    "Error",
                    "OID Tóner Actual y OID Tóner Máximo deben ingresarse juntos o no ingresarse"
                )
                return
            
            if usar_manual and not toner_model_manual_new:
                QMessageBox.warning(self, "Error", "Ingresa el nombre manual del modelo de tóner")
                return
            
            # Actualizar en JSON
            data = counter.load_json(display=False)
            if data and "_modelos" in data and marca in data["_modelos"] and modelo in data["_modelos"][marca]:
                nuevo_modelo_data = {
                    "oid_contador": oid_contador_new,
                    "oid_nombre": oid_contador_new,
                    "oid_toner_actual": oid_toner_actual_new,
                    "oid_toner_maximo": oid_toner_maximo_new,
                    "oid_modelo_toner": oid_modelo_toner_new,
                }
                if usar_manual:
                    nuevo_modelo_data["toner_model_manual"] = toner_model_manual_new
                
                data["_modelos"][marca][modelo] = nuevo_modelo_data
                
                try:
                    with open(counter.JSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    
                    QMessageBox.information(self, "Éxito", "Modelo actualizado correctamente")
                    self.load_models()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
    
