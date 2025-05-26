import os
import sys
from nucleo import ConceptosDifusos
from emergente import PensamientoEmergente

def ejecutar_experimento():
    """
    Ejecuta un experimento completo con IANAE mostrando sus capacidades
    """
    print("=== Experimento IANAE: Inteligencia Adaptativa No Algorítmica Emergente ===")
    print("Este experimento demostrará las capacidades del sistema IANAE")
    
    # Crear sistema base
    print("\n[1/6] Creando sistema conceptual base...")
    sistema = ConceptosDifusos(dim_vector=15)
    
    # Conceptos iniciales relacionados con inteligencia y emergencia
    conceptos_base = [
        "pensamiento", "lenguaje", "conocimiento", "consciencia",
        "emergencia", "adaptación", "evolución", "creatividad",
        "intuición", "abstracción", "patrón", "complejidad",
        "aprendizaje", "memoria", "percepción", "razonamiento"
    ]
    
    for c in conceptos_base:
        sistema.añadir_concepto(c)
    
    # Establecer relaciones semánticas
    relaciones = [
        ("pensamiento", "lenguaje"), ("pensamiento", "razonamiento"),
        ("lenguaje", "conocimiento"), ("consciencia", "percepción"),
        ("emergencia", "complejidad"), ("adaptación", "evolución"),
        ("evolución", "aprendizaje"), ("creatividad", "intuición"),
        ("abstracción", "patrón"), ("patrón", "complejidad"),
        ("aprendizaje", "memoria"), ("memoria", "conocimiento"),
        ("percepción", "intuición"), ("razonamiento", "abstracción")
    ]
    
    for c1, c2 in relaciones:
        sistema.relacionar(c1, c2)
    
    print(f"Sistema base creado con {len(sistema.conceptos)} conceptos y {sistema.grafo.number_of_edges()} relaciones")
    sistema.visualizar(titulo="Sistema conceptual inicial")
    
    # Crear sistema de pensamiento emergente
    pensamiento = PensamientoEmergente(sistema=sistema)
    
    # Importar conceptos de un texto
    print("\n[2/6] Importando conceptos adicionales desde texto...")
    
    # Texto de ejemplo sobre inteligencia emergente
    texto_ejemplo = """
    La inteligencia emergente es un fenómeno donde comportamientos complejos surgen de sistemas 
    simples interconectados. A diferencia de los sistemas algorítmicos tradicionales, los sistemas 
    emergentes no siguen reglas rígidas predefinidas, sino que desarrollan comportamientos adaptativos 
    a través de interacciones dinámicas entre sus componentes.
    
    En la naturaleza, encontramos ejemplos fascinantes como las colonias de hormigas, donde miles 
    de individuos siguiendo reglas simples crean estructuras y comportamientos colectivos sofisticados. 
    También vemos emergencia en los patrones de vuelo de las bandadas de pájaros, en las redes neuronales 
    del cerebro, y en los ecosistemas complejos.
    
    Los sistemas emergentes demuestran propiedades como auto-organización, adaptabilidad, robustez 
    y capacidad para evolucionar. Estas características los hacen especialmente interesantes para 
    el desarrollo de nuevos paradigmas de inteligencia artificial que superen las limitaciones de 
    los enfoques deterministas.
    
    La creatividad puede considerarse un fenómeno emergente, donde nuevas ideas surgen de la 
    combinación inesperada de conceptos existentes. La consciencia misma podría ser una propiedad 
    emergente de redes neuronales suficientemente complejas e interconectadas.
    
    El futuro de la inteligencia artificial probablemente incorporará principios de sistemas emergentes, 
    permitiendo a las máquinas desarrollar capacidades que no fueron explícitamente programadas, 
    sino que emergen naturalmente de su arquitectura y experiencia.
    """
    
    conceptos_importados = pensamiento.cargar_conceptos_desde_texto(texto_ejemplo)
    print(f"Importados {len(conceptos_importados)} conceptos nuevos")
    sistema.visualizar(titulo="Sistema después de importar conceptos")
    
    # Explorar asociaciones
    print("\n[3/6] Explorando asociaciones conceptuales...")
    resultado = pensamiento.explorar_asociaciones("emergencia", profundidad=3, anchura=6)
    print(resultado)
    
    # Visualizar la última exploración
    pensamiento.visualizar_pensamiento(-1)
    
    # Generar cadenas de pensamiento
    print("\n[4/6] Generando cadenas de pensamiento...")
    for i in range(3):
        pensamiento_generado = pensamiento.generar_pensamiento(longitud=6)
        print(f"\nCadena {i+1}:")
        print(pensamiento_generado)
    
    # Visualizar el último pensamiento
    pensamiento.visualizar_pensamiento(-1)
    
    # Asociar conceptos
    print("\n[5/6] Buscando asociaciones entre conceptos...")
    conceptos_a_asociar = [
        ("emergencia", "creatividad"),
        ("inteligencia", "adaptación"),
        ("consciencia", "complejidad")
    ]
    
    for c1, c2 in conceptos_a_asociar:
        resultado = pensamiento.asociar_conceptos(c1, c2)
        print(f"\n{resultado}")
    
    # Experimento de divergencia
    print("\n[6/6] Realizando experimento de divergencia creativa...")
    resultado = pensamiento.experimento_divergencia("creatividad", num_rutas=4, longitud=5)
    print(resultado)
    
    # Ciclo de vida del sistema
    print("\n[Bonus] Ejecutando ciclo de vida autónomo...")
    print("El sistema evolucionará durante 10 ciclos, auto-modificándose y generando nuevos conceptos")
    sistema.ciclo_vital(num_ciclos=10, visualizar_cada=5)
    
    # Guardar el sistema
    if input("\n¿Guardar el sistema para uso futuro? (s/n): ").lower().startswith('s'):
        sistema.guardar('ianae_experimento.json')
        print("Sistema guardado en 'ianae_experimento.json'")
    
    print("\n=== Experimento completado ===")
    print("Has visto las capacidades básicas de IANAE. Para continuar explorando,")
    print("puedes usar los módulos nucleo.py y emergente.py en tus propios scripts")
    print("o ejecutar main.py para la interfaz interactiva.")

if __name__ == "__main__":
    # Comprobar si se solicita directamente el experimento completo
    if len(sys.argv) > 1 and sys.argv[1] == 'completo':
        ejecutar_experimento()
    else:
        # Mostrar menú interactivo por defecto
        menu_experimentos()
