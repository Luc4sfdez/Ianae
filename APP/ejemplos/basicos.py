"""Ejemplo básico de datos para entrenar IANAE"""

# Conceptos iniciales
CONCEPTOS_INICIALES = {
    "pensamiento": {
        "vector": [0.9, 0.1, 0.3, 0.5],
        "activaciones": 10
    },
    "aprendizaje": {
        "vector": [0.2, 0.8, 0.4, 0.6], 
        "activaciones": 5
    }
}

# Relaciones iniciales 
RELACIONES_INICIALES = {
    "pensamiento": [("aprendizaje", 0.7)],
    "aprendizaje": [("pensamiento", 0.5)]
}

# Texto de ejemplo para procesamiento
TEXTO_EJEMPLO = '''
El pensamiento y el aprendizaje son procesos cognitivos fundamentales.
Un buen sistema de IA debe combinar ambos aspectos.
'''
