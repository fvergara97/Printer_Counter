# Ventana principal: PrinterDashboard ensamblada con todos los mixins.
import json
import logging
import asyncio
import os
from pathlib import Path

import qtawesome as qta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QMessageBox, QTabWidget, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QHeaderView, QTableWidget, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap

import core.snmp_engine as counter
from core.config import config as app_config

logger = logging.getLogger(__name__)

from ui.widgets import ToastNotification, CtrlSelectTable, CtrlClickHeader
from ui.workers import SNMPWorker
from ui.tabs.dashboard import DashboardMixin
from ui.tabs.models import ModelsMixin
from ui.tabs.snmp_config import SNMPConfigMixin
from ui.tabs.storage import StorageMixin
from ui.dialogs.about import AboutMixin
from ui.dialogs.printer_dialogs import PrinterDialogsMixin
from ui.dialogs.model_dialogs import ModelDialogsMixin


class PrinterDashboard(
    QMainWindow,
    DashboardMixin,
    ModelsMixin,
    SNMPConfigMixin,
    StorageMixin,
    AboutMixin,
    PrinterDialogsMixin,
    ModelDialogsMixin,
):
    # Ventana principal del Contador de Impresoras SNMP.

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Printer Counter V1.0")
        self.setGeometry(100, 100, 1200, 700)
        
        # Cargar icono personalizado — buscar en varias rutas
        _icon_candidates = [
            Path("Icon.ico"),                                    # Relativo al cwd (raíz del proyecto)
            Path(__file__).parent.parent / "Icon.ico",           # Raíz del proyecto (relativo a ui/)
            Path(__file__).parent / "Icon.ico",                  # Dentro de ui/ (no debería estar aquí)
        ]
        icon_path = next((p for p in _icon_candidates if p.exists()), None)
        if icon_path:
            app_icon = QIcon(str(icon_path))
            self.setWindowIcon(app_icon)
            # Establecer ícono global para que TODOS los diálogos lo hereden
            QApplication.instance().setWindowIcon(app_icon)
        
        # Event loop para async
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        self.snmp_worker = None
        self.current_data = {}  # Almacenar datos actuales
        self.edit_mode = False  # Modo edición de la tabla (desactivado por defecto)
        
        # Ruta de exportación por defecto
        self.export_path = Path.home() / "Documents" / "Contadores"
        self.export_path.mkdir(parents=True, exist_ok=True)
        
        # Crear notificación toast como ventana flotante independiente
        self.toast_notification = ToastNotification(self)
        
        # Inicializar UI
        self.init_ui()
        self.load_config_from_json()
    

    def show_toast(self, message, duration=1500):
        # Muestra una notificación temporal (toast) en el centro de la pantalla
        # 
        # Args:
        #     message (str): Mensaje a mostrar
        #     duration (int): Duración en milisegundos (default 1500ms = 1.5s)
        try:
            logger.info(f"show_toast: Enviando mensaje: '{message}'")
            self.toast_notification.show_message(message, duration)
        except Exception as e:
            logger.error(f"ERROR en show_toast: {type(e).__name__}: {e}", exc_info=True)
    
    def init_ui(self):
        # Inicializa la interfaz gráfica
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # ===== HEADER CON LOGO =====
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 10)
        
        # Agregar icono con mejor calidad
        icon_label = QLabel()
        
        # Buscar el ícono en varias ubicaciones
        icon_path = None
        possible_paths = [
            Path("Icon.ico"),
            Path(__file__).parent / "Icon.ico",
            Path(__file__).parent.parent / "Icon.ico",
        ]
        
        for path in possible_paths:
            if path.exists():
                icon_path = path
                break
        
        if icon_path:
            # Cargar con máxima calidad - RESOLUCIÓN HD (64x64)
            pixmap = QPixmap(str(icon_path))
            
            # Escalar a 64x64 manteniendo aspecto ratio con MÁXIMA calidad
            scaled_pixmap = pixmap.scaledToWidth(
                64,  # Aumentado a 64 para mejor definición
                Qt.SmoothTransformation  # Máxima calidad de renderizado
            )
            
            # Opcional: Aplicar configuración DPI-aware si es disponible
            icon_label.setPixmap(scaled_pixmap)
            icon_label.setFixedSize(64, 64)  # Fijar tamaño exacto
            header_layout.addWidget(icon_label)
        
        # Agregar título
        title_label = QLabel("Contador de Impresoras SNMP")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Botón Acerca de (pequeño, al lado derecho)
        btn_about = QPushButton()
        btn_about.setIcon(qta.icon('fa5s.info-circle', color='#2196F3'))
        btn_about.setText("  Acerca de")
        btn_about.setMaximumWidth(120)
        btn_about.setStyleSheet("font-size: 9pt; padding: 5px;")
        btn_about.clicked.connect(self.show_about)
        header_layout.addWidget(btn_about)
        
        main_layout.addLayout(header_layout)
        
        # Línea separadora
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(separator)
        
        # ===== TAB WIDGET =====
        tabs = QTabWidget()
        
        # TAB 1: DASHBOARD
        tab1 = QWidget()
        tab1_layout = QVBoxLayout()
        
        # Panel de control (arriba)
        control_panel = self.create_control_panel()
        tab1_layout.addWidget(control_panel)
        
        # Tabla de datos - Usar clase personalizada CtrlSelectTable
        self.table = CtrlSelectTable(
            on_copy_callback=self.show_toast,
            ip_column=2,                          # Columna IP = col 2
            ip_click_callback=self.open_ip_in_browser  # Abrir navegador al clic en IP
        )
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Marca", "Modelo", "IP", "Estado", "Ubicación", "Contador", "Nivel del Tóner", "Modelo de Tóner"])
        
        # Usar header personalizado que detecta Ctrl
        header = CtrlClickHeader(1)  # 1 = horizontal
        self.table.setHorizontalHeader(header)
        header.column_clicked.connect(self.select_column)
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Seleccion tipo Excel: celda individual o multi-celda; fila completa al clic en el número lateral
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        
        # IP clicable solo sobre el texto — se gestiona desde mousePressEvent de CtrlSelectTable
        # (NO conectar cellClicked aqui, para evitar que click en celda IP abra el navegador)
        
        # Tooltip con instrucciones
        self.table.setToolTip("💡 Selecciona fila y usa ↑/↓ para reordenar | Ctrl+C para copiar | Haz clic en la IP para abrirla en el navegador")
        
        tab1_layout.addWidget(self.table)
        
        # Barra de estado y botones finales
        bottom_layout = QHBoxLayout()
        
        self.status_label = QLabel("Listo | Usa ↑/↓ para reordenar")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        bottom_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar)
        
        bottom_layout.addStretch()
        
        # Botón Eliminar fila (inicialmente deshabilitado)
        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(qta.icon('fa5s.trash', color='white'))
        self.btn_delete.setText("  Eliminar Fila")
        self.btn_delete.setMinimumWidth(150)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 5px;")
        self.btn_delete.clicked.connect(self.delete_selected_row)
        bottom_layout.addWidget(self.btn_delete)
        
        # Conectar cambios de selección a habilitar/deshabilitar botón
        self.table.itemSelectionChanged.connect(self.update_delete_button_state)
        
        
        # Botón Copiar (atajo a Ctrl+C)
        btn_copy = QPushButton()
        btn_copy.setIcon(qta.icon('fa5s.copy', color='white'))
        btn_copy.setText("  Copiar (Ctrl+C)")
        btn_copy.setMinimumWidth(150)
        btn_copy.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
        btn_copy.clicked.connect(self.on_copy_button_clicked)
        bottom_layout.addWidget(btn_copy)
        
        # Botones de exportación
        btn_export_csv = QPushButton()
        btn_export_csv.setIcon(qta.icon('fa5s.file-csv', color='white'))
        btn_export_csv.setText("  Exportar CSV")
        btn_export_csv.setMinimumWidth(150)
        btn_export_csv.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        btn_export_csv.clicked.connect(self.export_csv)
        bottom_layout.addWidget(btn_export_csv)
        

        
        tab1_layout.addLayout(bottom_layout)
        
        tab1.setLayout(tab1_layout)
        tabs.addTab(tab1, "Dashboard")
        
        # TAB 2: GESTIÓN DE MODELOS
        tab2 = self.create_models_tab()
        tabs.addTab(tab2, "Gestión de Modelos")
        
        # TAB 3: CONFIGURACIÓN
        tab3 = self.create_config_tab()
        tabs.addTab(tab3, "Configuración SNMP")
        
        # TAB 4: UBICACIÓN DE ARCHIVOS
        tab4 = self.create_storage_tab()
        tabs.addTab(tab4, "Ubicación de Archivos")
        
        main_layout.addWidget(tabs)
        central_widget.setLayout(main_layout)
    

    def load_config_from_json(self):
        # Carga la configuración SNMP desde printers.json o valores por defecto
        import json
        import os
        
        # CRÍTICO: Actualizar JSON_PATH al cargar la configuración
        counter.JSON_PATH = app_config.get_json_path()
        
        # Intentar cargar configuración guardada en printers.json
        try:
            if os.path.exists(counter.JSON_PATH):
                with open(counter.JSON_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = data.get("_config", {})
                    
                    counter.COMMUNITY = config.get("community", counter.COMMUNITY)
                    counter.TIMEOUT = config.get("timeout", counter.TIMEOUT)
                    counter.RETRIES = config.get("retries", counter.RETRIES)
                    counter.SNMP_MODE_PARALLEL = config.get("snmp_mode_parallel", True)
                    logger.info(f"Configuración cargada desde printers.json: Modo={'Paralelo' if counter.SNMP_MODE_PARALLEL else 'Secuencial'}")
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración de JSON: {e}. Usando valores por defecto.")
        
        self.community_input.setText(counter.COMMUNITY)
        self.timeout_input.setValue(counter.TIMEOUT)
        self.retries_input.setValue(counter.RETRIES)
        
        # Cargar modo SNMP (ahora persistido en printers.json)
        self.mode_parallel.setChecked(counter.SNMP_MODE_PARALLEL)
        self.mode_sequential.setChecked(not counter.SNMP_MODE_PARALLEL)
        
        # Cargar configuración de ubicación
        use_smb = app_config.get("use_smb", False)
        self.radio_local.setChecked(not use_smb)
        self.radio_smb.setChecked(use_smb)
        self.smb_path_input.setText(app_config.get("smb_path", "\\\\192.168.1.241\\printers_snmp"))
        self.smb_path_input.setEnabled(use_smb)
    
    def save_config(self):
        # Guarda la configuración SNMP en printers.json y en memoria
        import json
        import os
        
        # Guardar en memoria
        counter.COMMUNITY = self.community_input.text()
        counter.TIMEOUT = self.timeout_input.value()
        counter.RETRIES = self.retries_input.value()
        counter.SNMP_MODE_PARALLEL = self.mode_parallel.isChecked()
        
        # Persistir en printers.json
        try:
            json_path = counter.JSON_PATH
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Crear sección _config con la configuración
            data["_config"] = {
                "community": counter.COMMUNITY,
                "timeout": counter.TIMEOUT,
                "retries": counter.RETRIES,
                "snmp_mode_parallel": counter.SNMP_MODE_PARALLEL
            }
            
            # Guardar cambios en printers.json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            modo = "Paralelo" if counter.SNMP_MODE_PARALLEL else "Secuencial"
            logger.info(f"Configuración guardada: Community={counter.COMMUNITY}, Timeout={counter.TIMEOUT}s, Retries={counter.RETRIES}, Modo={modo}")
            QMessageBox.information(self, "Éxito", f"Configuración SNMP guardada correctamente.\nModo: {modo}")
        except Exception as e:
            logger.error(f"ERROR guardando configuración: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al guardar configuración: {e}")
    
