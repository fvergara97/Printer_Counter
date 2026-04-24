# Mixin: diálogos Acerca de, Donar y Sugerencias.
import logging
from urllib.parse import quote

import qtawesome as qta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGroupBox, QMessageBox, QDialog,
    QTextEdit, QFrame, QTextBrowser,
    QComboBox, QApplication
)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QDesktopServices

import core.snmp_engine as counter
from core.config import config as app_config

logger = logging.getLogger(__name__)



class AboutMixin:
    # Diálogos informativos — se mezcla con PrinterDashboard.

    def show_about(self):
        # Muestra el diálogo Acerca de con botones de acción
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("Acerca de — Contador de Impresoras SNMP")
        dialog.setMinimumWidth(480)
        dialog.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel#title {
                font-size: 15pt;
                font-weight: bold;
                color: #1565C0;
            }
            QLabel#body {
                font-family: 'Courier New', Monospace;
                font-size: 9pt;
                color: #333;
                line-height: 1.5em;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 16)
        
        # --- Título ---
        title_label = QLabel("Printer Counter")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # --- Cuerpo ---
        body_label = QLabel("""
<pre style="font-family: 'Courier New'; font-size: 9pt; color: #333;">
Versión   : 1.0
Año       : 2026
Creado por: Fernando A. Muñoz Vergara
Licencia  : GNU GPL v3.0 (Libre)

Descripción:
  Centralización y consulta de contadores de impresoras
  en red mediante protocolo SNMP.

Funciones principales:
  • Consulta centralizada de contadores en tiempo real
  • Estados Online/Offline de impresoras
  • Editar, agregar y eliminar impresoras
  • Exportar/Importar configuraciones
  • Almacenamiento portable (sin instalación)
</pre>""")
        body_label.setObjectName("body")
        body_label.setTextFormat(Qt.RichText)
        layout.addWidget(body_label)
        
        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #bdc3c7; margin: 4px 0;")
        layout.addWidget(sep)
        
        # --- Botones de acción ---
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        btn_repo = QPushButton()
        btn_repo.setIcon(qta.icon('fa5b.github', color='white'))
        btn_repo.setText("  Repositorio")
        btn_repo.setStyleSheet(
            "background-color: #24292e; color: white; font-weight: bold; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        btn_repo.setCursor(Qt.PointingHandCursor)
        btn_repo.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/fvergara97/Printer_Counter"))
        )
        
        btn_contact = QPushButton()
        btn_contact.setIcon(qta.icon('fa5s.lightbulb', color='white'))
        btn_contact.setText("  Sugerencias")
        btn_contact.setStyleSheet(
            "background-color: #1565C0; color: white; font-weight: bold; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        btn_contact.setCursor(Qt.PointingHandCursor)
        btn_contact.clicked.connect(lambda: self._show_suggestions_dialog(dialog))
        
        btn_donate = QPushButton()
        btn_donate.setIcon(qta.icon('fa5s.heart', color='white'))
        btn_donate.setText("  Donar")
        btn_donate.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        btn_donate.setCursor(Qt.PointingHandCursor)
        btn_donate.clicked.connect(lambda: self._show_donate_dialog(dialog))
        
        btn_license = QPushButton()
        btn_license.setIcon(qta.icon('fa5s.file-contract', color='white'))
        btn_license.setText("  Licencia")
        btn_license.setStyleSheet(
            "background-color: #37474f; color: white; font-weight: bold; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        btn_license.setCursor(Qt.PointingHandCursor)
        btn_license.clicked.connect(lambda: self._show_license_dialog(dialog))
        
        action_layout.addWidget(btn_repo)
        action_layout.addWidget(btn_license)
        action_layout.addWidget(btn_contact)
        action_layout.addWidget(btn_donate)
        layout.addLayout(action_layout)
        
        # --- Botón Cerrar ---
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        btn_close = QPushButton("  Cerrar")
        btn_close.setIcon(qta.icon('fa5s.times', color='#555'))
        btn_close.setStyleSheet(
            "background-color: #e0e0e0; color: #333; padding: 6px 18px; border-radius: 4px;"
        )
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(dialog.accept)
        close_layout.addWidget(btn_close)
        layout.addLayout(close_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _show_license_dialog(self, parent=None):
        # Muestra la licencia GPL 3.0 de la aplicación.
        LICENSE_TEXT = """\
Printer Counter — GNU General Public License v3.0

Este programa es software libre: usted puede redistribuirlo y/o
modificarlo bajo los términos de la Licencia Pública General GNU
publicada por la Free Software Foundation, ya sea la versión 3
de la Licencia, o (a su elección) cualquier versión posterior.

Este programa se distribuye con la esperanza de que sea útil,
pero SIN NINGUNA GARANTÍA; ni siquiera la garantía implícita
de COMERCIABILIDAD o IDONEIDAD PARA UN FIN DETERMINADO.
Véase la Licencia Pública General GNU para más detalles.

Usted debería haber recibido una copia de la Licencia Pública
General GNU junto con este programa. En caso contrario, consúltela
en <a href="https://www.gnu.org/licenses/">https://www.gnu.org/licenses/</a>.
"""
        dlg = QDialog(parent or self)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dlg.setWindowTitle("Licencia — GPL v3.0")
        dlg.setMinimumWidth(520)
        dlg.setMinimumHeight(420)
        dlg.setStyleSheet("QDialog { background-color: #f5f5f5; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)

        # Título
        title = QLabel()
        title.setText(
            "<b style='font-size:12pt; color:#37474f;'>"
            "GNU General Public License v3.0</b>"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(sep)

        # Texto de la licencia (scrollable)
        txt = QTextBrowser()
        txt.setOpenExternalLinks(True)
        txt.setHtml(f"<pre style='font-family: Consolas, Courier New, monospace; font-size: 9pt; white-space: pre-wrap;'>{LICENSE_TEXT}</pre>")
        txt.setStyleSheet(
            "border: 1px solid #d0d7e3; border-radius: 4px; "
            "background: white; padding: 8px;"
        )
        txt.setMinimumHeight(220)
        layout.addWidget(txt)

        # Botón ver licencia completa online
        btn_row = QHBoxLayout()
        btn_full = QPushButton()
        btn_full.setIcon(qta.icon('fa5s.external-link-alt', color='white'))
        btn_full.setText("  Ver licencia completa")
        btn_full.setStyleSheet(
            "background-color: #37474f; color: white; font-weight: bold; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        btn_full.setCursor(Qt.PointingHandCursor)
        btn_full.setToolTip("Abre https://www.gnu.org/licenses/gpl-3.0.html")
        btn_full.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://www.gnu.org/licenses/gpl-3.0.html")
            )
        )

        btn_close = QPushButton("  Cerrar")
        btn_close.setIcon(qta.icon('fa5s.times', color='#555'))
        btn_close.setStyleSheet(
            "background-color: #e0e0e0; color: #333; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(dlg.accept)

        btn_row.addWidget(btn_full)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.setLayout(layout)
        dlg.exec_()

    def _show_donate_dialog(self, parent=None):
        # Muestra opciones de donación
        dlg = QDialog(parent or self)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dlg.setWindowTitle("Donar — Apoya el proyecto")
        dlg.setMinimumWidth(400)
        dlg.setStyleSheet("QDialog { background-color: #f5f5f5; }")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(14)
        
        title = QLabel("❤️  Apoya el Proyecto")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #c0392b;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("Si este proyecto te ha sido útil, considera apoyarlo.\n"
                      "Cualquier contribución es muy apreciada 🙏")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 9pt;")
        layout.addWidget(desc)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(sep)
        
        # Opción 1: MercadoPago
        btn_mp = QPushButton()
        btn_mp.setIcon(qta.icon('fa5s.credit-card', color='white'))
        btn_mp.setText("   MercadoPago")
        btn_mp.setStyleSheet(
            "background-color: #009ee3; color: white; font-weight: bold; "
            "padding: 10px; border-radius: 6px; font-size: 10pt;"
        )
        btn_mp.setCursor(Qt.PointingHandCursor)
        btn_mp.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://link.mercadopago.cl/fernandobc"))
        )
        layout.addWidget(btn_mp)
        
        # Opción 2: PayPal
        btn_pp = QPushButton()
        btn_pp.setIcon(qta.icon('fa5b.paypal', color='white'))
        btn_pp.setText("   PayPal")
        btn_pp.setStyleSheet(
            "background-color: #003087; color: white; font-weight: bold; "
            "padding: 10px; border-radius: 6px; font-size: 10pt;"
        )
        btn_pp.setCursor(Qt.PointingHandCursor)
        btn_pp.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.paypal.com/donate/?hosted_button_id=V8EZ3BGE8JZWS"))
        )
        layout.addWidget(btn_pp)
        
        layout.addStretch()
        
        btn_close = QPushButton("  Cerrar")
        btn_close.setIcon(qta.icon('fa5s.times', color='#555'))
        btn_close.setStyleSheet(
            "background-color: #e0e0e0; color: #333; padding: 6px 18px; border-radius: 4px;"
        )
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(dlg.accept)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)
        
        dlg.setLayout(layout)
        dlg.exec_()
    
    def _show_suggestions_dialog(self, parent=None):
        """Diálogo de sugerencias rediseñado: categoría, asunto, mensaje y copia rápida."""
        CONTACT_EMAIL = "famv.dev@gmail.com"

        dlg = QDialog(parent or self)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dlg.setWindowTitle("Enviar Sugerencia")
        dlg.setMinimumWidth(460)
        dlg.setMinimumHeight(480)
        dlg.setStyleSheet("""
            QDialog { background-color: #f0f4f8; }
            QLabel#hdr {
                font-size: 13pt;
                font-weight: bold;
                color: #1565C0;
            }
            QLabel#sub {
                font-size: 9pt;
                color: #555;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 9pt;
                border: 1px solid #d0d7e3;
                border-radius: 6px;
                margin-top: 8px;
                padding: 10px 8px 8px 8px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #1565C0;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #c5cfe0;
                border-radius: 4px;
                padding: 5px 8px;
                background: white;
                font-size: 9pt;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1.5px solid #1565C0;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 14)
        main_layout.setSpacing(10)

        # ── Cabecera ─────────────────────────────────────────────────────────
        hdr = QLabel("Sugerencias y Reportes")
        hdr.setObjectName("hdr")
        hdr.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hdr)

        sub = QLabel("Tus comentarios ayudan a mejorar la aplicación.")
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #c5cfe0;")
        main_layout.addWidget(sep)

        # ── Categoría ────────────────────────────────────────────────────────
        grp_form = QGroupBox("Redactar mensaje")
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        cat_row = QHBoxLayout()
        cat_lbl = QLabel("Categoría:")
        cat_lbl.setFixedWidth(72)
        combo_cat = QComboBox()
        combo_cat.addItems([
            "💡 Sugerencia de mejora",
            "🐛 Reporte de error (bug)",
            "❓ Consulta general",
            "🎨 Mejora de diseño",
            "🔒 Seguridad",
        ])
        combo_cat.setMinimumHeight(30)
        cat_row.addWidget(cat_lbl)
        cat_row.addWidget(combo_cat)
        form_layout.addLayout(cat_row)

        # ── Asunto ───────────────────────────────────────────────────────────
        sub_row = QHBoxLayout()
        sub_lbl = QLabel("Asunto:")
        sub_lbl.setFixedWidth(72)
        txt_subject = QLineEdit()
        txt_subject.setPlaceholderText("Breve descripción del tema...")
        txt_subject.setMinimumHeight(30)
        sub_row.addWidget(sub_lbl)
        sub_row.addWidget(txt_subject)
        form_layout.addLayout(sub_row)

        # ── Mensaje ──────────────────────────────────────────────────────────
        msg_lbl = QLabel("Mensaje:")
        form_layout.addWidget(msg_lbl)
        txt_msg = QTextEdit()
        txt_msg.setPlaceholderText(
            "Describe tu sugerencia o reporte con el mayor detalle posible...\n\n"
            "Si es un error, incluye: ¿qué hiciste? ¿qué esperabas? ¿qué ocurrió?"
        )
        txt_msg.setMinimumHeight(120)
        form_layout.addWidget(txt_msg)

        grp_form.setLayout(form_layout)
        main_layout.addWidget(grp_form)

        # Instrucciones para el usuario
        grp_inst = QGroupBox("Cómo enviar")
        inst_layout = QVBoxLayout()
        inst_layout.setSpacing(4)
        for step in [
            "1. Completa la categoría, asunto y mensaje.",
            "2. Haz clic en  \"Copiar todo\"  para copiar el email + contenido.",
            "3. Abre tu cliente de correo (Outlook, Gmail, etc.)",
            "4. Pega el contenido y envíalo a la dirección copiada.",
        ]:
            lbl = QLabel(step)
            lbl.setStyleSheet("font-size: 8.5pt; color: #444;")
            inst_layout.addWidget(lbl)

        # Email copyable
        email_row = QHBoxLayout()
        email_lbl = QLabel(f"<b>Destino:</b> <code>{CONTACT_EMAIL}</code>")
        email_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        email_lbl.setCursor(Qt.IBeamCursor)
        email_lbl.setStyleSheet("font-size: 9pt;")

        btn_copy_email = QPushButton()
        btn_copy_email.setIcon(qta.icon('fa5s.copy', color='#1565C0'))
        btn_copy_email.setToolTip("Copiar solo el email")
        btn_copy_email.setFixedSize(28, 28)
        btn_copy_email.setStyleSheet("border: none; background: transparent;")
        btn_copy_email.setCursor(Qt.PointingHandCursor)

        def _copy_email():
            QApplication.clipboard().setText(CONTACT_EMAIL)
            btn_copy_email.setIcon(qta.icon('fa5s.check', color='green'))
            QTimer.singleShot(1500, lambda: btn_copy_email.setIcon(
                qta.icon('fa5s.copy', color='#1565C0')))
        btn_copy_email.clicked.connect(_copy_email)

        email_row.addWidget(email_lbl)
        email_row.addStretch()
        email_row.addWidget(btn_copy_email)
        inst_layout.addLayout(email_row)
        grp_inst.setLayout(inst_layout)
        main_layout.addWidget(grp_inst)

        # ── Botones ──────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_copy_all = QPushButton()
        btn_copy_all.setIcon(qta.icon('fa5s.clipboard', color='white'))
        btn_copy_all.setText("  Copiar todo")
        btn_copy_all.setStyleSheet(
            "background-color: #1565C0; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 4px;"
        )
        btn_copy_all.setCursor(Qt.PointingHandCursor)
        btn_copy_all.setToolTip("Copia email + asunto + mensaje al portapapeles")

        def _copy_all():
            cat = combo_cat.currentText()
            subj = txt_subject.text().strip() or "(sin asunto)"
            body = txt_msg.toPlainText().strip() or "(sin mensaje)"
            full = (
                f"Para: {CONTACT_EMAIL}\n"
                f"Categoría: {cat}\n"
                f"Asunto: {subj}\n"
                f"{'─' * 40}\n"
                f"{body}"
            )
            QApplication.clipboard().setText(full)
            btn_copy_all.setText("  ¡Copiado!")
            btn_copy_all.setStyleSheet(
                "background-color: #2e7d32; color: white; font-weight: bold; "
                "padding: 8px 16px; border-radius: 4px;"
            )
            QTimer.singleShot(2000, lambda: (
                btn_copy_all.setText("  Copiar todo"),
                btn_copy_all.setStyleSheet(
                    "background-color: #1565C0; color: white; font-weight: bold; "
                    "padding: 8px 16px; border-radius: 4px;"
                )
            ))
        btn_copy_all.clicked.connect(_copy_all)

        # Botón Abrir correo: abre el cliente de correo pre-rellenado (si lo hay)
        btn_open_mail = QPushButton()
        btn_open_mail.setIcon(qta.icon('fa5s.envelope-open-text', color='white'))
        btn_open_mail.setText("  Abrir correo")
        btn_open_mail.setStyleSheet(
            "background-color: #6a1b9a; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 4px;"
        )
        btn_open_mail.setCursor(Qt.PointingHandCursor)
        btn_open_mail.setToolTip(
            "Abre tu cliente de correo con el mensaje pre-cargado\n"
            "(requiere un cliente de correo configurado como predeterminado)"
        )

        def _open_mail():
            cat_raw = combo_cat.currentText()
            # Quitar emojis: tomar solo el texto después del primer espacio
            cat_clean = cat_raw.split(' ', 1)[-1] if ' ' in cat_raw else cat_raw
            subj = txt_subject.text().strip() or "Sugerencia Printer Counter"
            body = txt_msg.toPlainText().strip()
            full_subject = quote(f"[Printer Counter] {cat_clean} - {subj}")
            full_body = quote(body if body else "(escribe aqui tu mensaje)")
            mailto_url = f"mailto:{CONTACT_EMAIL}?subject={full_subject}&body={full_body}"
            QDesktopServices.openUrl(QUrl(mailto_url))
        btn_open_mail.clicked.connect(_open_mail)

        btn_close = QPushButton("  Cerrar")
        btn_close.setIcon(qta.icon('fa5s.times', color='#555'))
        btn_close.setStyleSheet(
            "background-color: #e0e0e0; color: #333; padding: 8px 16px; border-radius: 4px;"
        )
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(dlg.accept)

        btn_row.addWidget(btn_copy_all)
        btn_row.addWidget(btn_open_mail)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        main_layout.addLayout(btn_row)

        dlg.setLayout(main_layout)
        dlg.exec_()

