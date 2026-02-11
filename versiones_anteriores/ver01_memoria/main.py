import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from nucleo import ConceptosDifusos

def main():
    """Función principal para iniciar IANAE.
    
    Maneja el flujo principal de la aplicación:
    - Carga/creación del sistema
    - Menú interactivo
    - Ejecución de operaciones
    
    Returns:
        None
    """
    print("Iniciando IANAE - Inteligencia Adaptativa No Algorítmica Emergente")
    print("=" * 60)
    
    # Comprobar si hay un estado guardado
    if os.path.exists('ianae_estado.json'):
        print("Detectado estado previo. ¿Deseas cargar el sistema anterior? (s/n)")
        respuesta = input().lower()
        
        if respuesta.startswith('s'):
            sistema = ConceptosDifusos.cargar('ianae_estado.json')
            print(f"Sistema cargado con {len(sistema.conceptos)} conceptos")
        else:
            sistema = crear_sistema_nuevo()
    else:
        sistema = crear_sistema_nuevo()
    
    # Mostrar menú principal
    while True:
        print("\nMenú Principal de IANAE")
        print("-" * 30)
        print("1. Visualizar estado actual")
        print("2. Añadir concepto")
        print("3. Activar concepto")
        print("4. Ejecutar ciclo de vida")
        print("5. Generar nuevos conceptos")
        print("6. Auto-modificar sistema")
        print("7. Guardar estado actual")
        print("8. Mostrar métricas")
        print("9. Salir")
        # Añadir esta opción al menú principal en main.py

    print("10. Modo Optimizado (experimentos a gran escala)")

    if opcion == '10':
        from optimizador import IANAEOptimizado
        
        print("\nIANAE - Modo Optimizado")
        print("-" * 30)
        print("1. Ejecutar ciclo vital optimizado")
        print("2. Analizar patrones emergentes")
        print("3. Fusionar conceptos similares")
        print("4. Generar informe del sistema")
        print("5. Visualizar métricas de rendimiento")
        
        sub_opcion = input("\nSelecciona una opción: ")
        
        # Crear optimizador con el sistema actual
        optimizador = IANAEOptimizado(sistema=sistema)
        
        if sub_opcion == '1':
            num_ciclos = int(input("Número de ciclos a ejecutar: "))
            vis_cada = int(input("Visualizar cada cuántos ciclos (0 para nunca): "))
            opt_cada = int(input("Optimizar cada cuántos ciclos: "))
            
            optimizador.ciclo_vital_optimizado(
                num_ciclos_total=num_ciclos,
                visualizar_cada=vis_cada,
                optimizar_cada=opt_cada
            )
        
        elif sub_opcion == '2':
            optimizador.buscar_patrones_emergentes()
        
        elif sub_opcion == '3':
            umbral = float(input("Umbral de similitud (0.7-0.9): "))
            umbral = max(0.7, min(0.9, umbral))
            optimizador.fusionar_conceptos_similares(umbral_similitud=umbral)
        
        elif sub_opcion == '4':
            optimizador.generar_informe_sistema()
        
        elif sub_opcion == '5':
            optimizador.visualizar_metricas_rendimiento()
        
        opcion = input("\nSelecciona una opción: ")
        
        try:
            if opcion == '1':
                sistema.visualizar()
                
            elif opcion == '2':
                nombre = input("Nombre del concepto: ")
                sistema.añadir_concepto(nombre)
                print(f"Concepto '{nombre}' añadido")
                
                # Preguntar si se quiere relacionar
                print("¿Relacionar con conceptos existentes? (s/n)")
                if input().lower().startswith('s'):
                    print("Conceptos disponibles:")
                    for idx, c in enumerate(sistema.conceptos.keys()):
                        if c != nombre:
                            print(f"  {idx+1}. {c}")
                    
                    indices = input("Indica índices separados por comas: ")
                    if indices:
                        conceptos_existentes = list(sistema.conceptos.keys())
                        for idx_str in indices.split(','):
                            try:
                                idx = int(idx_str.strip()) - 1
                                if 0 <= idx < len(conceptos_existentes):
                                    otro = conceptos_existentes[idx]
                                    if otro != nombre:
                                        fuerza = sistema.relacionar(nombre, otro)
                                        print(f"Relacionado '{nombre}' con '{otro}' (fuerza: {fuerza:.2f})")
                            except:
                                pass
                
            elif opcion == '3':
                if not sistema.conceptos:
                    print("No hay conceptos para activar")
                    pass
                    
                print("Conceptos disponibles:")
                for idx, c in enumerate(sistema.conceptos.keys()):
                    print(f"  {idx+1}. {c}")
                
                try:
                    idx = int(input("Selecciona un concepto (índice): ")) - 1
                    conceptos = list(sistema.conceptos.keys())
                    
                    if 0 <= idx < len(conceptos):
                        concepto = conceptos[idx]
                        pasos = int(input("Número de pasos de propagación (2-5): "))
                        pasos = max(2, min(5, pasos))
                        
                        print(f"Activando '{concepto}' por {pasos} pasos...")
                        resultado = sistema.activar(concepto, pasos=pasos)
                        
                        # Mostrar resultados
                        sistema.visualizar(activaciones=resultado[-1])
                        
                        # Mostrar conceptos más activados
                        print("\nConceptos más activados:")
                        for c, a in sorted(resultado[-1].items(), key=lambda x: -x[1])[:5]:
                            print(f"  {c}: {a:.3f}")
                    
                except ValueError:
                    print("Entrada inválida")
            
            elif opcion == '4':
                num_ciclos = int(input("Número de ciclos a ejecutar: "))
                visualizar = input("¿Visualizar proceso? (s/n): ").lower().startswith('s')
                
                vis_cada = 0
                if visualizar:
                    vis_cada = max(1, num_ciclos // 5)  # Mostrar hasta 5 visualizaciones
                
                print(f"Ejecutando {num_ciclos} ciclos...")
                sistema.ciclo_vital(num_ciclos=num_ciclos, visualizar_cada=vis_cada)
                print("Ciclos completados")
                
            elif opcion == '5':
                num = int(input("Número de conceptos a generar: "))
                nuevos = sistema.generar_concepto(numero=num)
                
                print(f"Generados {len(nuevos)} nuevos conceptos:")
                for n in nuevos:
                    print(f"  - {n}")
                
                if nuevos and input("¿Visualizar red actualizada? (s/n): ").lower().startswith('s'):
                    sistema.visualizar()
            
            elif opcion == '6':
                fuerza = float(input("Fuerza de auto-modificación (0.1-0.5): "))
                fuerza = max(0.1, min(0.5, fuerza))
                
                modificaciones = sistema.auto_modificar(fuerza=fuerza)
                print(f"Realizadas {modificaciones} modificaciones")
                
                if modificaciones > 0 and input("¿Visualizar cambios? (s/n): ").lower().startswith('s'):
                    sistema.visualizar()
            
            elif opcion == '7':
                ruta = input("Nombre del archivo (o Enter para predeterminado): ")
                if not ruta:
                    ruta = 'ianae_estado.json'
                
                if sistema.guardar(ruta):
                    print(f"Sistema guardado correctamente en '{ruta}'")
                else:
                    print("Error al guardar")
            
            elif opcion == '8':
                print("\nMétricas del Sistema:")
                print("-" * 30)
                for k, v in sistema.metricas.items():
                    print(f"{k.replace('_', ' ').title():.<25} {v}")
                
                # Estadísticas adicionales
                print(f"{'Conceptos Actuales':.<25} {len(sistema.conceptos)}")
                print(f"{'Relaciones Actuales':.<25} {sistema.grafo.number_of_edges()}")
                
                # Conceptos más activos
                if sistema.conceptos:
                    print("\nConceptos más activos:")
                    conceptos_por_activacion = sorted(
                        sistema.conceptos.items(), 
                        key=lambda x: x[1]['activaciones'], 
                        reverse=True
                    )
                    for nombre, datos in conceptos_por_activacion[:5]:
                        print(f"  {nombre}: {datos['activaciones']} activaciones")
            
            elif opcion == '9':
                if input("¿Guardar antes de salir? (s/n): ").lower().startswith('s'):
                    sistema.guardar('ianae_estado.json')
                    print("Sistema guardado")
                
                print("¡Hasta pronto!")
                return
            
            else:
                print("Opción no válida")
                
        except Exception as e:
            print(f"Error: {e}")

def crear_sistema_nuevo():
    """Crea un nuevo sistema IANAE con conceptos iniciales.
    
    Configura:
    - Dimensionalidad de vectores conceptuales
    - Conceptos semilla básicos
    - Relaciones iniciales
    
    Returns:
        ConceptosDifusos: Sistema recién creado
    """
    print("Creando nuevo sistema IANAE...")
    
    # Pedir dimensionalidad
    while True:
        try:
            entrada = input("Dimensionalidad de los vectores conceptuales (10-50, por defecto 10): ")
            if not entrada:
                dim = 10
                break
            dim = int(entrada)
            if 10 <= dim <= 50:
                break
            print("Error: La dimensionalidad debe estar entre 10 y 50")
        except ValueError:
            print("Error: Ingrese un número válido")
        
    # Crear sistema
    sistema = ConceptosDifusos(dim_vector=dim)
    
    # Añadir conceptos semilla
    conceptos_base = [
        "pensamiento", "lenguaje", "conocimiento", 
        "percepción", "memoria", "aprendizaje",
        "abstracción", "patrón", "relación",
        "emergencia", "adaptación", "evolución"
    ]
    
    print(f"Añadiendo {len(conceptos_base)} conceptos semilla...")
    for c in conceptos_base:
        sistema.añadir_concepto(c)
        
    # Crear algunas relaciones iniciales
    print("Estableciendo relaciones iniciales...")
    # Relacionar conceptos con afinidad semántica
    pares = [
        ("pensamiento", "lenguaje"), ("pensamiento", "conocimiento"),
        ("lenguaje", "conocimiento"), ("percepción", "memoria"),
        ("memoria", "aprendizaje"), ("aprendizaje", "adaptación"),
        ("adaptación", "evolución"), ("patrón", "relación"),
        ("abstracción", "patrón"), ("emergencia", "evolución"),
        ("conocimiento", "memoria")
    ]
    
    for c1, c2 in pares:
        sistema.relacionar(c1, c2)
        
    print(f"Sistema creado con {len(sistema.conceptos)} conceptos y {sistema.grafo.number_of_edges()} relaciones")
    
    # Visualización inicial
    if input("¿Visualizar sistema inicial? (s/n): ").lower().startswith('s'):
        sistema.visualizar()
        
    return sistema

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPrograma interrumpido por el usuario")
        sys.exit(0)
