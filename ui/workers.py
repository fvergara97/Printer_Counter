# Worker thread para consultas SNMP asíncronas (no bloquea la UI).
import logging
from PyQt5.QtCore import QThread, pyqtSignal

import core.snmp_engine as counter

logger = logging.getLogger(__name__)



class SNMPWorker(QThread):
    # Worker thread para ejecutar SNMP sin bloquear la GUI
    finished = pyqtSignal()
    error = pyqtSignal(str)
    data_ready = pyqtSignal(dict)
    
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
    
    def run(self):
        try:
            # Ejecutar la función async en el event loop
            result = self.loop.run_until_complete(counter.get_snmp_data())
            if result:
                self.data_ready.emit(result)
            else:
                self.error.emit("No se pudieron obtener datos SNMP")
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
            self.finished.emit()


