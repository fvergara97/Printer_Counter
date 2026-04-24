# Mixin: pestaña Dashboard (tabla principal, SNMP, edición, export).
import sys
import json
import logging
import subprocess
import shutil
import os
from pathlib import Path
from datetime import datetime

import qtawesome as qta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
    QGroupBox, QMessageBox, QFileDialog, QProgressBar,
    QHeaderView, QDialog, QCheckBox
)
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtGui import QColor, QDesktopServices

import core.snmp_engine as counter
from core.config import config as app_config

logger = logging.getLogger(__name__)
from ui.workers import SNMPWorker



class DashboardMixin:
    # Pestaña Dashboard — se mezcla con PrinterDashboard.

    def create_control_panel(self):
        # Crea panel de control con botones principales (tamaño uniforme)
        group = QGroupBox("Control")
        main_layout = QVBoxLayout()
        
        # Primera fila: Botones principales
        layout_row1 = QHBoxLayout()
        
        # Estilo uniforme para todos los botones
        button_style_orange = "background-color: #FF9800; color: white; font-weight: bold; padding: 10px; min-width: 150px;"
        button_style_green = "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; min-width: 150px;"
        button_style_gray = "background-color: #607D8B; color: white; font-weight: bold; padding: 10px; min-width: 150px;"
        button_style_blue = "background-color: #2196F3; color: white; font-weight: bold; padding: 10px; min-width: 150px;"
        # Botón Agregar nueva impresora
        btn_add = QPushButton()
        btn_add.setIcon(qta.icon('fa5s.plus', color='white'))
        btn_add.setText("  Agregar Nueva")
        btn_add.setStyleSheet(button_style_orange)
        btn_add.clicked.connect(self.add_new_printer)
        layout_row1.addWidget(btn_add)
        
        # Botón Ejecutar SNMP
        btn_fetch = QPushButton()
        btn_fetch.setIcon(qta.icon('fa5s.play-circle', color='white'))
        btn_fetch.setText("  Ejecutar Consulta")
        btn_fetch.setStyleSheet(button_style_green)
        btn_fetch.clicked.connect(self.execute_snmp_query)
        layout_row1.addWidget(btn_fetch)
        
        # Botón Refrescar Tabla
        btn_refresh = QPushButton()
        btn_refresh.setIcon(qta.icon('fa5s.sync-alt', color='white'))
        btn_refresh.setText("  Refrescar")
        btn_refresh.setStyleSheet(button_style_gray)
        btn_refresh.clicked.connect(self.refresh_table_from_json)
        layout_row1.addWidget(btn_refresh)
        
        # Botón Editar — abre diálogo de edición de la impresora seleccionada
        btn_edit = QPushButton()
        btn_edit.setIcon(qta.icon('fa5s.edit', color='white'))
        btn_edit.setText("  Editar")
        btn_edit.setStyleSheet(button_style_blue)
        btn_edit.clicked.connect(self.edit_printer)
        layout_row1.addWidget(btn_edit)
        

        
        main_layout.addLayout(layout_row1)
        
        # Segunda fila: Botones pequeños para mover
        layout_row2 = QHBoxLayout()
        layout_row2.addWidget(QLabel("Reordenar:"))
        
        # Botones pequeños para mover (solo iconos, sin bordes)
        btn_move_up = QPushButton()
        btn_move_up.setIcon(qta.icon('fa5s.arrow-up', color='#2196F3'))
        btn_move_up.setStyleSheet("background-color: transparent; border: none; padding: 0px; margin: 0px;")
        btn_move_up.setMaximumWidth(30)
        btn_move_up.setMaximumHeight(25)
        btn_move_up.setCursor(Qt.PointingHandCursor)
        btn_move_up.clicked.connect(self.move_row_up)
        layout_row2.addWidget(btn_move_up)
        
        btn_move_down = QPushButton()
        btn_move_down.setIcon(qta.icon('fa5s.arrow-down', color='#2196F3'))
        btn_move_down.setStyleSheet("background-color: transparent; border: none; padding: 0px; margin: 0px; font-size: 16px;")
        btn_move_down.setMaximumWidth(30)
        btn_move_down.setMaximumHeight(25)
        btn_move_down.setCursor(Qt.PointingHandCursor)
        btn_move_down.clicked.connect(self.move_row_down)
        layout_row2.addWidget(btn_move_down)
        
        # Botón Guardar orden - inicia deshabilitado (gris), se activa al mover filas
        self.btn_save_order = QPushButton()
        self.btn_save_order.setIcon(qta.icon('fa5s.save', color='#BDBDBD'))  # Gris = deshabilitado
        self.btn_save_order.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; padding: 2px; }"
            "QPushButton:disabled { opacity: 0.4; }"
        )
        self.btn_save_order.setIconSize(QSize(16, 16))
        self.btn_save_order.setMaximumWidth(28)
        self.btn_save_order.setMaximumHeight(25)
        self.btn_save_order.setCursor(Qt.PointingHandCursor)
        self.btn_save_order.setEnabled(False)
        self.btn_save_order.setToolTip("Guardar orden actual")
        self.btn_save_order.clicked.connect(self.save_names)
        layout_row2.addWidget(self.btn_save_order)
        
        layout_row2.addStretch()
        
        # Buscador / Filtro en tiempo real
        lbl_buscar = QLabel("Buscar:")
        layout_row2.addWidget(lbl_buscar)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filtrar por marca, modelo, IP, ubicación...")
        self.search_input.setMaximumWidth(260)
        self.search_input.setMinimumWidth(180)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            "QLineEdit { border: 1px solid #90CAF9; border-radius: 4px; padding: 3px 6px; }"
            "QLineEdit:focus { border: 1px solid #1565C0; }"
        )
        self.search_input.textChanged.connect(self.filter_table)
        layout_row2.addWidget(self.search_input)
        
        main_layout.addLayout(layout_row2)
        
        group.setLayout(main_layout)
        return group
    def execute_snmp_query(self):
        """Ejecuta la consulta SNMP en un thread separado (optimizado con paralelismo)"""
        if self.snmp_worker is not None and self.snmp_worker.isRunning():
            QMessageBox.warning(self, "Advertencia", "Ya hay una consulta en progreso.")
            return
        
        # Mostrar el modo SNMP que se va a usar
        mode_text = "Paralelo" if counter.SNMP_MODE_PARALLEL else "Secuencial"
        self.status_label.setText(f"Consultando SNMP (modo: {mode_text})...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        
        self.snmp_worker = SNMPWorker(self.loop)
        self.snmp_worker.data_ready.connect(self.on_data_ready)
        self.snmp_worker.error.connect(self.on_snmp_error)
        self.snmp_worker.finished.connect(self.on_snmp_finished)
        self.snmp_worker.start()
    
    def filter_table(self, text=None):
        """Filtra las filas de la tabla según el texto buscado (todas las columnas)"""
        search_text = (text if text is not None else self.search_input.text()).strip().lower()
        for row in range(self.table.rowCount()):
            match = False
            if not search_text:
                match = True
            else:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        match = True
                        break
            self.table.setRowHidden(row, not match)

    def on_data_ready(self, data):
        """Se llama cuando los datos SNMP están listos"""
        self.current_data = data
        self.populate_table(data)
    
    def on_snmp_error(self, error_msg):
        """Se llama cuando hay un error SNMP"""
        QMessageBox.critical(self, "Error SNMP", error_msg)
    
    def on_snmp_finished(self):
        """Se llama cuando la consulta SNMP ha terminado"""
        mode_text = "Paralelo" if counter.SNMP_MODE_PARALLEL else "Secuencial"
        self.status_label.setText(f"Consulta SNMP completada ✓ (modo: {mode_text})")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.progress_bar.setVisible(False)
    
    def populate_table(self, data):
        """Llena la tabla con los datos SNMP"""
        self.table.setRowCount(0)
        row = 0
        
        # Usar el orden guardado en JSON si existe (soporta cross-brand ordering)
        try:
            json_data = counter.load_json(display=False) or {}
            printer_order = json_data.get("_printer_order", [])
        except Exception:
            printer_order = []
        
        if printer_order:
            # Construir lista ordenada desde los resultados SNMP
            ordered = []
            seen_ips = set()
            for entry in printer_order:
                b = entry.get("brand", "")
                ip_e = entry.get("ip", "")
                bk = next((k for k in data if k not in ("_modelos", "_printer_order", "_config") and k.lower() == b.lower()), None)
                if not bk:
                    continue
                p = next((pr for pr in data[bk] if pr.get("ip", "") == ip_e), None)
                if p:
                    ordered.append((bk, p))
                    seen_ips.add(ip_e)
            # Añadir impresoras nuevas no incluidas en _printer_order
            for bk, printers in data.items():
                if bk in ("_modelos", "_printer_order", "_config") or not isinstance(printers, list):
                    continue
                for p in printers:
                    if p.get("ip", "") not in seen_ips:
                        ordered.append((bk, p))
        else:
            ordered = []
            for bk, printers in data.items():
                if bk in ("_modelos", "_printer_order", "_config") or not isinstance(printers, list):
                    continue
                for p in printers:
                    ordered.append((bk, p))
        
        for brand, printer in ordered:
                self.table.insertRow(row)
                
                # [0] Marca
                item_brand = QTableWidgetItem(brand)
                item_brand.setFlags(item_brand.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, item_brand)
                
                # [1] Modelo Asignado (no editable)
                modelo_asignado = printer.get("modelo_asignado", "")
                item_modelo = QTableWidgetItem(modelo_asignado if modelo_asignado else "--")
                item_modelo.setFlags(item_modelo.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 1, item_modelo)
                
                # [2] IP — Clickeable para abrir en navegador
                item_ip = QTableWidgetItem(printer.get("ip", ""))
                item_ip.setFlags(item_ip.flags() & ~Qt.ItemIsEditable)
                item_ip.setForeground(QColor("#1565C0"))
                item_ip.setToolTip(f"🌐 Clic para abrir http://{printer.get('ip', '')} en el navegador")
                self.table.setItem(row, 2, item_ip)
                
                # [3] Estado
                counter_val = printer.get("counter", "N/A")
                # Verificar si hay error, exception o valores inválidos
                counter_str = str(counter_val).lower()
                has_error = any(keyword in counter_str for keyword in ["error", "exception", "bad", "timeout", "unreachable", "unknown"])
                
                if has_error:
                    item_status = QTableWidgetItem("✗ No disponible")
                    item_status.setForeground(QColor("red"))
                else:
                    item_status = QTableWidgetItem("✓ OK")
                    item_status.setForeground(QColor("green"))
                
                item_status.setFlags(item_status.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 3, item_status)
                
                # [4] Ubicación/Nombre (Editable)
                item_name = QTableWidgetItem(printer.get("custom_name", ""))
                self.table.setItem(row, 4, item_name)
                
                # [5] Contador
                item_counter = QTableWidgetItem(str(counter_val))
                item_counter.setFlags(item_counter.flags() & ~Qt.ItemIsEditable)
                if "Error" in str(counter_val) or "Exception" in str(counter_val):
                    item_counter.setForeground(QColor("red"))
                self.table.setItem(row, 5, item_counter)
                
                # [6] Nivel del Tóner - desde datos SNMP calculados
                toner_level = printer.get("toner_level", "--")
                item_toner = QTableWidgetItem(str(toner_level))
                item_toner.setFlags(item_toner.flags() & ~Qt.ItemIsEditable)
                
                # Colorear según el nivel si es un porcentaje
                if toner_level != "--" and "%" in str(toner_level):
                    try:
                        percentage = int(toner_level.rstrip("%"))
                        if percentage < 20:
                            item_toner.setForeground(QColor("red"))
                        elif percentage < 50:
                            item_toner.setForeground(QColor("orange"))
                        else:
                            item_toner.setForeground(QColor("green"))
                    except:
                        pass
                
                self.table.setItem(row, 6, item_toner)
                
                # [7] Modelo de Tóner - desde datos SNMP, o fallback a valor manual del JSON
                toner_model = printer.get("toner_model", "")
                toner_model_str = str(toner_model) if toner_model else "--"
                if toner_model_str.startswith(("Exception:", "Error:")):
                    toner_model_str = "--"
                
                # Fallback: si sigue siendo --, buscar toner_model_manual en _modelos del JSON
                if toner_model_str == "--":
                    try:
                        json_data_fb = counter.load_json(display=False) or {}
                        modelos_dict = json_data_fb.get("_modelos", {})
                        brand_lower = brand.lower()
                        modelos_marca = next(
                            (v for k, v in modelos_dict.items() if k.lower() == brand_lower), {}
                        )
                        
                        if modelo_asignado:
                            # Buscar modelo específico asignado
                            modelo_lower = modelo_asignado.lower()
                            modelo_data_fb = next(
                                (v for k, v in modelos_marca.items() if k.lower() == modelo_lower), {}
                            )
                            manual_val = modelo_data_fb.get("toner_model_manual", "")
                            if manual_val:
                                toner_model_str = manual_val
                        else:
                            # Sin modelo asignado: buscar en TODOS los modelos de la marca
                            for nombre_modelo, modelo_data_fb in modelos_marca.items():
                                manual_val = modelo_data_fb.get("toner_model_manual", "")
                                if manual_val:
                                    toner_model_str = manual_val
                                    break
                    except Exception:
                        pass
                
                item_toner_model = QTableWidgetItem(toner_model_str)
                item_toner_model.setFlags(item_toner_model.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 7, item_toner_model)
                
                row += 1
        
        # Re-aplicar filtro de búsqueda si hay texto activo
        self.filter_table()
    
    def refresh_table_from_json(self):
        """Recarga la tabla desde printers.json sin hacer consultas SNMP"""
        data = counter.load_json(display=False)
        if data is None:
            QMessageBox.warning(self, "Error", "No se pudo cargar printers.json")
            return
        
        self.table.setRowCount(0)
        row = 0
        
        if not data:
            self.status_label.setText("No hay impresoras. Usa 'Agregar Nueva' para crear una.")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            return
        
        # Determinar orden usando _printer_order (soporta cross-brand ordering)
        SKIP_KEYS = {"_modelos", "_printer_order", "_config"}
        printer_order = data.get("_printer_order", [])
        
        if printer_order:
            ordered = []
            for entry in printer_order:
                b = entry.get("brand", "")
                ip_e = entry.get("ip", "")
                bk = next((k for k in data if k not in SKIP_KEYS
                           and isinstance(data[k], dict) and "printer" in data[k]
                           and k.lower() == b.lower()), None)
                if not bk:
                    continue
                p = next((p for p in data[bk]["printer"] if counter._get_printer_ip(p) == ip_e), None)
                if p:
                    ordered.append((bk, p))
        else:
            # Fallback: orden de claves del JSON
            ordered = []
            for bk, info in data.items():
                if bk in SKIP_KEYS or not isinstance(info, dict) or "printer" not in info:
                    continue
                for p in info["printer"]:
                    ordered.append((bk, p))
        
        for brand, printer_item in ordered:
                ip = counter._get_printer_ip(printer_item)
                name = counter._get_printer_name(printer_item)
                
                self.table.insertRow(row)
                
                # [0] Marca
                item_brand = QTableWidgetItem(brand)
                item_brand.setFlags(item_brand.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, item_brand)
                
                # [1] Modelo Asignado - mostrar el valor guardado
                modelo_asignado = printer_item.get("modelo_asignado", "")
                item_modelo = QTableWidgetItem(modelo_asignado if modelo_asignado else "--")
                item_modelo.setFlags(item_modelo.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 1, item_modelo)
                
                # [2] IP — Clickeable para abrir en navegador
                item_ip = QTableWidgetItem(ip)
                item_ip.setFlags(item_ip.flags() & ~Qt.ItemIsEditable)
                item_ip.setForeground(QColor("#1565C0"))
                item_ip.setToolTip(f"🌐 Clic para abrir http://{ip} en el navegador")
                self.table.setItem(row, 2, item_ip)
                
                # [3] Estado
                item_status = QTableWidgetItem("--")
                item_status.setFlags(item_status.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 3, item_status)
                
                # [4] Ubicación/Nombre
                item_name = QTableWidgetItem(name)
                self.table.setItem(row, 4, item_name)
                
                # [5] Contador
                item_counter = QTableWidgetItem("--")
                item_counter.setFlags(item_counter.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 5, item_counter)
                
                # [6] Nivel del Tóner (no editable)
                item_toner = QTableWidgetItem("--")
                item_toner.setFlags(item_toner.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 6, item_toner)
                
                # [7] Modelo de Tóner (no editable) -- hasta ejecutar SNMP
                item_toner_model = QTableWidgetItem("--")
                item_toner_model.setFlags(item_toner_model.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 7, item_toner_model)
                
                row += 1
        
        self.status_label.setText(f"Tabla recargada ({row} impresoras)")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        # Al recargar desde JSON no hay cambios de orden pendientes
        self.btn_save_order.setEnabled(False)
        self.btn_save_order.setIcon(qta.icon('fa5s.save', color='#BDBDBD'))
        self.btn_save_order.setToolTip("Guardar orden actual")
        # Re-aplicar filtro de búsqueda si hay texto activo
        self.filter_table()
    

    def open_ip_in_browser(self, ip: str):
        """Abre la IP en el navegador web por defecto"""
        url = QUrl(f"http://{ip}")
        QDesktopServices.openUrl(url)
        logger.info(f"Abriendo navegador con URL: http://{ip}")

    def save_names(self):
        """Guarda nombres, IPs y marcas leyendo directamente de la tabla"""
        # Si la tabla está vacía, no hay nada que guardar
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Info", "No hay impresoras para guardar")
            return
        
        # Cargar JSON EXISTENTE para preservar OIDs de tóner
        existing_data = counter.load_json(display=False) or {}
        
        # RECONSTRUIR JSON DESDE LA TABLA
        data = {}
        
        for row in range(self.table.rowCount()):
            marca = self.table.item(row, 0).text().strip()  # Columna 0: Marca
            modelo = self.table.item(row, 1).text().strip() # Columna 1: Modelo (IMPORTANTE guardar)
            ip = self.table.item(row, 2).text().strip()      # Columna 2: IP
            # estado = self.table.item(row, 3).text().strip()  # Columna 3: Estado (readonly, generado)
            nombre = self.table.item(row, 4).text().strip()  # Columna 4: Ubicación
            # contador = self.table.item(row, 5).text().strip()  # Columna 5: Contador (readonly, SNMP)
            # toner = self.table.item(row, 6).text().strip()  # Columna 6: Nivel Tóner (readonly, SNMP)
            # toner_model = self.table.item(row, 7).text().strip()  # Columna 7: Modelo Tóner (readonly, SNMP)
            
            # Validar que marca e IP no estén vacías
            if not marca or not ip:
                QMessageBox.warning(self, "Error", f"Fila {row + 1}: Marca e IP son obligatorias")
                return
            
            # Crear marca si no existe - búsqueda case-insensitive en existing_data
            if marca not in data:
                # Preservar OIDs del JSON existente (buscar con case-insensitive)
                existing_oids = {}
                marca_key_existing = next(
                    (k for k in existing_data if k.lower() == marca.lower()
                     and isinstance(existing_data[k], dict) and "OID" in existing_data[k]), None
                )
                if marca_key_existing:
                    existing_oids = existing_data[marca_key_existing]["OID"].copy()
                
                data[marca] = {
                    "OID": {
                        "counter": existing_oids.get("counter", "1.3.6.1.2.1.43.10.2.1.5.1.1"),
                        "name": existing_oids.get("name", "1.3.6.1.2.1.43.10.2.1.5.1.1"),
                        "toner_current": existing_oids.get("toner_current", ""),
                        "toner_max": existing_oids.get("toner_max", ""),
                        "toner_model": existing_oids.get("toner_model", "")
                    },
                    "printer": []
                }
            
            # Agregar impresora a la marca - IMPORTANTE: guardar modelo_asignado
            printer_data = {
                "ip": ip,
                "custom_name": nombre if nombre else ip
            }
            # Incluir modelo si está definido y no es "--"
            if modelo and modelo != "--":
                printer_data["modelo_asignado"] = modelo
            
            data[marca]["printer"].append(printer_data)
        
        # Guardar orden global para preservar cross-brand ordering al recargar
        printer_order = []
        for row_idx in range(self.table.rowCount()):
            b_item = self.table.item(row_idx, 0)
            ip_item = self.table.item(row_idx, 2)
            if b_item and ip_item:
                printer_order.append({
                    "brand": b_item.text().strip(),
                    "ip": ip_item.text().strip()
                })
        data["_printer_order"] = printer_order
        
        # Preservar _modelos si existe
        if "_modelos" in existing_data:
            data["_modelos"] = existing_data["_modelos"]
        
        # Guardar el JSON reconstruido
        try:
            # CRÍTICO: Crear el directorio si no existe
            json_path = Path(counter.JSON_PATH)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(counter.JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Éxito", "✓ Datos guardados correctamente")
            self.status_label.setText("✓ Cambios guardados")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            # Deshabilitar botón guardar hasta nuevo reordenamiento
            self.btn_save_order.setEnabled(False)
            self.btn_save_order.setIcon(qta.icon('fa5s.save', color='#BDBDBD'))
            self.btn_save_order.setToolTip("Guardar orden actual")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
            self.status_label.setText("✗ Error al guardar")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def export_csv(self):
        """Exporta los datos a CSV y abre automáticamente"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.export_path / f"printercounter_{timestamp}.csv"
        
        try:
            with open(filename, "w", encoding="utf-8-sig") as f:
                # Cabecera - IDÉNTICA al dashboard
                f.write("Marca;Modelo;IP;Estado;Ubicación;Contador;Nivel del Tóner;Modelo de Tóner\n")
                
                # Datos
                for row in range(self.table.rowCount()):
                    brand = self.table.item(row, 0).text()      # [0] Marca
                    modelo = self.table.item(row, 1).text()     # [1] Modelo
                    ip = self.table.item(row, 2).text()         # [2] IP
                    status = self.table.item(row, 3).text()     # [3] Estado
                    name = self.table.item(row, 4).text()       # [4] Ubicación
                    counter_val = self.table.item(row, 5).text()    # [5] Contador
                    toner_level = self.table.item(row, 6).text()    # [6] Nivel Tóner
                    toner_model = self.table.item(row, 7).text()    # [7] Modelo Tóner
                    
                    f.write(f"{brand};{modelo};{ip};{status};{name};{counter_val};{toner_level};{toner_model}\n")
            
            # Abrir automáticamente
            self.open_file(str(filename))
            QMessageBox.information(self, "Éxito", f"Archivo exportado y abierto:\n{filename.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al exportar CSV: {str(e)}")
    
    def open_file(self, filepath):
        """Abre un archivo con su aplicación predeterminada"""
        try:
            if sys.platform == 'win32':
                os.startfile(filepath)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', filepath])
            else:  # Linux
                subprocess.Popen(['xdg-open', filepath])
        except Exception as e:
            print(f"No se pudo abrir automáticamente: {e}")
    
    def move_row_up(self):
        """Mueve la fila seleccionada hacia arriba"""
        current_row = self.table.currentRow()
        if current_row <= 0:
            return
        
        try:
            self.table.move_row_up()
            self.btn_save_order.setEnabled(True)
            self.btn_save_order.setIcon(qta.icon('fa5s.save', color='#1565C0'))
            self.btn_save_order.setToolTip("Guardar orden (hay cambios sin guardar)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mover fila: {str(e)}")
    
    def move_row_down(self):
        """Mueve la fila seleccionada hacia abajo"""
        current_row = self.table.currentRow()
        if current_row < 0 or current_row >= self.table.rowCount() - 1:
            return
        
        try:
            self.table.move_row_down()
            self.btn_save_order.setEnabled(True)
            self.btn_save_order.setIcon(qta.icon('fa5s.save', color='#1565C0'))
            self.btn_save_order.setToolTip("Guardar orden (hay cambios sin guardar)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mover fila: {str(e)}")
    
    def update_delete_button_state(self):
        """Habilita/deshabilita botón Eliminar según si hay algo seleccionado"""
        has_selection = len(self.table.selectedItems()) > 0
        self.btn_delete.setEnabled(has_selection)
    
    def select_column(self, column_index, ctrl_pressed):
        """Selecciona/deselecciona una columna completa cuando se hace clic en el encabezado
        
        Args:
            column_index: Índice de la columna
            ctrl_pressed: Si True agrega a la selección, si False reemplaza/toggle
        """
        # Verificar si la columna ya está completamente seleccionada
        column_selected_count = 0
        for row in range(self.table.rowCount()):
            item = self.table.item(row, column_index)
            if item and item.isSelected():
                column_selected_count += 1
        
        is_fully_selected = column_selected_count == self.table.rowCount()
        
        # Si no se presiona Ctrl, limpiar selección previa
        if not ctrl_pressed:
            self.table.clearSelection()
            
            # Si la columna ya estaba seleccionada, hacer toggle (deseleccionar)
            if is_fully_selected:
                return
        
        # Seleccionar todas las celdas de la columna
        for row in range(self.table.rowCount()):
            item = self.table.item(row, column_index)
            if item:
                item.setSelected(True)
    
    def on_copy_button_clicked(self):
        """Simula presionar Ctrl+C en la tabla para copiar al portapapeles"""
        try:
            logger.info("on_copy_button_clicked: Simulando Ctrl+C...")
            from PyQt5.QtGui import QKeyEvent
            from PyQt5.QtCore import Qt
            
            # Crear evento de teclado Ctrl+C
            key_event = QKeyEvent(
                QKeyEvent.KeyPress,
                Qt.Key_C,
                Qt.ControlModifier,
                "c"
            )
            
            # Enviar evento a la tabla (dispara keyPressEvent del CtrlSelectTable)
            QApplication.sendEvent(self.table, key_event)
            logger.info("on_copy_button_clicked: ✓ Evento Ctrl+C enviado correctamente")
        except Exception as e:
            logger.error(f"ERROR en on_copy_button_clicked: {e}", exc_info=True)
            QMessageBox.critical(self, "Error al Copiar", f"Error al simular Ctrl+C: {e}")
    
    def delete_selected_row(self):
        """Elimina filas seleccionadas con diálogo de selección"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Selecciona al menos una fila para eliminar")
            return
        
        # Leer datos directamente desde las celdas visibles de la tabla (no del JSON)
        rows_info = []  # [(visual_row, brand, ip, name), ...]
        for r in sorted(selected_rows):
            def _cell(c, row_idx=r):  # Capturar r por valor para evitar closure bug
                item = self.table.item(row_idx, c)
                return item.text() if item else ""
            rows_info.append((r, _cell(0), _cell(2), _cell(4)))
        
        # Crear diálogo de confirmación
        dialog = QDialog(self)
        dialog.setWindowTitle("Eliminar Impresoras")
        dialog.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Se han seleccionado {len(rows_info)} fila(s).\n¿Cuáles deseas eliminar?"))
        
        checkboxes = []
        for (r, brand, ip, name) in rows_info:
            cb = QCheckBox(f"{brand} - {ip} - {name}")
            cb.setChecked(True)
            checkboxes.append(cb)
            layout.addWidget(cb)
        
        layout.addStretch()
        button_layout = QHBoxLayout()
        btn_ok = QPushButton()
        btn_ok.setIcon(qta.icon('fa5s.trash', color='white'))
        btn_ok.setText("  Eliminar Seleccionados")
        btn_ok.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px; min-width: 150px;")
        btn_cancel = QPushButton()
        btn_cancel.setIcon(qta.icon('fa5s.times', color='white'))
        btn_cancel.setText("  Cancelar")
        btn_cancel.setStyleSheet("background-color: #757575; color: white; font-weight: bold; padding: 10px; min-width: 150px;")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # Qué filas confirma el usuario eliminar
        to_delete = [(rows_info[i]) for i, cb in enumerate(checkboxes) if cb.isChecked()]
        if not to_delete:
            QMessageBox.warning(self, "Advertencia", "No seleccionaste ninguna fila para eliminar")
            return
        
        result = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar {len(to_delete)} fila(s)?\n\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        if result != QMessageBox.Yes:
            return
        
        # Cargar JSON y eliminar por brand+ip (case-insensitive)
        data = counter.load_json(display=False)
        if not data:
            QMessageBox.critical(self, "Error", "No se pudo cargar printers.json")
            return
        
        SKIP_KEYS = {"_modelos", "_printer_order", "_config"}
        
        for _, brand_ui, ip_del, name_del in to_delete:
            # Buscar la clave real en el JSON (case-insensitive)
            bk = next((k for k in data if k not in SKIP_KEYS
                        and isinstance(data[k], dict) and "printer" in data[k]
                        and k.lower() == brand_ui.lower()), None)
            if bk:
                # Eliminar solo la PRIMERA coincidencia (por ip+name, o solo ip como fallback)
                printers_list = data[bk]["printer"]
                idx_to_remove = None
                for idx, p in enumerate(printers_list):
                    if p.get("ip") == ip_del and p.get("custom_name", "") == name_del:
                        idx_to_remove = idx
                        break
                if idx_to_remove is None:
                    # Fallback: buscar solo por IP
                    for idx, p in enumerate(printers_list):
                        if p.get("ip") == ip_del:
                            idx_to_remove = idx
                            break
                if idx_to_remove is not None:
                    printers_list.pop(idx_to_remove)
                if not printers_list:
                    del data[bk]
        
        # Actualizar _printer_order eliminando solo entradas exactas
        if "_printer_order" in data:
            new_order = data["_printer_order"][:]
            for _, brand_ui, ip_del, _ in to_delete:
                for idx, e in enumerate(new_order):
                    if e.get("ip") == ip_del and e.get("brand", "").lower() == brand_ui.lower():
                        new_order.pop(idx)
                        break
            data["_printer_order"] = new_order
        
        # Guardar JSON
        try:
            with open(counter.JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # Eliminar filas de la tabla (en orden inverso)
            for (r, _, _, _) in sorted(to_delete, key=lambda x: x[0], reverse=True):
                self.table.removeRow(r)
            
            count = len(to_delete)
            self.status_label.setText(f"✓ {count} fila(s) eliminada(s)")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            QMessageBox.information(self, "Éxito", f"✓ {count} fila(s) eliminada(s) correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al eliminar: {str(e)}")
    
    def export_printers_json(self):
        """Exporta el printers.json actual con contraseña a carpeta de exportación"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = self.export_path / f"printers_backup_{timestamp}.json"
            
            shutil.copy(counter.JSON_PATH, str(export_file))
            self.open_file(str(export_file))
            QMessageBox.information(self, "Éxito", f"Archivo exportado:\n{export_file.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al exportar: {str(e)}")
    
    def import_printers_json(self):
        """Importa un archivo printers.json desde disco"""
        file_dialog = QFileDialog()
        filepath, _ = file_dialog.getOpenFileName(
            self,
            "Importar printers.json",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            # Validar que sea un JSON válido
            with open(filepath, "r", encoding="utf-8") as f:
                test_data = json.load(f)
            
            # Hacer backup del actual
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = Path(counter.JSON_PATH).parent / f"printers_backup_{timestamp}.json"
            shutil.copy(counter.JSON_PATH, str(backup_file))
            
            # Copiar nuevo archivo
            shutil.copy(filepath, counter.JSON_PATH)
            
            QMessageBox.information(self, "Éxito", f"Archivo importado correctamente\nBackup guardado en: {backup_file.name}")
            self.refresh_table_from_json()
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "El archivo no es un JSON válido")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al importar: {str(e)}")
