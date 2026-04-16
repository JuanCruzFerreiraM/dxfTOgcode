# Generador de G-Code para Impresoras 3D de Gran Escala

[![Versión](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/JuanCruzFerreiraM/dxfTOgcode/releases)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
[![Licencia](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Módulos actuales

- ✅ Conversor de capas 2D — **completo**
- ⏳ GUI para conversor 2D — **completo**
- ⏳ Slicer IFC — **completo**

## Roadmap

- `v1.0.0`: GUI para el conversor 2D
- `v2.0.0`: GUI completa e integración total con IFC

## 🛠️ Instalación

Para clonar y preparar el entorno de trabajo local de este proyecto, seguí estos pasos:

### Requisitos previos

- Tener instalado **Python 3.8** o superior.  
- Tener instalado **pip** (el gestor de paquetes de Python).

### 1. Clonar el repositorio

```bash
git clone https://github.com/JuanCruzFerreiraM/dxfTOgcode.git
cd dxfTOgcode
```

### 2. Crear un entorno virtual (opcional pero recomendado)

```bash
python -m venv venv
source venv/bin/activate      # En Linux / macOS
venv\Scripts\activate         # En Windows
```

### 3. Instalar las dependencias del proyecto

```bash
pip install -r requirements.txt
```

### Ejecutable Windows (PyInstaller, modo onedir)

En un entorno con todas las dependencias instaladas:

```bash
pip install pyinstaller
pyinstaller --clean CAMUNLP.spec
```

La aplicación queda en `dist/CAMUNLP/CAMUNLP.exe` junto con la carpeta interna de dependencias. No se usa modo onefile.

Diagnóstico opcional del pipeline IFC: definir la variable de entorno `CAMUNLP_DEBUG=1` antes de arrancar.

## Licencia

Este proyecto fue desarrollado por Juan Cruz Ferreira Monteiro, en representación del LEICI-UNLP.
El código se publica bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.
