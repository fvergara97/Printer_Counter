# Motor SNMP: consultas SNMP y lectura de JSON.
import asyncio
import json
from datetime import datetime
from pathlib import Path
from pysnmp.hlapi.v3arch.asyncio import (
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    get_cmd
)

try:
    from core.config import config as app_config
except ImportError:
    # Si config.py no está disponible, usar valores por defecto
    class DummyConfig:
        def get_json_path(self):
            return "printers.json"
        def get(self, key, default=None):
            defaults = {"community": "public", "timeout": 1, "retries": 1}
            return defaults.get(key, default)
    app_config = DummyConfig()

#CONFIG

JSON_PATH = app_config.get_json_path()
COMMUNITY = "public"
SNMP_VERSION = 1
TIMEOUT = 1
RETRIES = 1
SNMP_MODE_PARALLEL = True  # True = Paralelo (optimizado) | False = Secuencial (compatible)


def file_exists():
    return Path(JSON_PATH).exists()

def load_json(display=True):
    if not file_exists():
        # Si el archivo no existe en modo local, crearlo automáticamente
        if not app_config.get("use_smb", False):
            try:
                Path(JSON_PATH).parent.mkdir(parents=True, exist_ok=True)
                with open(JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4, ensure_ascii=False)
                if display:
                    print(f"Archivo '{JSON_PATH}' creado automáticamente.")
                return {}
            except Exception as e:
                if display:
                    print(f"Error al crear archivo: {e}")
                return None
        else:
            if display:
                print(f"El archivo '{JSON_PATH}' no existe.")
            return None
    
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Convertir estructura antigua a nueva si es necesario
        return _migrate_json_structure(data)
    except json.JSONDecodeError:
        if display:
            print(f"Error: El archivo '{JSON_PATH}' está corrupto o vacío.")
        return {}
    except Exception as e:
        if display:
            print(f"Error al leer '{JSON_PATH}': {e}")
        return None

def _migrate_json_structure(data):
    # Convierte estructura antigua de printer (lista de strings) a nueva (lista de dicts)
    if not data:
        return data
    
    for brand, info in data.items():
        if isinstance(info, dict) and "printer" in info:
            printers = info["printer"]
            # Si es lista de strings, convertir a lista de dicts
            if printers and isinstance(printers, list) and isinstance(printers[0], str):
                info["printer"] = [
                    {"ip": ip, "custom_name": ip} 
                    for ip in printers
                ]
    return data

def _get_printer_ip(printer_item):
    # Extrae IP de un item printer (compatible con ambas estructuras)
    if isinstance(printer_item, dict):
        return printer_item.get("ip", printer_item)
    return printer_item

def _get_printer_name(printer_item):
    # Extrae nombre personalizado de un item printer
    if isinstance(printer_item, dict):
        return printer_item.get("custom_name", printer_item.get("ip", ""))
    return printer_item

def _get_printer_model(printer_item):
    # Extrae modelo asignado de un item printer
    if isinstance(printer_item, dict):
        return printer_item.get("modelo_asignado", "")
    return ""

def _get_oids_for_printer(brand, modelo_asignado, data):
    # Obtiene los OIDs correctos para una impresora basándose en su modelo o marca
    # Returns: dict con OIDs y opcionalmente toner_model_manual, o {} si no encuentra
    try:
        # Si tiene modelo asignado, intentar obtener OIDs del modelo
        if modelo_asignado and "_modelos" in data:
            modelos_dict = data.get("_modelos", {})
            # Búsqueda case-insensitive por marca
            brand_lower = brand.lower()
            modelos_brand = next(
                (v for k, v in modelos_dict.items() if k.lower() == brand_lower), {}
            )
            # Búsqueda case-insensitive por nombre de modelo
            modelo_lower = modelo_asignado.lower()
            modelo_data = next(
                (v for k, v in modelos_brand.items() if k.lower() == modelo_lower), None
            )
            if modelo_data is not None:
                result = {
                    "counter": modelo_data.get("oid_contador", ""),
                    "name": modelo_data.get("oid_nombre", ""),
                    "toner_current": modelo_data.get("oid_toner_actual", ""),
                    "toner_max": modelo_data.get("oid_toner_maximo", ""),
                    "toner_model": modelo_data.get("oid_modelo_toner", "")
                }
                # Pasar el valor manual si existe
                if "toner_model_manual" in modelo_data and modelo_data["toner_model_manual"]:
                    result["toner_model_manual"] = modelo_data["toner_model_manual"]
                return result
        
        # Si no hay modelo o no se encuentra, usar OIDs por defecto de la marca
        if brand in data and "OID" in data[brand]:
            return data[brand]["OID"]
        
        # Si la marca en minúsculas existe
        brand_lower = brand.lower()
        if brand_lower in data and "OID" in data[brand_lower]:
            return data[brand_lower]["OID"]
        
        return {}
    except Exception as e:
        print(f"ERROR en _get_oids_for_printer({brand}, {modelo_asignado}): {e}")
        return {}

