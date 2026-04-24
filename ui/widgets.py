# Widgets personalizados: ToastNotification, CtrlClickHeader, CtrlSelectTable.
import sys
import json
import logging
import subprocess
import shutil
import os
import asyncio
from pathlib import Path
from datetime import datetime

import qtawesome as qta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
    QSpinBox, QGroupBox, QMessageBox, QFileDialog, QProgressBar,
    QTabWidget, QHeaderView, QDialog, QCheckBox, QTextEdit, QFrame,
    QMenu, QTextBrowser, QRadioButton, QButtonGroup, QComboBox, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QDesktopServices

import core.snmp_engine as counter
from core.config import config as app_config

logger = logging.getLogger(__name__)


class ToastNotification(QWidget):
    # Ventana flotante independiente para mostrar notificaciones tipo toast
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Window |                    # Es una ventana independiente
            Qt.FramelessWindowHint |       # Sin borde
            Qt.WindowStaysOnTopHint |      # Siempre al frente
            Qt.NoDropShadowWindowHint      # Sin sombra
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # Fondo transparente
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel()
        self.label.setStyleSheet("""
            QLabel {
                background-color: #27ae60;
                color: white;
                border-radius: 8px;
                padding: 12px 25px;
                font-weight: bold;
                font-size: 12pt;
                border: 2px solid #1e8449;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #2ecc71, stop:1 #27ae60);
            }
        """)
        self.label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        layout.addWidget(self.label)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide_toast)
        self.parent_window = parent
    
    def show_message(self, message, duration=1500):
        """Muestra el mensaje con duración especificada"""
        try:
            logger.info(f"ToastNotification: Mostrando '{message}' por {duration}ms")
            self.label.setText(message)
            self.adjustSize()
            self._center_on_parent()
            self.show()
            self.raise_()
            self.activateWindow()
            QApplication.processEvents()
            
            if self.timer.isActive():
                self.timer.stop()
            
            self.timer.setSingleShot(True)
            self.timer.start(duration)
        except Exception as e:
            logger.error(f"ERROR en ToastNotification.show_message: {type(e).__name__}: {e}", exc_info=True)
    
    def _center_on_parent(self):
        """Centra la notificación en la ventana padre"""
        if self.parent_window:
            parent_geometry = self.parent_window.frameGeometry()
            x = parent_geometry.center().x() - self.width() // 2
            y = parent_geometry.center().y() - self.height() // 2
            self.move(x, y)
            logger.info(f"ToastNotification: Posicionado en ({x}, {y})")
    
    def hide_toast(self):
        """Oculta la notificación"""
        self.hide()
        logger.debug("ToastNotification: Ocultado")




class CtrlClickHeader(QHeaderView):
    # Header personalizado que detecta Ctrl para multi-selección de columnas
    
    column_clicked = pyqtSignal(int, bool)  # (column_index, ctrl_pressed)
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setSectionsClickable(True)
        self.last_clicked_column = None
    
    def mousePressEvent(self, event):
        """Detecta clic con o sin Ctrl y emite señal"""
        column = self.logicalIndexAt(event.x())
        if column < 0:
            return
        
        ctrl_pressed = event.modifiers() == Qt.ControlModifier
        
        # Enviar señal con info de si es el mismo o diferente
        is_same_column = column == self.last_clicked_column
        self.column_clicked.emit(column, ctrl_pressed)
        
        # Guardar última columna clickeada
        if not ctrl_pressed:
            self.last_clicked_column = column if not is_same_column else None
        else:
            self.last_clicked_column = column



