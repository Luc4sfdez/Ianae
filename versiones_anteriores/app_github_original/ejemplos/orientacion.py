"""Ejemplo de orientación de imágenes con IANAE"""

try:
    from ianae.ianae_visual import IANAEVisual
except ImportError:
    from ..ianae_visual import IANAEVisual
from torchvision import transforms
import os

# 1. Inicializar sistema visual
ianae_vis = IANAEVisual()

# 2. Definir conceptos de orientación
CONCEPTOS_ORIENTACION = [
    "orientacion_0", "orientacion_90", 
    "orientacion_180", "orientacion_270",
    "horizontal", "vertical"
]

# 3. Crear dataset de ejemplo (rutas a imágenes)
DATASET_EJEMPLO = {
    "orientacion_0": ["ejemplos/imagenes/horizontal_1.jpg"],
    "orientacion_90": ["ejemplos/imagenes/vertical_1.jpg"],
    "orientacion_180": ["ejemplos/imagenes/horizontal_2.jpg"],
    "orientacion_270": ["ejemplos/imagenes/vertical_2.jpg"]
}

def entrenar_sistema(sistema, dataset):
    """Entrena IANAE con imágenes de ejemplo"""
    print("Entrenando sistema de orientación...")
    
    for clase, rutas_imagenes in dataset.items():
        print(f"\nProcesando clase: {clase}")
        
        for ruta in rutas_imagenes:
            if not os.path.exists(ruta):
                print(f"Advertencia: {ruta} no existe")
                continue
                
            # Extraer características
            vector = sistema.extraer_caracteristicas(ruta)
            
            # Crear concepto (usando nombre de archivo como ID)
            nombre = os.path.splitext(os.path.basename(ruta))[0]
            concepto = sistema.crear_concepto_visual(nombre, vector_visual=vector)
            
            print(f"- Procesada: {ruta}")
    
    print("\nEntrenamiento completado")

if __name__ == "__main__":
    entrenar_sistema(ianae_vis, DATASET_EJEMPLO)