def save_custom_names(custom_names_dict):
    # Guarda nombres personalizados en el JSON: {brand: {ip: custom_name}}
    if not file_exists():
        return False
    
    data = load_json(display=False)
    if not data:
        return False
    
    for brand, ips_dict in custom_names_dict.items():
        if brand in data and "printer" in data[brand]:
            for printer_item in data[brand]["printer"]:
                ip = _get_printer_ip(printer_item)
                if ip in ips_dict:
                    if isinstance(printer_item, dict):
                        printer_item["custom_name"] = ips_dict[ip]
    
    # Guardar en JSON
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return True

def get_mp_model():
    return 0 if SNMP_VERSION == 1 else 1

#SNMP

async def fetch_snmp(ip: str, oid: str) -> str:
    try:
        transport = await UdpTransportTarget.create(
            (ip, 161), timeout=TIMEOUT, retries=RETRIES
        )

        errorIndication, errorStatus, _, varBinds = await get_cmd(
            SnmpEngine(),
            CommunityData(COMMUNITY, mpModel=get_mp_model()),
            transport,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lookupMib=False
        )

        if errorIndication:
            return f"Error: {errorIndication}"
        elif errorStatus:
            return f"Error: {errorStatus.prettyPrint()}"
        else:
            return str(varBinds[0][1])

    except Exception as e:
        return f"Exception: {e}"


async def get_snmp_data_sequential():
    # MODO SECUENCIAL: Consulta impresora por impresora (máxima compatibilidad)
    # Espera a cada consulta antes de pasar a la siguiente
    data = load_json(display=False)
    if not data:
        return None

    result = {}

    for brand, info in data.items():
        # CRÍTICO: Ignorar la clave especial _modelos
        if brand == "_modelos":
            continue
        
        # Validar que info tiene la estructura correcta
        if not isinstance(info, dict) or "printer" not in info:
            continue
        
        # Obtener OIDs con fallback seguro
        oids = info.get("OID", {})
        if not oids:
            print(f"WARNING: No se encontraron OIDs para marca {brand}")
            continue
            
        printers = info["printer"]
        result[brand] = []

        for printer_item in printers:
            try:
                ip = _get_printer_ip(printer_item)
                custom_name = _get_printer_name(printer_item)
                modelo_asignado = _get_printer_model(printer_item)
                
                # Obtener OIDs correctos (del modelo si existe, sino de la marca)
                oids_to_use = _get_oids_for_printer(brand, modelo_asignado, data)
                if not oids_to_use:
                    oids_to_use = oids  # Fallback a OIDs de la marca
                
                row = {"ip": ip, "custom_name": custom_name, "modelo_asignado": modelo_asignado}
                
                # Procesar OIDs normales SECUENCIALMENTE
                for name, oid in oids_to_use.items():
                    if name.startswith("toner_"):  # Los de tóner se procesan aparte
                        continue
                    if not oid or oid.lower() == "oid no definido":
                        row[name] = "OID no definido"
                    else:
                        row[name] = await fetch_snmp(ip, oid)
                
                # Calcular nivel de tóner SECUENCIALMENTE
                toner_current_oid = oids_to_use.get("toner_current", "")
                toner_max_oid = oids_to_use.get("toner_max", "")
                toner_model_oid = oids_to_use.get("toner_model", "")
                
                if toner_current_oid and toner_max_oid:
                    try:
                        current_val = await fetch_snmp(ip, toner_current_oid)
                        max_val = await fetch_snmp(ip, toner_max_oid)
                        
                        try:
                            current = float(current_val) if current_val else 0
                            max_num = float(max_val) if max_val else 0
                            
                            if max_num > 0:
                                percentage = (current / max_num) * 100
                                row["toner_level"] = f"{percentage:.0f}%"
                            else:
                                row["toner_level"] = "--"
                        except (ValueError, TypeError):
                            row["toner_level"] = "--"
                    except Exception:
                        row["toner_level"] = "--"
                else:
                    row["toner_level"] = "--"
                
                # Modelo de tóner SECUENCIAL
                # Prioridad 1: valor manual guardado en el modelo
                toner_model_manual = oids_to_use.get("toner_model_manual", "")
                if toner_model_manual:
                    row["toner_model"] = toner_model_manual
                # Prioridad 2: consultar por OID
                elif toner_model_oid:
                    try:
                        toner_model = await fetch_snmp(ip, toner_model_oid)
                        row["toner_model"] = toner_model if toner_model else "--"
                    except Exception:
                        row["toner_model"] = "--"
                else:
                    row["toner_model"] = "--"
                
                result[brand].append(row)
            except Exception as e:
                print(f"ERROR procesando impresora {ip}: {e}")
                continue

    return result

