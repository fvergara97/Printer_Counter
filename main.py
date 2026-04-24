# Printer Counter v1.0 — Punto de entrada principal.
#
# Uso:
#     python main.py
#
# Compilar para Windows:
#     pyinstaller --onefile --windowed --icon=Icon.ico --add-data "printers.json;." --add-data "Icon.ico;." main.py
#
# Compilar para macOS:
#     pyinstaller --onefile --windowed --icon=Icon.icns --add-data "printers.json:." --add-data "Icon.icns:." main.py
import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication

#Configurar logging global (antes de importar módulos de la app) 
LOG_FILE = Path(__file__).parent / "printer_counter.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("Iniciando aplicación Printer Counter")
logger.info("=" * 80)

#Importar ventana principal (después de logging)
from ui.main_window import PrinterDashboard  


def main() -> None:
    app = QApplication(sys.argv)
    dashboard = PrinterDashboard()
    dashboard.refresh_table_from_json()   # Cargar datos iniciales desde JSON
    dashboard.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
