# Gestión de configuración y rutas del aplicativo.


import json
from pathlib import Path
import os
import sys

CONFIG_FILE = "app_config.json"

# Configuración por defecto
DEFAULT_CONFIG = {
    "use_smb": True,
    "smb_path": "\\\\192.168.1.241\\printers_snmp",
    "json_filename": "printers.json",
    "language": "es",
    "snmp_community": "public",
    "snmp_timeout": 1,
    "snmp_retries": 1
}


class ConfigManager:
    # Gestiona la configuración de la aplicación
    
    def __init__(self):
        # Determinar la carpeta base para guardar configuración
        if getattr(sys, 'frozen', False):
            # Estamos en PyInstaller
            self.base_path = os.path.dirname(sys.executable)
        else:
            # Estamos en desarrollo
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.config_file = os.path.join(self.base_path, "app_config.json")
        self.config = self.load_config()
    
    def load_config(self):
        # Carga la configuración desde archivo
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        # Guarda la configuración a archivo
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def get(self, key, default=None):
        # Obtiene un valor de configuración
        return self.config.get(key, default)
    
    def set(self, key, value):
        # Establece un valor de configuración
        self.config[key] = value
        self.save_config()
    
    def get_json_path(self):
        # Retorna la ruta completa al archivo printers.json
        if self.config.get("use_smb", False):
            smb_path = self.config.get("smb_path", "").rstrip("\\")
            filename = self.config.get("json_filename", "printers.json")
            return f"{smb_path}\\{filename}"
        else:
            # En modo local, usar la carpeta base
            local_path = Path(self.base_path) / self.config.get("json_filename", "printers.json")
            return str(local_path)
    
    def validate_smb_path(self, smb_path):
        # Valida si la ruta SMB es accesible
        try:
            # Intenta acceder a la ruta
            if os.path.exists(smb_path):
                return True, "Ruta accesible"
            else:
                return False, "Ruta no accesible o no existe"
        except PermissionError:
            return False, "Acceso denegado (permisos insuficientes)"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def test_connection(self):
        # Prueba la conexión a la ruta configurada
        json_path = self.get_json_path()
        try:
            # Intenta acceder al directorio
            path_obj = Path(json_path).parent
            if path_obj.exists():
                return True, "Conexión OK"
            else:
                return False, "No se puede acceder a la ruta"
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"


# Instancia global
config = ConfigManager()
