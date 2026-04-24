# Mixin: pestaña Gestión de Modelos.
import json
import logging

import qtawesome as qta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QGroupBox, QMessageBox, QHeaderView
)
from PyQt5.QtGui import QColor

import core.snmp_engine as counter

logger = logging.getLogger(__name__)
from ui.widgets import CtrlSelectTable



class ModelsMixin:
    """Pestaña Gestión de Modelos — se mezcla con PrinterDashboard."""

    def create_models_tab(self):
        """Crea pestaña de gestión de modelos con tabla CRUD"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Tabla de modelos - usar CtrlSelectTable para permitir copiar con Ctrl+C
        self.models_table = CtrlSelectTable(on_copy_callback=self.show_toast)
        self.models_table.setColumnCount(6)
        self.models_table.setHorizontalHeaderLabels([
            "Marca", "Modelo", "OID Contador", "OID Tóner Actual", 
            "OID Tóner Máximo", "OID Modelo Tóner"
        ])
        self.models_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.models_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Selección tipo Excel: celda individual o multi-celda; fila completa al clic en el número lateral
        self.models_table.setSelectionBehavior(QTableWidget.SelectItems)
        self.models_table.setSelectionMode(QTableWidget.ExtendedSelection)
        
        # Tooltip con instrucciones
        self.models_table.setToolTip("💡 Ctrl+C para copiar | Clic en celda para seleccionar | Clic en número de fila para seleccionar fila")
        
        layout.addWidget(QLabel("📋 Gestión de Modelos Predefinidos"))
        layout.addWidget(self.models_table)
        
        # Panel de botones
        button_layout = QHBoxLayout()
        
        btn_add_model = QPushButton()
        btn_add_model.setIcon(qta.icon('fa5s.plus', color='white'))
        btn_add_model.setText("  Agregar Modelo")
        btn_add_model.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_add_model.setMinimumWidth(140)
        btn_add_model.clicked.connect(self.add_model)
        button_layout.addWidget(btn_add_model)
        
        btn_edit_model = QPushButton()
        btn_edit_model.setIcon(qta.icon('fa5s.edit', color='white'))
        btn_edit_model.setText("  Editar")
        btn_edit_model.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        btn_edit_model.setMinimumWidth(140)
        btn_edit_model.clicked.connect(self.edit_model)
        button_layout.addWidget(btn_edit_model)
        
        self.btn_delete_model = QPushButton()
        self.btn_delete_model.setIcon(qta.icon('fa5s.trash', color='white'))
        self.btn_delete_model.setText("  Eliminar")
        self.btn_delete_model.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        self.btn_delete_model.setMinimumWidth(140)
        self.btn_delete_model.setEnabled(False)  # Deshabilitado hasta seleccionar una fila
        self.btn_delete_model.clicked.connect(self.delete_model)
        button_layout.addWidget(self.btn_delete_model)
        
        # Habilitar/deshabilitar Eliminar según selección
        self.models_table.itemSelectionChanged.connect(
            lambda: self.btn_delete_model.setEnabled(self.models_table.currentRow() >= 0 and bool(self.models_table.selectedItems()))
        )
        
        btn_refresh_models = QPushButton()
        btn_refresh_models.setIcon(qta.icon('fa5s.sync-alt', color='white'))
        btn_refresh_models.setText("  Refrescar")
        btn_refresh_models.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold; padding: 8px;")
        btn_refresh_models.setMinimumWidth(140)
        btn_refresh_models.clicked.connect(self.load_models)
        button_layout.addWidget(btn_refresh_models)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        
        # Cargar modelos al inicializar
        self.load_models()
        
        return widget
    
    def load_models(self):
        """Carga los modelos desde printers.json y los muestra en la tabla"""
        data = counter.load_json(display=False)
        if data is None:
            return
        
        self.models_table.setRowCount(0)
        row = 0
        
        modelos = data.get("_modelos", {})
        
        for marca, modelos_marca in modelos.items():
            for nombre_modelo, oids in modelos_marca.items():
                self.models_table.insertRow(row)
                
                # Marca
                item = QTableWidgetItem(marca)
                self.models_table.setItem(row, 0, item)
                
                # Nombre Modelo
                item = QTableWidgetItem(nombre_modelo)
                self.models_table.setItem(row, 1, item)
                
                # OID Contador
                item = QTableWidgetItem(oids.get("oid_contador", ""))
                self.models_table.setItem(row, 2, item)
                
                # OID Tóner Actual
                item = QTableWidgetItem(oids.get("oid_toner_actual", ""))
                self.models_table.setItem(row, 3, item)
                
                # OID Tóner Máximo
                item = QTableWidgetItem(oids.get("oid_toner_maximo", ""))
                self.models_table.setItem(row, 4, item)
                
                # OID Modelo Tóner (o valor manual)
                toner_model_manual = oids.get("toner_model_manual", "")
                oid_modelo_valor = oids.get("oid_modelo_toner", "")
                if toner_model_manual:
                    # Mostrar valor manual con indicador visual
                    item = QTableWidgetItem(f"📝 {toner_model_manual}")
                    item.setForeground(QColor("#e65100"))  # naranja para indicar manual
                    item.setToolTip("Valor ingresado manualmente (no por OID)")
                else:
                    item = QTableWidgetItem(oid_modelo_valor)
                self.models_table.setItem(row, 5, item)
                
                row += 1
    
    def delete_model(self):
        """Elimina el modelo seleccionado"""
        row = self.models_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un modelo para eliminar")
            return
        
        marca = self.models_table.item(row, 0).text()
        modelo = self.models_table.item(row, 1).text()
        
        result = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Eliminar el modelo '{modelo}' de {marca}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            data = counter.load_json(display=False)
            if data and "_modelos" in data and marca in data["_modelos"]:
                if modelo in data["_modelos"][marca]:
                    del data["_modelos"][marca][modelo]
                    
                    # Si la marca quedó sin modelos, eliminarla
                    if not data["_modelos"][marca]:
                        del data["_modelos"][marca]
                    
                    try:
                        with open(counter.JSON_PATH, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4, ensure_ascii=False)
                        
                        QMessageBox.information(self, "Éxito", "Modelo eliminado correctamente")
                        self.load_models()
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
    