async def get_snmp_data_parallel():
    # Retorna datos SNMP sin mostrar en consola - Para GUI
    # Ejecuta todas las consultas SNMP EN PARALELO para optimizar tiempo
    data = load_json(display=False)
    if not data:
        return None

    result = {}
    
    # Recolectar todas las tareas asincrónicas
    all_tasks = []

    for brand, info in data.items():
        # CRÍTICO: Ignorar la clave especial _modelos
        if brand == "_modelos":
            continue
        
        # Validar que info tiene la estructura correcta
        if not isinstance(info, dict) or "printer" not in info:
            continue
        
        # Obtener OIDs con fallback seguro
        oids = info.get("OID", {})
        if not oids:
            print(f"WARNING: No se encontraron OIDs para marca {brand}")
            continue
            
        printers = info["printer"]
        result[brand] = [None] * len(printers)  # Pre-asignar espacio

        for printer_idx, printer_item in enumerate(printers):
            try:
                ip = _get_printer_ip(printer_item)
                custom_name = _get_printer_name(printer_item)
                modelo_asignado = _get_printer_model(printer_item)
                
                # Obtener OIDs correctos (del modelo si existe, sino de la marca)
                oids_to_use = _get_oids_for_printer(brand, modelo_asignado, data)
                if not oids_to_use:
                    oids_to_use = oids  # Fallback a OIDs de la marca
                
                # Crear tarea para procesar esta impresora
                async def process_printer(brand_name, printer_idx, ip, custom_name, modelo_asignado, oids_para_usar):
                    try:
                        row = {"ip": ip, "custom_name": custom_name, "modelo_asignado": modelo_asignado}
                        
                        # Recolectar todas las consultas SNMP de esta impresora
                        snmp_tasks = []
                        oid_keys = []
                        
                        # Tareas para OIDs normales (counter, name, etc)
                        for name, oid in oids_para_usar.items():
                            if name.startswith("toner_"):  # Los de tóner se procesan aparte
                                continue
                            if not oid or oid.lower() == "oid no definido":
                                snmp_tasks.append(None)
                                oid_keys.append((name, "OID no definido"))
                            else:
                                snmp_tasks.append(fetch_snmp(ip, oid))
                                oid_keys.append((name, None))
                        
                        # Ejecutar todas las consultas SNMP de una vez
                        if snmp_tasks:
                            results = await asyncio.gather(*snmp_tasks, return_exceptions=True)
                            for (name, default_val), result_val in zip(oid_keys, results):
                                if isinstance(result_val, Exception):
                                    row[name] = "Error"
                                elif default_val:
                                    row[name] = default_val
                                else:
                                    row[name] = result_val
                        
                        # Calcular nivel de tóner EN PARALELO
                        toner_current_oid = oids_para_usar.get("toner_current", "")
                        toner_max_oid = oids_para_usar.get("toner_max", "")
                        toner_model_oid = oids_para_usar.get("toner_model", "")
                        
                        if toner_current_oid and toner_max_oid:
                            try:
                                # Ejecutar ambas consultas EN PARALELO
                                current_val, max_val = await asyncio.gather(
                                    fetch_snmp(ip, toner_current_oid),
                                    fetch_snmp(ip, toner_max_oid)
                                )
                                
                                try:
                                    current = float(current_val) if current_val else 0
                                    max_num = float(max_val) if max_val else 0
                                    
                                    if max_num > 0:
                                        percentage = (current / max_num) * 100
                                        row["toner_level"] = f"{percentage:.0f}%"
                                    else:
                                        row["toner_level"] = "--"
                                except (ValueError, TypeError):
                                    row["toner_level"] = "--"
                            except Exception:
                                row["toner_level"] = "--"
                        else:
                            row["toner_level"] = "--"
                        
                        # Modelo de tóner
                        # Prioridad 1: valor manual guardado en el modelo
                        toner_model_manual = oids_para_usar.get("toner_model_manual", "")
                        if toner_model_manual:
                            row["toner_model"] = toner_model_manual
                        # Prioridad 2: consultar por OID
                        elif toner_model_oid:
                            try:
                                toner_model = await fetch_snmp(ip, toner_model_oid)
                                row["toner_model"] = toner_model if toner_model else "--"
                            except Exception:
                                row["toner_model"] = "--"
                        else:
                            row["toner_model"] = "--"
                        
                        return (brand_name, printer_idx, row)
                    except Exception as e:
                        print(f"ERROR en process_printer({ip}): {e}")
                        return (brand_name, printer_idx, None)
                
                all_tasks.append(process_printer(brand, printer_idx, ip, custom_name, modelo_asignado, oids_to_use))
            except Exception as e:
                print(f"ERROR preparando tarea para {brand}: {e}")
                continue

    # Ejecutar TODAS las impresoras EN PARALELO
    if all_tasks:
        printer_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        for item in printer_results:
            if isinstance(item, Exception):
                print(f"ERROR en tarea paralela: {item}")
                continue
            if item is None:
                continue
            brand_name, printer_idx, row = item
            if row is not None:
                result[brand_name][printer_idx] = row
    
    # Limpiar None values
    for brand in result:
        result[brand] = [r for r in result[brand] if r is not None]

    return result

async def get_snmp_data():
    # Wrapper que elige entre modo paralelo y secuencial basado en SNMP_MODE_PARALLEL
    if SNMP_MODE_PARALLEL:
        return await get_snmp_data_parallel()
    else:
        return await get_snmp_data_sequential()

