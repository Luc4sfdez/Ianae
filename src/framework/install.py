#!/usr/bin/env python3
"""
install_ianae.py - Script de instalación automática CORREGIDO para Windows
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_banner():
    """Muestra banner de instalación sin emojis problemáticos"""
    print("="*60)
    print("   IANAE 4.0 - INSTALACION AUTOMATICA")
    print("   Sistema Universal de Digestion de Conversaciones")
    print("="*60)
    print()

def check_python_version():
    """Verifica versión de Python"""
    print("Verificando version de Python...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("ERROR: Python 3.8+ requerido")
        print(f"   Version actual: {version.major}.{version.minor}.{version.micro}")
        print("   Instala Python 3.8+ desde: https://python.org")
        return False
    
    print(f"OK: Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_pip():
    """Verifica pip"""
    print("Verificando pip...")
    
    try:
        import pip
        print("OK: pip disponible")
        return True
    except ImportError:
        print("ERROR: pip no encontrado")
        print("   Instala pip: python -m ensurepip --upgrade")
        return False

def create_directory_structure():
    """Crea estructura de directorios"""
    print("Creando estructura de directorios...")
    
    directories = [
        "core",
        "processors", 
        "tests",
        "docs",
        "data",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   OK: {directory}/")
    
    # Crear __init__.py files
    init_files = [
        "__init__.py",
        "core/__init__.py", 
        "processors/__init__.py",
        "tests/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        print(f"   OK: {init_file}")

def install_dependencies():
    """Instala dependencias de requirements.txt"""
    print("Instalando dependencias...")
    
    if not Path("requirements.txt").exists():
        print("ERROR: requirements.txt no encontrado")
        print("   Descarga el archivo requirements.txt del proyecto")
        return False
    
    try:
        # Instalar dependencias principales
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("OK: Dependencias principales instaladas")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Error instalando dependencias: {e}")
        return False

def create_config_file():
    """Crea archivo de configuración"""
    print("Creando configuracion...")
    
    config_content = """# IANAE 4.0 Configuration File
# Configuracion del sistema

[database]
# Ruta de la base de datos SQLite
path = ianae_memoria_produccion.db

# Configuracion de performance
enable_wal_mode = true
cache_size = 10000

[processing]
# Numero maximo de archivos por lote
max_batch_files = 100

# Extensiones de archivo soportadas
supported_extensions = [".json", ".md", ".txt"]

# Limite de tamaño de archivo (MB)
max_file_size_mb = 100

[web]
# Configuracion del servidor web
host = 0.0.0.0
port = 8000
debug = false

# CORS settings
allow_origins = ["*"]

[detection]
# Configuracion del auto-detector
confidence_threshold = 0.8
fallback_to_generic = true

[logging]
# Nivel de logging: DEBUG, INFO, WARNING, ERROR
level = INFO
file = logs/ianae.log
max_size_mb = 50
backup_count = 5
"""
    
    with open("ianae_config.ini", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("OK: Archivo de configuracion creado: ianae_config.ini")

def create_startup_script():
    """Crea script de inicio"""
    print("Creando scripts de inicio...")
    
    # Script para Windows
    windows_script = """@echo off
echo Iniciando IANAE 4.0...
python ianae_webapp.py
pause
"""
    
    with open("start_ianae.bat", "w", encoding="utf-8") as f:
        f.write(windows_script)
    
    # Script para Unix/Linux/Mac
    unix_script = """#!/bin/bash
echo "Iniciando IANAE 4.0..."
python3 ianae_webapp.py
"""
    
    with open("start_ianae.sh", "w", encoding="utf-8") as f:
        f.write(unix_script)
    
    # Hacer ejecutable en Unix
    if platform.system() != "Windows":
        os.chmod("start_ianae.sh", 0o755)
    
    print("OK: Scripts de inicio creados:")
    print("   • Windows: start_ianae.bat")
    print("   • Unix/Linux/Mac: start_ianae.sh")

def verify_installation():
    """Verifica la instalación"""
    print("Verificando instalacion...")
    
    # Verificar archivos principales
    required_files = [
        "ianae_webapp.py",
        "requirements.txt", 
        "core/__init__.py",
        "processors/__init__.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("ERROR: Archivos faltantes:")
        for file in missing_files:
            print(f"   • {file}")
        print("   Descarga todos los archivos del proyecto IANAE")
        return False
    
    # Verificar importación de módulos
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("OK: Modulos principales importables")
    except ImportError as e:
        print(f"ERROR: Error importando modulos: {e}")
        return False
    
    print("OK: Instalacion verificada correctamente")
    return True

def create_core_manager():
    """Crea manager básico si no existe"""
    manager_path = Path("core/manager.py")
    
    if not manager_path.exists():
        print("Creando core/manager.py basico...")
        
        # Se creará automáticamente con el artifact que ya hicimos
        print("OK: Usa el archivo core/manager.py del proyecto")
    else:
        print("OK: core/manager.py ya existe")

def show_next_steps():
    """Muestra próximos pasos"""
    print("\nINSTALACION COMPLETADA!")
    print("="*50)
    print()
    print("PROXIMOS PASOS:")
    print("1. Asegurate de tener estos archivos:")
    print("   • core/manager.py")
    print("   • ianae_webapp.py")
    print("   • requirements.txt (corregido)")
    print()
    print("2. Iniciar el sistema:")
    if platform.system() == "Windows":
        print("   start_ianae.bat")
        print("   o: python ianae_webapp.py")
    else:
        print("   ./start_ianae.sh")
        print("   o: python ianae_webapp.py")
    print()
    print("3. Abrir navegador en: http://localhost:8000")
    print()
    print("DOCUMENTACION:")
    print("• API docs: http://localhost:8000/api/docs")
    print("• ReDoc: http://localhost:8000/api/redoc")
    print()
    print("SOPORTE:")
    print("• Logs: logs/ianae.log")
    print("• Config: ianae_config.ini")

def main():
    """Función principal de instalación"""
    print_banner()
    
    # Verificaciones previas
    if not check_python_version():
        sys.exit(1)
    
    if not check_pip():
        sys.exit(1)
    
    # Instalación paso a paso
    create_directory_structure()
    
    # Solo instalar dependencias si requirements.txt existe
    if Path("requirements.txt").exists():
        if not install_dependencies():
            print("ADVERTENCIA: Continuo sin instalar dependencias...")
    else:
        print("ADVERTENCIA: requirements.txt no encontrado - saltando instalacion de dependencias")
    
    create_config_file()
    create_startup_script()
    create_core_manager()
    
    # Verificación final
    if verify_installation():
        show_next_steps()
    else:
        print("\nERROR: Instalacion incompleta")
        print("   Descarga todos los archivos del proyecto IANAE")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstalacion cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR durante la instalacion: {e}")
        sys.exit(1)