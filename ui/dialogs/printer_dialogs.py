# Mixin: diálogos Agregar Impresora y Editar Impresora.
import json
import logging

import qtawesome as qta
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QMessageBox, QDialog, QComboBox
)
from PyQt5.QtCore import Qt

import core.snmp_engine as counter

logger = logging.getLogger(__name__)



class PrinterDialogsMixin:
    """Diálogos de gestión de impresoras — se mezcla con PrinterDashboard."""

    def add_new_printer(self):
        """Dialogo para agregar nueva impresora con selección de modelo"""
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("Agregar Nueva Impresora")
        dialog.setGeometry(200, 200, 550, 650)
        
        layout = QVBoxLayout()
        
        # Obtener datos de modelos
        data = counter.load_json(display=False)
        modelos_dict = data.get("_modelos", {}) if data else {}
        marcas = sorted(modelos_dict.keys())
        
        # SECCIÓN 1: SELECCIÓN DE MODELO
        layout.addWidget(QLabel("📦 Seleccionar Modelo Predefinido (Opcional):"))
        
        # Selector de Marca
        layout.addWidget(QLabel("Marca:"))
        combo_marca = QComboBox()
        combo_marca.addItem("-- Selecciona una marca --", None)
        for marca in marcas:
            combo_marca.addItem(marca, marca)
        layout.addWidget(combo_marca)
        
        # Selector de Modelo
        layout.addWidget(QLabel("Modelo:"))
        combo_modelo = QComboBox()
        combo_modelo.addItem("-- Selecciona un modelo --", None)
        layout.addWidget(combo_modelo)
        
        # Variables para almacenar OIDs del modelo seleccionado
        selected_model_data = {}
        
        def update_modelos_combo():
            """Actualiza los modelos según la marca seleccionada"""
            nonlocal selected_model_data
            selected_model_data = {}
            combo_modelo.clear()
            combo_modelo.addItem("-- Selecciona un modelo --", None)
            
            marca_seleccionada = combo_marca.currentData()
            if marca_seleccionada and marca_seleccionada in modelos_dict:
                for nombre_modelo in sorted(modelos_dict[marca_seleccionada].keys()):
                    combo_modelo.addItem(nombre_modelo, nombre_modelo)
        
        def on_modelo_selected():
            """Se ejecuta cuando se selecciona un modelo"""
            nonlocal selected_model_data
            marca_seleccionada = combo_marca.currentData()
            modelo_seleccionado = combo_modelo.currentData()
            
            if marca_seleccionada and modelo_seleccionado:
                if marca_seleccionada in modelos_dict and modelo_seleccionado in modelos_dict[marca_seleccionada]:
                    selected_model_data = modelos_dict[marca_seleccionada][modelo_seleccionado].copy()
                    
                    # Auto-rellenar campos OID
                    input_brand.setText(marca_seleccionada)
                    input_oid.setText(selected_model_data.get("oid_contador", ""))
                    input_toner_current.setText(selected_model_data.get("oid_toner_actual", ""))
                    input_toner_max.setText(selected_model_data.get("oid_toner_maximo", ""))
                    input_toner_model_oid.setText(selected_model_data.get("oid_modelo_toner", ""))
                    
                    # Si el modelo tiene toner manual, mostrarlo en el campo informativo
                    manual_val = selected_model_data.get("toner_model_manual", "")
                    if manual_val:
                        label_oid_toner_model.setText("Modelo de Tóner (entrada manual):")
                        label_oid_toner_model.setStyleSheet("color: #e65100; font-weight: bold;")
                        input_toner_model_oid.setText(manual_val)
                        input_toner_model_oid.setStyleSheet(
                            "background-color: #fff8e1; color: #e65100; border: 1px solid #e65100;"
                        )
                        input_toner_model_oid.setToolTip(f"Valor ingresado manualmente: {manual_val}")
                    else:
                        label_oid_toner_model.setText("OID Modelo de Tóner (auto desde modelo):")
                        label_oid_toner_model.setStyleSheet("")
                        input_toner_model_oid.setText(selected_model_data.get("oid_modelo_toner", ""))
                        input_toner_model_oid.setStyleSheet(
                            "background-color: #f5f5f5; color: #757575; border: 1px solid #e0e0e0;"
                        )
                        input_toner_model_oid.setToolTip("")
            else:
                # Limpiar campos si no hay modelo seleccionado
                label_oid_toner_model.setText("OID Modelo de Tóner (auto desde modelo):")
                label_oid_toner_model.setStyleSheet("")
                input_brand.clear()
                input_oid.clear()
                input_toner_current.clear()
                input_toner_max.clear()
                input_toner_model_oid.clear()
                input_toner_model_oid.setStyleSheet(
                    "background-color: #f5f5f5; color: #757575; border: 1px solid #e0e0e0;"
                )
                input_toner_model_oid.setToolTip("")
        
        combo_marca.currentIndexChanged.connect(update_modelos_combo)
        combo_modelo.currentIndexChanged.connect(on_modelo_selected)
        
        # SECCIÓN 2: ENTRADA MANUAL
        layout.addWidget(QLabel("\n📝 Datos de la Impresora:"))
        
        # Marca (auto-rellenada por modelo, editable)
        layout.addWidget(QLabel("Marca:"))
        input_brand = QLineEdit()
        layout.addWidget(input_brand)
        
        # IP (obligatorio)
        layout.addWidget(QLabel("IP:"))
        input_ip = QLineEdit()
        layout.addWidget(input_ip)
        
        # Nombre/Ubicación
        layout.addWidget(QLabel("Nombre/Ubicación:"))
        input_name = QLineEdit()
        layout.addWidget(input_name)
        
        # OID Contador (auto-rellenado por modelo, no editable)
        oid_readonly_style = "background-color: #f5f5f5; color: #757575; border: 1px solid #e0e0e0;"
        
        layout.addWidget(QLabel("OID para Contador (auto desde modelo):"))
        input_oid = QLineEdit()
        input_oid.setPlaceholderText("Auto-rellenado al seleccionar modelo")
        input_oid.setReadOnly(True)
        input_oid.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_oid)
        
        # OID Nivel Tóner Actual
        layout.addWidget(QLabel("OID Nivel Tóner Actual (auto desde modelo):"))
        input_toner_current = QLineEdit()
        input_toner_current.setPlaceholderText("Auto-rellenado al seleccionar modelo")
        input_toner_current.setReadOnly(True)
        input_toner_current.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_toner_current)
        
        # OID Nivel Tóner Máximo
        layout.addWidget(QLabel("OID Nivel Tóner Máximo (auto desde modelo):"))
        input_toner_max = QLineEdit()
        input_toner_max.setPlaceholderText("Auto-rellenado al seleccionar modelo")
        input_toner_max.setReadOnly(True)
        input_toner_max.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_toner_max)
        
        # OID Modelo de Tóner / indicador de entrada manual
        label_oid_toner_model = QLabel("OID Modelo de Tóner (auto desde modelo):")
        layout.addWidget(label_oid_toner_model)
        input_toner_model_oid = QLineEdit()
        input_toner_model_oid.setPlaceholderText("Auto-rellenado al seleccionar modelo")
        input_toner_model_oid.setReadOnly(True)
        input_toner_model_oid.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_toner_model_oid)
        
        # Botones
        button_layout = QHBoxLayout()
        btn_ok = QPushButton()
        btn_ok.setIcon(qta.icon('fa5s.check', color='white'))
        btn_ok.setText("  Agregar")
        btn_ok.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_cancel = QPushButton()
        btn_cancel.setIcon(qta.icon('fa5s.times', color='white'))
        btn_cancel.setText("  Cancelar")
        btn_cancel.setStyleSheet("background-color: #757575; color: white; font-weight: bold; padding: 8px;")

        def on_agregar_clicked():
            """Valida que se haya seleccionado marca y modelo antes de aceptar"""
            marca_sel = combo_marca.currentData()
            modelo_sel = combo_modelo.currentData()
            if not marca_sel or not modelo_sel:
                QMessageBox.warning(
                    dialog,
                    "Selección requerida",
                    "Debes seleccionar una Marca y un Modelo para agregar la impresora.\n\n"
                    "Si no existen, créalos desde la pestaña \"Gestión de Modelos\"."
                )
                return
            dialog.accept()

        btn_ok.clicked.connect(on_agregar_clicked)
        btn_cancel.clicked.connect(dialog.reject)
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            brand = input_brand.text().strip()
            ip = input_ip.text().strip()
            name = input_name.text().strip()
            oid = input_oid.text().strip() or "1.3.6.1.2.1.43.10.2.1.5.1.1"
            toner_current_oid = input_toner_current.text().strip()
            toner_max_oid = input_toner_max.text().strip()
            toner_model_oid = input_toner_model_oid.text().strip()
            
            # Obtener modelo seleccionado
            modelo_seleccionado = combo_modelo.currentData()
            
            # Validar
            if not brand or not ip:
                QMessageBox.warning(self, "Error", "Marca e IP son requeridos")
                return
            
            # VALIDACIÓN CRÍTICA: OIDs de tóner deben ir juntos
            if (toner_current_oid and not toner_max_oid) or (toner_max_oid and not toner_current_oid):
                QMessageBox.warning(
                    self, 
                    "Error", 
                    "❌ OIDs de Tóner incompletos\n\n"
                    "Si ingresas OID Nivel Tóner Actual, DEBES ingresar también OID Nivel Tóner Máximo\n\n"
                    "Ambos OIDs son obligatorios si deseas monitorear el nivel de tóner."
                )
                return
            
            # Cargar JSON
            data = counter.load_json(display=False)
            if data is None:
                QMessageBox.warning(self, "Error", "No se pudo cargar printers.json")
                return
            
            # Buscar marca existente con lookup case-insensitive
            SKIP_KEYS = {"_modelos", "_printer_order", "_config"}
            brand_key_existing = next(
                (k for k in data if k not in SKIP_KEYS
                 and isinstance(data[k], dict) and "printer" in data[k]
                 and k.lower() == brand.lower()), None
            )
            
            if brand_key_existing:
                # Usar la clave exacta ya existente (preservar capitalización original)
                brand_key = brand_key_existing
            else:
                # Marca nueva: crearla
                brand_key = brand
                data[brand_key] = {
                    "OID": {
                        "counter": oid,
                        "name": oid,
                        "toner_current": toner_current_oid,
                        "toner_max": toner_max_oid,
                        "toner_model": toner_model_oid
                    },
                    "printer": []
                }
            
            # Agregar impresora CON el modelo asignado
            printer_data = {
                "ip": ip,
                "custom_name": name if name else ip
            }
            if modelo_seleccionado:
                printer_data["modelo_asignado"] = modelo_seleccionado
            
            data[brand_key]["printer"].append(printer_data)
            
            # Actualizar _printer_order para incluir la nueva impresora al final
            printer_order = data.get("_printer_order", [])
            if printer_order:
                # Reconstruir desde el orden existente + nueva impresora
                printer_order.append({"brand": brand_key, "ip": ip})
                data["_printer_order"] = printer_order
            # Si no hay _printer_order aún, se creará la próxima vez que el usuario guarde el orden
            
            # Guardar
            try:
                with open(counter.JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                QMessageBox.information(self, "Éxito", f"Impresora {brand_key} {ip} agregada correctamente")
                self.refresh_table_from_json()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
    
    def edit_printer(self):
        """Edita una impresora existente (marca, modelo, OIDs)"""
        # Obtener fila seleccionada
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona una impresora para editar")
            return
        
        # Obtener datos de la fila con guards contra None
        def _get_cell(r, c):
            item = self.table.item(r, c)
            return item.text() if item else ""
        
        marca_actual = _get_cell(row, 0)
        modelo_actual = _get_cell(row, 1)
        ip_actual = _get_cell(row, 2)
        name_actual = _get_cell(row, 4)
        if modelo_actual == "--":
            modelo_actual = ""
        
        if not ip_actual:
            QMessageBox.warning(self, "Error", "No se pudo obtener la IP de la impresora")
            return
        
        # Cargar datos de modelos
        data = counter.load_json(display=False)
        if data is None:
            QMessageBox.warning(self, "Error", "No se pudo cargar printers.json")
            return
        modelos_dict = data.get("_modelos", {})
        # Las claves de _modelos pueden estar en minúscula, crear mapa normalizado
        modelos_dict_lower = {k.lower(): v for k, v in modelos_dict.items()}
        marcas = sorted(modelos_dict.keys())
        
        # Crear diálogo de edición
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Editar Impresora - {marca_actual} ({ip_actual})")
        dialog.setGeometry(200, 200, 550, 650)
        
        layout = QVBoxLayout()
        
        # SECCIÓN 1: SELECCIÓN DE MODELO
        layout.addWidget(QLabel("📦 Seleccionar/Cambiar Modelo:"))
        
        # Selector de Marca
        layout.addWidget(QLabel("Marca:"))
        combo_marca = QComboBox()
        combo_marca.addItem("-- Selecciona una marca --", None)
        for marca in marcas:
            combo_marca.addItem(marca, marca)
        layout.addWidget(combo_marca)
        
        # Selector de Modelo
        layout.addWidget(QLabel("Modelo:"))
        combo_modelo = QComboBox()
        combo_modelo.addItem("-- Selecciona un modelo --", None)
        layout.addWidget(combo_modelo)
        
        # SECCIÓN 2: DATOS DE LA IMPRESORA (definidos antes de conectar signals)
        layout.addWidget(QLabel("\n📝 Datos de la Impresora:"))
        
        layout.addWidget(QLabel("Marca:"))
        input_brand = QLineEdit(marca_actual)
        layout.addWidget(input_brand)
        
        layout.addWidget(QLabel("IP:"))
        input_ip = QLineEdit(ip_actual)
        input_ip.setPlaceholderText("Ej: 192.168.1.100")
        layout.addWidget(input_ip)
        
        layout.addWidget(QLabel("Nombre/Ubicación:"))
        input_name = QLineEdit(name_actual)
        layout.addWidget(input_name)
        
        oid_readonly_style = "background-color: #f5f5f5; color: #757575; border: 1px solid #e0e0e0;"
        
        layout.addWidget(QLabel("OID para Contador (auto desde modelo):"))
        input_oid = QLineEdit()
        marca_key = next((k for k in data if k.lower() == marca_actual.lower() and k != "_modelos"), None)
        if marca_key and "OID" in data[marca_key]:
            input_oid.setText(data[marca_key]["OID"].get("counter", ""))
        input_oid.setReadOnly(True)
        input_oid.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_oid)
        
        layout.addWidget(QLabel("OID Nivel Tóner Actual (auto desde modelo):"))
        input_toner_current = QLineEdit()
        if marca_key and "OID" in data[marca_key]:
            input_toner_current.setText(data[marca_key]["OID"].get("toner_current", ""))
        input_toner_current.setReadOnly(True)
        input_toner_current.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_toner_current)
        
        layout.addWidget(QLabel("OID Nivel Tóner Máximo (auto desde modelo):"))
        input_toner_max = QLineEdit()
        if marca_key and "OID" in data[marca_key]:
            input_toner_max.setText(data[marca_key]["OID"].get("toner_max", ""))
        input_toner_max.setReadOnly(True)
        input_toner_max.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_toner_max)
        
        label_oid_toner_model = QLabel("OID Modelo de Tóner (auto desde modelo):")
        layout.addWidget(label_oid_toner_model)
        input_toner_model_oid = QLineEdit()
        if marca_key and "OID" in data[marca_key]:
            input_toner_model_oid.setText(data[marca_key]["OID"].get("toner_model", ""))
        input_toner_model_oid.setReadOnly(True)
        input_toner_model_oid.setStyleSheet(oid_readonly_style)
        layout.addWidget(input_toner_model_oid)
        
        selected_model_data = {}
        
        def update_modelos_combo():
            """Actualiza los modelos según la marca seleccionada"""
            nonlocal selected_model_data
            selected_model_data = {}
            combo_modelo.clear()
            combo_modelo.addItem("-- Selecciona un modelo --", None)
            
            marca_sel = combo_marca.currentData()
            if marca_sel:
                modelos_marca = modelos_dict.get(marca_sel) or modelos_dict_lower.get(marca_sel.lower(), {})
                for nombre_modelo in sorted(modelos_marca.keys()):
                    combo_modelo.addItem(nombre_modelo, nombre_modelo)
                # Pre-seleccionar el modelo asignado actualmente
                if modelo_actual:
                    for i in range(combo_modelo.count()):
                        if combo_modelo.itemData(i) == modelo_actual:
                            combo_modelo.setCurrentIndex(i)
                            break
        
        def on_modelo_selected():
            """Rellena los campos OID cuando se elige un modelo del listado"""
            nonlocal selected_model_data
            marca_sel = combo_marca.currentData()
            modelo_sel = combo_modelo.currentData()
            if not (marca_sel and modelo_sel):
                return
            modelos_marca = modelos_dict.get(marca_sel) or modelos_dict_lower.get(marca_sel.lower(), {})
            if modelo_sel in modelos_marca:
                selected_model_data = modelos_marca[modelo_sel].copy()
                input_brand.setText(marca_sel)
                input_oid.setText(selected_model_data.get("oid_contador", ""))
                input_toner_current.setText(selected_model_data.get("oid_toner_actual", ""))
                input_toner_max.setText(selected_model_data.get("oid_toner_maximo", ""))
                
                # Si el modelo tiene toner manual, mostrarlo con estilo naranja
                manual_val = selected_model_data.get("toner_model_manual", "")
                if manual_val:
                    label_oid_toner_model.setText("Modelo de Tóner (entrada manual):")
                    label_oid_toner_model.setStyleSheet("color: #e65100; font-weight: bold;")
                    input_toner_model_oid.setText(manual_val)
                    input_toner_model_oid.setStyleSheet(
                        "background-color: #fff8e1; color: #e65100; border: 1px solid #e65100;"
                    )
                    input_toner_model_oid.setToolTip(f"Valor ingresado manualmente: {manual_val}")
                else:
                    label_oid_toner_model.setText("OID Modelo de Tóner (auto desde modelo):")
                    label_oid_toner_model.setStyleSheet("")
                    input_toner_model_oid.setText(selected_model_data.get("oid_modelo_toner", ""))
                    input_toner_model_oid.setStyleSheet(oid_readonly_style)
                    input_toner_model_oid.setToolTip("")
        
        # Conectar signals DESPUÉS de definir todos los inputs
        combo_marca.currentIndexChanged.connect(update_modelos_combo)
        combo_modelo.currentIndexChanged.connect(on_modelo_selected)
        
        # Pre-seleccionar marca actual (insensible a mayúsculas) y llenar modelos
        for i in range(combo_marca.count()):
            item_data = combo_marca.itemData(i)
            if item_data and item_data.lower() == marca_actual.lower():
                combo_marca.setCurrentIndex(i)  # Esto dispara update_modelos_combo
                break
        else:
            update_modelos_combo()  # Forzar llenado si no se preseleccionó marca
        
        # Botones
        button_layout = QHBoxLayout()
        btn_ok = QPushButton()
        btn_ok.setIcon(qta.icon('fa5s.check', color='white'))
        btn_ok.setText("  Guardar Cambios")
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
            brand_new = input_brand.text().strip()
            name_new = input_name.text().strip()
            oid_new = input_oid.text().strip() or "1.3.6.1.2.1.43.10.2.1.5.1.1"
            toner_current_oid_new = input_toner_current.text().strip()
            toner_max_oid_new = input_toner_max.text().strip()
            toner_model_oid_new = input_toner_model_oid.text().strip()
            modelo_seleccionado = combo_modelo.currentData()
            
            # Validar
            if not brand_new:
                QMessageBox.warning(self, "Error", "Marca es requerida")
                return
            
            # VALIDACIÓN CRÍTICA: OIDs de tóner deben ir juntos
            if (toner_current_oid_new and not toner_max_oid_new) or (toner_max_oid_new and not toner_current_oid_new):
                QMessageBox.warning(
                    self, 
                    "Error", 
                    "❌ OIDs de Tóner incompletos\n\n"
                    "Si ingresas OID Nivel Tóner Actual, DEBES ingresar también OID Nivel Tóner Máximo"
                )
                return
            
            # Cargar JSON
            data = counter.load_json(display=False)
            if data is None:
                QMessageBox.warning(self, "Error", "No se pudo cargar printers.json")
                return
            
            SKIP_KEYS = {"_modelos", "_printer_order", "_config"}
            
            # Buscar clave real de la marca actual en el JSON (case-insensitive)
            marca_actual_key = next(
                (k for k in data if k not in SKIP_KEYS
                 and isinstance(data[k], dict) and "printer" in data[k]
                 and k.lower() == marca_actual.lower()), None
            )
            
            # Si cambió la marca, mover la impresora a la nueva marca
            if brand_new.lower() != marca_actual.lower():
                # Eliminar de marca anterior (clave real del JSON)
                if marca_actual_key:
                    data[marca_actual_key]["printer"] = [
                        p for p in data[marca_actual_key]["printer"]
                        if p.get("ip") != ip_actual
                    ]
                    if not data[marca_actual_key]["printer"]:
                        del data[marca_actual_key]
                
                # Buscar si ya existe la nueva marca (case-insensitive)
                brand_new_key = next(
                    (k for k in data if k not in SKIP_KEYS
                     and isinstance(data[k], dict) and "printer" in data[k]
                     and k.lower() == brand_new.lower()), None
                )
                
                if brand_new_key is None:
                    brand_new_key = brand_new
                    data[brand_new_key] = {
                        "OID": {
                            "counter": oid_new, "name": oid_new,
                            "toner_current": toner_current_oid_new,
                            "toner_max": toner_max_oid_new,
                            "toner_model": toner_model_oid_new
                        },
                        "printer": []
                    }
                else:
                    if "OID" not in data[brand_new_key]:
                        data[brand_new_key]["OID"] = {}
                    data[brand_new_key]["OID"].update({
                        "counter": oid_new, "name": oid_new,
                        "toner_current": toner_current_oid_new,
                        "toner_max": toner_max_oid_new,
                        "toner_model": toner_model_oid_new
                    })
                
                printer_data = {"ip": ip_actual, "custom_name": name_new}
                if modelo_seleccionado:
                    printer_data["modelo_asignado"] = modelo_seleccionado
                data[brand_new_key]["printer"].append(printer_data)
                
                # CRÍTICO: Actualizar _printer_order con la nueva marca
                if "_printer_order" in data:
                    for entry in data["_printer_order"]:
                        if (entry.get("ip") == ip_actual and
                                entry.get("brand", "").lower() == marca_actual.lower()):
                            entry["brand"] = brand_new_key
                            break
            else:
                # Misma marca — usar la clave real del JSON
                bk = marca_actual_key or brand_new
                if bk in data and "OID" in data[bk]:
                    data[bk]["OID"].update({
                        "counter": oid_new, "name": oid_new,
                        "toner_current": toner_current_oid_new,
                        "toner_max": toner_max_oid_new,
                        "toner_model": toner_model_oid_new
                    })
                if bk in data and "printer" in data[bk]:
                    for printer in data[bk]["printer"]:
                        if printer.get("ip") == ip_actual:
                            printer["custom_name"] = name_new
                            if modelo_seleccionado:
                                printer["modelo_asignado"] = modelo_seleccionado
                            break
            
            # Guardar
            try:
                with open(counter.JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                modelo_msg = f" con modelo '{modelo_seleccionado}'" if modelo_seleccionado else ""
                QMessageBox.information(self, "Éxito", f"Impresora actualizada correctamente{modelo_msg}")
                self.load_models()  # Actualizar tabla de modelos si fue modificada
                self.refresh_table_from_json()
            except Exception as e:
                logger.error(f"ERROR en edit_printer al guardar: {type(e).__name__}: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
    
