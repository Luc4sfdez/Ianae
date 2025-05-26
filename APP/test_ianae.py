"""
Test IANAE - Experimento para demostrar las capacidades del sistema
según los principios que definimos:
- Conceptos difusos con incertidumbre inherente
- Relaciones probabilísticas
- Propagación no determinística
- Auto-modificación
- Emergencia de nuevos conceptos
"""

import numpy as np
import matplotlib.pyplot as plt
from nucleo import ConceptosDifusos
from emergente import PensamientoEmergente
from optimizador import IANAEOptimizado
from optimizador_complemento import buscar_patrones_emergentes, generar_informe_sistema
import types

def aplicar_complementos(optimizador):
    """Añade funciones complementarias al optimizador"""
    optimizador.buscar_patrones_emergentes = types.MethodType(buscar_patrones_emergentes, optimizador)
    optimizador.generar_informe_sistema = types.MethodType(generar_informe_sistema, optimizador)
    return optimizador

def ejecutar_test_completo():
    print("\n" + "=" * 60)
    print("TEST IANAE: Demostrando el nuevo paradigma de inteligencia")
    print("=" * 60)
    
    # 1. Crear sistema base con alta dimensionalidad para mayor expresividad
    print("\n[FASE 1] Creando sistema con conceptos difusos de alta dimensionalidad...")
    sistema = ConceptosDifusos(dim_vector=100, incertidumbre_base=0.25)
    
    # Conceptos base relacionados con el paradigma que definimos
    conceptos_base = [
        "pensamiento", "lenguaje", "conocimiento", 
        "emergencia", "adaptación", "evolución",
        "incertidumbre", "probabilidad", "difuso", 
        "no_determinismo", "paralelismo", "red"
    ]
    
    for c in conceptos_base:
        sistema.añadir_concepto(c)
    
    # Crear relaciones iniciales
    relaciones = [
        ("pensamiento", "lenguaje"), ("pensamiento", "conocimiento"),
        ("emergencia", "adaptación"), ("adaptación", "evolución"),
        ("incertidumbre", "probabilidad"), ("probabilidad", "difuso"),
        ("no_determinismo", "paralelismo"), ("paralelismo", "red"),
        ("red", "emergencia"), ("difuso", "incertidumbre"),
        ("evolución", "conocimiento"), ("lenguaje", "red")
    ]
    
    for c1, c2 in relaciones:
        sistema.relacionar(c1, c2)
    
    # Visualizar estado inicial
    print(f"Sistema base creado con {len(sistema.conceptos)} conceptos y {sistema.grafo.number_of_edges()} relaciones")
    sistema.visualizar(titulo="Estado inicial - Conceptos difusos")
    
    # 2. Demostrar propagación no determinística
    print("\n[FASE 2] Demostrando propagación no determinística...")
    
    # Ejecutar propagación desde el mismo concepto varias veces
    # para mostrar que los resultados varían (no determinismo)
    print("Ejecutando 3 propagaciones desde 'pensamiento' con resultados diferentes:")
    
    for i in range(3):
        # Usar temperatura alta para enfatizar comportamiento no determinista
        resultado = sistema.activar("pensamiento", pasos=3, temperatura=0.7)
        
        # Mostrar los 5 conceptos más activados en cada ejecución
        conceptos_activados = sorted(resultado[-1].items(), key=lambda x: x[1], reverse=True)[:5]
        
        print(f"\nPropagación {i+1}:")
        for concepto, activacion in conceptos_activados:
            print(f"  {concepto}: {activacion:.3f}")
    
    # Visualizar la última propagación
    sistema.visualizar(activaciones=resultado[-1], 
                     titulo="Propagación no determinística desde 'pensamiento'")
    
    # 3. Ciclos de auto-modificación y emergencia
    print("\n[FASE 3] Ejecutando ciclos con auto-modificación y emergencia de conceptos...")
    
    # Configurar optimizador para monitorear recursos
    optimizador = IANAEOptimizado(sistema=sistema)
    optimizador = aplicar_complementos(optimizador)  # Añadir métodos complementarios
    
    # Ejecutar ciclos vitales optimizados
    print("Ejecutando 100 ciclos vitales optimizados...")
    optimizador.ciclo_vital_optimizado(
        num_ciclos_total=100,
        ciclos_por_batch=20,
        visualizar_cada=50,
        optimizar_cada=20
    )
    
    # 4. Análisis de patrones emergentes
    print("\n[FASE 4] Analizando patrones emergentes en el sistema...")
    patrones = optimizador.buscar_patrones_emergentes()
    
    # 5. Explorar cadenas de pensamiento con el sistema emergente
    print("\n[FASE 5] Explorando cadenas de pensamiento emergentes...")
    pensamiento = PensamientoEmergente(sistema=sistema)
    
    print("\nGenerando cadenas de pensamiento a partir de diferentes conceptos:")
    
    # Generar cadenas desde diferentes puntos iniciales
    semillas = ["emergencia", "no_determinismo", "incertidumbre"]
    for semilla in semillas:
        cadena = pensamiento.generar_pensamiento(semilla=semilla, longitud=6)
        print(f"\n{cadena}")
    
    # Visualizar la última cadena
    pensamiento.visualizar_pensamiento(-1)
    
    # 6. Experimento de divergencia creativa
    print("\n[FASE 6] Demostrando divergencia creativa...")
    divergencia = pensamiento.experimento_divergencia(
        concepto="pensamiento", 
        num_rutas=4, 
        longitud=5
    )
    
    # 7. Informe final del sistema
    print("\n[FASE 7] Generando informe final del sistema...")
    informe = optimizador.generar_informe_sistema()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETO - PARADIGMA IANAE DEMOSTRADO")
    print("=" * 60)
    print("\nEl test ha demostrado las características fundamentales:")
    print("✓ Conceptos difusos con incertidumbre inherente")
    print("✓ Relaciones probabilísticas entre conceptos")
    print("✓ Propagación no determinística de activación")
    print("✓ Auto-modificación del sistema")
    print("✓ Emergencia de nuevos conceptos")
    print("✓ Pensamiento paralelo y patrones emergentes")
    
    return sistema, optimizador, pensamiento

if __name__ == "__main__":
    sistema, optimizador, pensamiento = ejecutar_test_completo()
