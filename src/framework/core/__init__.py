# Core module 
#!/usr/bin/env python3
"""
core/__init__.py - Módulo core de IANAE
Componentes principales del sistema
"""

from .database import IANAEDatabase, create_database
from .manager import IANAECore, create_ianae_system

__version__ = "1.0.0"
__author__ = "Lucas - IANAE System"

# Exports principales
__all__ = [
    'IANAEDatabase',
    'create_database', 
    'IANAECore',
    'create_ianae_system'
]