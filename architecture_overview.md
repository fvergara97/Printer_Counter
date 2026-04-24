# Arquitectura y Estructura del Proyecto "Printer_Counter"

**Printer_Counter** nace de la necesidad de automatizar y centralizar la recolección de contadores, estados de tóner y conexión de múltiples impresoras en red. Mediante el uso del protocolo SNMP, la herramienta permite recopilar estos datos de forma masiva, optimizando los tiempos de administración y control de equipos de impresión.

Este documento proporciona una vista general de la arquitectura del software, explicando cómo está distribuido el código y de qué manera diseñado lograr este objetivo.

## 🗂️ Árbol de Directorios

```text
Printer_Counter/
├── main.py                     # Punto de entrada de la aplicación
├── printers.json               # Base de datos local (configuraciones e impresoras)
├── build.bat                   # Script de compilación usando PyInstaller
├── core/                       # Lógica de negocio (Backend)
│   ├── snmp_engine.py          # Motor asíncrono de escaneo SNMP
│   └── config.py               # Gestor de configuraciones y rutas (Local/SMB)
└── ui/                         # Interfaz de Usuario (Frontend / PyQt5)
    ├── main_window.py          # Ventana principal que ensambla todos los módulos
    ├── widgets.py              # Componentes visuales personalizados (Notificaciones, Tablas especializadas)
    ├── workers.py              # Hilos de procesamiento (QThread) para no congelar la GUI
    ├── tabs/                   # Lógica de cada pestaña principal
    │   ├── dashboard.py        # Pestaña Principal (Tabla de escaneo y exportación)
    │   ├── models.py           # Pestaña Gestión de Modelos (CRUD)
    │   ├── snmp_config.py      # Pestaña Configuración SNMP
    │   └── storage.py          # Pestaña Ubicación de Archivos
    └── dialogs/                # Ventanas emergentes (Modales)
        ├── printer_dialogs.py  # Ventanas de Agregar/Editar Impresora
        ├── model_dialogs.py    # Ventanas de Agregar/Editar Modelo
        └── about.py            # Ventana de "Acerca de"
```

## 🔄 Flujo de Datos y Ejecución

### 1. El Arranque
- **`main.py`** inicializa el bucle de eventos de PyQt5 levantando `QApplication`.
- `main.py` manda a crear `PrinterDashboard` que ensambla todas las pestañas y la interfaz.
- Al cargar, se lee `core/config.py` para determinar dónde está ubicado el archivo `printers.json` (red local SMB vs Mis Documentos).
- Seguidamente, `dashboard.py` lee `printers.json` pre-dibujando la tabla con las IP almacenadas.

### 2. El Escaneo de Red (El núcleo de tu aplicación)
1. El usuario presiona **Consultar Dispositivos**.
2. Almacenado en `ui/tabs/dashboard.py`, este evento invoca al `SNMPWorker` de `ui/workers.py`.
3. Esto es crítico: **las peticiones web SNMP tardan segundos**.
4. El hilo habla directo con `core/snmp_engine.py`.
5. Dependiendo de lo configurado en la Pestaña SNMP, `snmp_engine.py` utiliza `get_snmp_data_parallel` (todas las IP a la vez velozmente usando `asyncio`) o `get_snmp_data_sequential` (una por una).
6. Una vez la red contesta o agota el `timeout`, el `QThread` emite una "señal" (`pyqtSignal(dict)`) con los resultados de vuelta hacia `dashboard.py`.
7. `dashboard.py` recibe el diccionario e inmensamente actualiza colores, contadores y niveles de tóner en pantalla.

### 3. Agregar o Modificar Datos
- Cuando abres un diálogo (ej.: "Agregar Modelo"), entran en juego los archivos en `ui/dialogs/`.
- Al rellenar información y presionar "Guardar", se lee el archivo físico `printers.json`, se le suma la información como un gran objeto Python en memoria y se sobreescribe el archivo JSON en el disco local o SMB.
- Finalmente, se lanza una señal interna para que las tablas visibles se vuelvan a pintar.

---

## 💻 El Motor SNMP (`core/snmp_engine.py`)

Es la joya técnica del software. 
- Utiliza la biblioteca especializada **`pysnmp`** para enviar peticiones UDP por la red local a los puertos 161 de las máquinas. 
- Trabaja con OIDs (ej: `1.3.6.1.2.1.43.10...`) traduciendo lo que responde el hardware (a nivel hexa) a un formato legible en texto (ASCII string) y números. 
- Tiene manejo pesado de errores previendo que las impresoras puedan estar apagadas, tener otro Community String y lidia con las excepciones sin que nada colapse. 

## 📦 Compilación (`build.bat`)

Se encarga de utilizar PyInstaller para coger todo lo expuesto, suprimir el código fuente original (para crear cerrado comercial) y pegarlo junto con una instancia en miniatura del intérprete subyacente de Python en un único archivo precompilado `Printer_Counter_V1.X.exe`.