class CtrlSelectTable(QTableWidget):
    # QTableWidget personalizado: seleccion tipo Excel, Ctrl+C copia al portapapeles
    
    def __init__(self, parent=None, on_copy_callback=None, ip_column=None, ip_click_callback=None):
        super().__init__(parent)
        logger.info("CtrlSelectTable: Inicializando")
        self.setSelectionMode(QTableWidget.ExtendedSelection)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.on_copy_callback = on_copy_callback
        self.ip_column = ip_column          # Índice de columna con IPs clicables
        self.ip_click_callback = ip_click_callback  # callback(ip) al hacer clic en IP
        self.setMouseTracking(True)         # Necesario para mouseMoveEvent sin clic
    
    def mouseMoveEvent(self, event):
        """Cambia cursor a puntero SOLO cuando el ratón pasa sobre el texto de la IP"""
        if self.ip_column is not None and self.ip_click_callback is not None:
            item = self.itemAt(event.pos())
            if item and self.column(item) == self.ip_column:
                ip_text = item.text().strip()
                if ip_text and ip_text != "--":
                    # Calcular rectángulo exacto del texto
                    cell_rect = self.visualItemRect(item)
                    fm = self.fontMetrics()
                    text_width = fm.horizontalAdvance(ip_text)
                    text_height = fm.height()
                    PADDING = 6
                    text_left = cell_rect.left() + PADDING
                    text_right = text_left + text_width
                    text_top = cell_rect.top() + (cell_rect.height() - text_height) // 2
                    text_bottom = text_top + text_height
                    
                    if (text_left <= event.pos().x() <= text_right and
                            text_top <= event.pos().y() <= text_bottom):
                        self.viewport().setCursor(Qt.PointingHandCursor)
                        super().mouseMoveEvent(event)
                        return
        self.viewport().setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        """Restaura cursor al salir de la tabla"""
        self.viewport().setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Abre navegador SOLO si el clic cae sobre el texto de la IP (no en el espacio vacío de la celda)"""
        if (event.button() == Qt.LeftButton and
                self.ip_column is not None and self.ip_click_callback is not None):
            item = self.itemAt(event.pos())
            if item and self.column(item) == self.ip_column:
                ip_text = item.text().strip()
                if ip_text and ip_text != "--":
                    # Calcular el rectángulo exacto del texto dentro de la celda
                    cell_rect = self.visualItemRect(item)
                    fm = self.fontMetrics()
                    text_width = fm.horizontalAdvance(ip_text)
                    text_height = fm.height()
                    # El texto se renderiza con ~6px de padding horizontal a la izquierda
                    PADDING = 6
                    text_left = cell_rect.left() + PADDING
                    text_right = text_left + text_width
                    text_top = cell_rect.top() + (cell_rect.height() - text_height) // 2
                    text_bottom = text_top + text_height
                    
                    click_x = event.pos().x()
                    click_y = event.pos().y()
                    
                    if (text_left <= click_x <= text_right and
                            text_top <= click_y <= text_bottom):
                        self.ip_click_callback(ip_text)
                        return  # NO pasar a super() — no seleccionar celda
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """Maneja pulsación de teclas - Ctrl+C copia al portapapeles"""
        try:
            logger.debug(f"keyPressEvent: KEY={event.key()}, Qt.Key_C={Qt.Key_C}, MODIFIERS={event.modifiers()}, Qt.ControlModifier={Qt.ControlModifier}, TEXT='{event.text()}'")
            
            # Detectar Ctrl+C de múltiples formas para asegurar compatibilidad
            is_c_key = (event.key() == Qt.Key_C) or (event.text().lower() == 'c')
            is_ctrl = (event.modifiers() & Qt.ControlModifier)
            
            if is_c_key and is_ctrl:
                logger.info("keyPressEvent: ✓ Detectado Ctrl+C, llamando _copy_selection_safe()...")
                self._copy_selection_safe()
                return
            
            logger.debug(f"keyPressEvent: No es Ctrl+C (is_c_key={is_c_key}, is_ctrl={is_ctrl})")
            
        except Exception as e:
            logger.error(f"ERROR en keyPressEvent: {type(e).__name__}: {e}", exc_info=True)
        
        super().keyPressEvent(event)
    
    def _copy_selection_safe(self):
        """Copia solo las filas Y columnas seleccionadas al portapapeles de forma segura"""
        try:
            logger.info("_copy_selection_safe: Iniciando copia...")
            logger.info(f"_copy_selection_safe: callback definido: {self.on_copy_callback is not None}")
            
            # Obtener elementos seleccionados
            selected_items = self.selectedItems()
            logger.info(f"_copy_selection_safe: Items seleccionados: {len(selected_items)}")
            
            if not selected_items:
                logger.warning("_copy_selection_safe: No hay elementos seleccionados")
                # Mostrar notificación aunque no haya selección
                if self.on_copy_callback:
                    logger.info("_copy_selection_safe: Llamando callback con mensaje de advertencia")
                    self.on_copy_callback("⚠️ Selecciona elementos para copiar")
                else:
                    logger.error("_copy_selection_safe: ERROR - on_copy_callback es None")
                return
            
            # Obtener números de fila y columna únicos seleccionados
            selected_rows = sorted(set(self.row(item) for item in selected_items))
            selected_cols = sorted(set(self.column(item) for item in selected_items))
            logger.debug(f"_copy_selection_safe: Filas: {selected_rows}, Columnas: {selected_cols}")
            
            # Construir texto tab-separado SOLO CON COLUMNAS SELECCIONADAS
            lines = []
            for row in selected_rows:
                row_values = []
                for col in selected_cols:
                    cell = self.item(row, col)
                    value = (cell.text() if cell else "").strip()
                    row_values.append(value)
                lines.append("\t".join(row_values))
            
            # Copiar al portapapeles
            text = "\n".join(lines)
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
            cantidad = len(selected_rows) * len(selected_cols)
            logger.info(f"_copy_selection_safe: ✓ {len(selected_rows)} fila(s) x {len(selected_cols)} columna(s) copiada(s)")
            
            # Mostrar notificación
            if self.on_copy_callback:
                msg = f"✓ Copiado ({cantidad} celda{'s' if cantidad != 1 else ''})"
                logger.info(f"_copy_selection_safe: Llamando callback con mensaje: {msg}")
                self.on_copy_callback(msg)
            else:
                logger.error("_copy_selection_safe: ERROR - on_copy_callback es None cuando debería haber items")
            
        except Exception as e:
            logger.error(f"ERROR en _copy_selection_safe: {type(e).__name__}: {e}", exc_info=True)
    
    def move_row_up(self):
        """Mueve la fila seleccionada hacia arriba"""
        current_row = self.currentRow()
        if current_row <= 0:
            return
        self.swap_rows(current_row, current_row - 1)
        self.selectRow(current_row - 1)
    
    def move_row_down(self):
        """Mueve la fila seleccionada hacia abajo"""
        current_row = self.currentRow()
        if current_row < 0 or current_row >= self.rowCount() - 1:
            return
        self.swap_rows(current_row, current_row + 1)
        self.selectRow(current_row + 1)
    
    def swap_rows(self, row1, row2):
        """Intercambia dos filas manteniendo formato"""
        try:
            for col in range(self.columnCount()):
                item1 = self.item(row1, col)
                item2 = self.item(row2, col)
                
                if not item1 or not item2:
                    continue
                
                # Guardar propiedades
                text1 = item1.text()
                flags1 = item1.flags()
                fg1 = item1.foreground()
                
                # Intercambiar
                item1.setText(item2.text())
                item1.setFlags(item2.flags())
                item1.setForeground(item2.foreground())
                
                item2.setText(text1)
                item2.setFlags(flags1)
                item2.setForeground(fg1)
        except Exception as e:
            logger.error(f"ERROR en swap_rows: {type(e).__name__}: {e}", exc_info=True)
