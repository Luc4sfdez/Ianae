# test_ianae_lucas.py - Suite de pruebas integrada para IANAE Lucas
import time
import os
import sys

# Asegurarse de que podamos importar nuestros módulos
sys.path.append('.')

from nucleo_lucas import ConceptosLucas, crear_universo_lucas
from emergente_lucas import PensamientoLucas

def test_completo_ianae_lucas():
    """
    Suite de pruebas completa para validar IANAE adaptado para Lucas
    """
    print("🚀 INICIANDO SUITE DE PRUEBAS IANAE-LUCAS")
    print("=" * 60)
    
    # === FASE 1: CREACIÓN DEL UNIVERSO CONCEPTUAL ===
    print("\n📍 FASE 1: CREACIÓN DEL UNIVERSO CONCEPTUAL")
    print("-" * 40)
    
    inicio = time.time()
    sistema = crear_universo_lucas()
    tiempo_creacion = time.time() - inicio
    
    print(f"✅ Universo creado en {tiempo_creacion:.2f} segundos")
    
    # Validar creación
    assert len(sistema.conceptos) > 20, "Debería haber al menos 20 conceptos"
    assert sistema.grafo.number_of_edges() > 15, "Debería haber al menos 15 relaciones"
    
    print(f"   📊 {len(sistema.conceptos)} conceptos creados")
    print(f"   🔗 {sistema.grafo.number_of_edges()} relaciones establecidas")
    
    # Verificar categorías
    categorias_esperadas = ['tecnologias', 'proyectos', 'lucas_personal', 'conceptos_ianae', 'herramientas']
    for categoria in categorias_esperadas:
        conceptos_categoria = len(sistema.categorias.get(categoria, []))
        print(f"   📁 {categoria}: {conceptos_categoria} conceptos")
        assert conceptos_categoria > 0, f"Categoría {categoria} debería tener conceptos"
    
    # === FASE 2: PRUEBAS BÁSICAS DEL NÚCLEO ===
    print("\n📍 FASE 2: PRUEBAS BÁSICAS DEL NÚCLEO")
    print("-" * 40)
    
    # Test 1: Activación simple
    print("🧪 Test 1: Activación de concepto...")
    resultado_activacion = sistema.activar('Python', pasos=3, temperatura=0.2)
    assert len(resultado_activacion) == 4, "Debería haber 4 pasos de activación (inicial + 3)"
    
    conceptos_activos = [c for c, a in resultado_activacion[-1].items() if a > 0.1]
    print(f"   ✅ {len(conceptos_activos)} conceptos activados desde Python")
    
    # Verificar que se activaron conceptos relacionados esperados
    activaciones_finales = resultado_activacion[-1]
    conceptos_esperados = ['Automatizacion', 'OpenCV', 'VBA2Python']
    encontrados = [c for c in conceptos_esperados if c in activaciones_finales and activaciones_finales[c] > 0.05]
    print(f"   🎯 Conceptos relacionados encontrados: {', '.join(encontrados)}")
    
    # Test 2: Auto-modificación
    print("\n🧪 Test 2: Auto-modificación...")
    modificaciones = sistema.auto_modificar(fuerza=0.2)
    print(f"   ✅ {modificaciones} modificaciones realizadas")
    
    # Test 3: Exploración específica de proyecto
    print("\n🧪 Test 3: Exploración de proyecto...")
    reporte_tacografos = sistema.explorar_proyecto('Tacografos', profundidad=3)
    print("   ✅ Exploración de Tacógrafos completada")
    print("   📋 Primeras líneas del reporte:")
    primeras_lineas = reporte_tacografos.split('\n')[:5]
    for linea in primeras_lineas:
        print(f"      {linea}")
    
    # Test 4: Detección de emergencias
    print("\n🧪 Test 4: Detección de emergencias...")
    # Necesitamos más historia para detectar emergencias, así que activamos varios conceptos
    conceptos_para_activar = ['Python', 'OpenCV', 'Automatizacion', 'Lucas', 'IANAE']
    for concepto in conceptos_para_activar:
        if concepto in sistema.conceptos:
            sistema.activar(concepto, pasos=2, temperatura=0.15)
    
    emergencias = sistema.detectar_emergencias()
    print("   ✅ Detección de emergencias completada")
    if "EMERGENCIAS DETECTADAS" in emergencias:
        print("   🌟 ¡Emergencias encontradas!")
    else:
        print("   📊 No se detectaron emergencias (normal con pocos datos)")
    
    # === FASE 3: PRUEBAS DE PENSAMIENTO EMERGENTE ===
    print("\n📍 FASE 3: PRUEBAS DE PENSAMIENTO EMERGENTE")
    print("-" * 40)
    
    # Crear sistema de pensamiento emergente
    pensamiento = PensamientoLucas(sistema)
    
    # Test 5: Exploración desde proyecto
    print("🧪 Test 5: Exploración emergente desde proyecto...")
    resultado_exploracion = pensamiento.explorar_desde_proyecto('VBA2Python', profundidad=4)
    print("   ✅ Exploración emergente completada")
    
    # Verificar que el resultado contiene secciones esperadas
    secciones_esperadas = ['EXPLORACIÓN EMERGENTE', 'CADENA DE PENSAMIENTO', 'CONEXIONES INESPERADAS', 'OPTIMIZACIONES']
    secciones_encontradas = [s for s in secciones_esperadas if s in resultado_exploracion]
    print(f"   📋 Secciones encontradas: {len(secciones_encontradas)}/{len(secciones_esperadas)}")
    
    # Test 6: Pensamiento contextual
    print("\n🧪 Test 6: Generación de pensamiento contextual...")
    contextos_test = ['desarrollo', 'vision_artificial', 'ia_local']
    
    for contexto in contextos_test:
        pensamiento_contextual = pensamiento.generar_pensamiento_contextual(contexto, longitud=5)
        print(f"   ✅ Contexto '{contexto}': {len(pensamiento_contextual)} caracteres generados")
        assert len(pensamiento_contextual) > 50, f"Pensamiento de contexto {contexto} muy corto"
    
    # Test 7: Convergencia de proyectos
    print("\n🧪 Test 7: Experimento de convergencia...")
    proyectos_test = ['Tacografos', 'VBA2Python', 'Hollow_Earth']
    convergencia = pensamiento.experimento_convergencia_proyectos(proyectos_test)
    print("   ✅ Experimento de convergencia completado")
    
    # Verificar que se encontraron puntos de convergencia
    if "PUNTOS DE CONVERGENCIA" in convergencia:
        print("   🎯 Puntos de convergencia detectados")
    else:
        print("   📊 No se detectaron convergencias fuertes")
    
    # Test 8: Detección de automatización
    print("\n🧪 Test 8: Detección de automatización...")
    oportunidades = pensamiento.detectar_oportunidades_automatizacion()
    print("   ✅ Análisis de automatización completado")
    
    if "OPORTUNIDADES DE AUTOMATIZACIÓN" in oportunidades:
        print("   🤖 Oportunidades de automatización encontradas")
    else:
        print("   ✅ Proyectos bien automatizados")
    
    # Test 9: Análisis de patrones personales
    print("\n🧪 Test 9: Análisis de patrones personales...")
    patrones = pensamiento.analizar_patrones_personales()
    print("   ✅ Análisis de patrones completado")
    
    # Verificar que se analizaron diferentes tipos de patrones
    tipos_patrones = ['FORTALEZAS TÉCNICAS', 'SUPERPODERES COGNITIVOS', 'PROYECTOS CON MAYOR AFINIDAD']
    patrones_encontrados = [p for p in tipos_patrones if p in patrones]
    print(f"   🧠 Tipos de patrones analizados: {len(patrones_encontrados)}/{len(tipos_patrones)}")
    
    # === FASE 4: PRUEBAS DE PERSISTENCIA ===
    print("\n📍 FASE 4: PRUEBAS DE PERSISTENCIA")
    print("-" * 40)
    
    # Test 10: Guardar estado
    print("🧪 Test 10: Guardado de estado...")
    archivo_test = 'test_ianae_lucas_estado.json'
    
    # Limpiar archivo anterior si existe
    if os.path.exists(archivo_test):
        os.remove(archivo_test)
    
    guardado_exitoso = sistema.guardar(archivo_test)
    assert guardado_exitoso, "El guardado debería ser exitoso"
    assert os.path.exists(archivo_test), "El archivo debería existir después del guardado"
    
    tamaño_archivo = os.path.getsize(archivo_test)
    print(f"   ✅ Estado guardado: {tamaño_archivo} bytes")
    
    # Test 11: Cargar estado
    print("\n🧪 Test 11: Carga de estado...")
    sistema_cargado = ConceptosLucas.cargar(archivo_test)
    assert sistema_cargado is not None, "El sistema debería cargarse correctamente"
    
    # Verificar que se cargó correctamente
    assert len(sistema_cargado.conceptos) == len(sistema.conceptos), "Mismo número de conceptos"
    assert sistema_cargado.grafo.number_of_edges() == sistema.grafo.number_of_edges(), "Mismo número de aristas"
    
    print(f"   ✅ Sistema cargado: {len(sistema_cargado.conceptos)} conceptos, {sistema_cargado.grafo.number_of_edges()} relaciones")
    
    # Limpiar archivo de prueba
    os.remove(archivo_test)
    
    # === FASE 5: PRUEBAS DE RENDIMIENTO ===
    print("\n📍 FASE 5: PRUEBAS DE RENDIMIENTO")
    print("-" * 40)
    
    # Test 12: Rendimiento de activación masiva
    print("🧪 Test 12: Rendimiento de activación masiva...")
    conceptos_a_probar = list(sistema.conceptos.keys())[:10]  # Primeros 10 conceptos
    
    inicio_masivo = time.time()
    for concepto in conceptos_a_probar:
        sistema.activar(concepto, pasos=2, temperatura=0.1)
    tiempo_masivo = time.time() - inicio_masivo
    
    velocidad = len(conceptos_a_probar) / tiempo_masivo
    print(f"   ⚡ {len(conceptos_a_probar)} activaciones en {tiempo_masivo:.2f}s")
    print(f"   📈 Velocidad: {velocidad:.1f} activaciones/segundo")
    
    # Test 13: Ciclo vital
    print("\n🧪 Test 13: Ciclo vital del sistema...")
    inicio_ciclo = time.time()
    resultados_ciclo = sistema.ciclo_vital(num_ciclos=5, auto_mod=True, visualizar_cada=0)
    tiempo_ciclo = time.time() - inicio_ciclo
    
    print(f"   🔄 5 ciclos vitales en {tiempo_ciclo:.2f}s")
    print(f"   📊 {len(resultados_ciclo)} resultados de ciclo")
    
    # Verificar que el sistema evolucionó
    assert len(resultados_ciclo) == 5, "Debería haber 5 resultados de ciclo"
    
    # === FASE 6: INFORME FINAL ===
    print("\n📍 FASE 6: INFORME FINAL")
    print("-" * 40)
    
    # Generar informe completo del sistema
    sistema.informe_lucas()
    
    # Estadísticas finales
    tiempo_total = time.time() - inicio
    print(f"\n🏁 PRUEBAS COMPLETADAS EN {tiempo_total:.2f} SEGUNDOS")
    print("=" * 60)
    
    # Resumen de métricas finales
    print("📊 MÉTRICAS FINALES:")
    print(f"   • Conceptos: {len(sistema.conceptos)}")
    print(f"   • Relaciones: {sistema.grafo.number_of_edges()}")
    print(f"   • Ciclos de pensamiento: {sistema.metricas['ciclos_pensamiento']}")
    print(f"   • Auto-modificaciones: {sistema.metricas['auto_modificaciones']}")
    print(f"   • Emergencias detectadas: {sistema.metricas['emergencias_detectadas']}")
    print(f"   • Pensamientos generados: {len(pensamiento.historial_pensamientos)}")
    
    # Exportar insights de la sesión de prueba
    archivo_insights = 'test_insights_lucas.txt'
    exito_export = pensamiento.exportar_insights_lucas(archivo_insights)
    if exito_export:
        print(f"   📄 Insights exportados a: {archivo_insights}")
    
    print("\n🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    print("🔥 IANAE-LUCAS ESTÁ LISTO PARA PRODUCCIÓN")
    
    return sistema, pensamiento

def demo_interactivo():
    """
    Demo interactivo para que Lucas pueda probar manualmente
    """
    print("🎮 DEMO INTERACTIVO IANAE-LUCAS")
    print("=" * 40)
    
    # Crear sistema
    sistema, pensamiento = test_completo_ianae_lucas()
    
    print("\n🎯 OPCIONES DE DEMO:")
    print("1. Explorar proyecto específico")
    print("2. Generar pensamiento contextual")
    print("3. Detectar oportunidades de automatización")
    print("4. Analizar patrones personales")
    print("5. Experimento de convergencia")
    print("6. Visualizar red conceptual")
    print("7. Salir")
    
    while True:
        try:
            opcion = input("\n🎮 Selecciona opción (1-7): ").strip()
            
            if opcion == '1':
                proyectos = sistema.categorias.get('proyectos', [])
                print(f"📁 Proyectos disponibles: {', '.join(proyectos)}")
                proyecto = input("🚀 Proyecto a explorar: ").strip()
                
                if proyecto in sistema.conceptos:
                    resultado = pensamiento.explorar_desde_proyecto(proyecto)
                    print("\n" + resultado)
                else:
                    print("❌ Proyecto no encontrado")
            
            elif opcion == '2':
                contextos = list(pensamiento.contextos_proyecto.keys())
                print(f"🎨 Contextos disponibles: {', '.join(contextos)}")
                contexto = input("🧠 Contexto para pensamiento: ").strip()
                
                if contexto in contextos:
                    pensamiento_resultado = pensamiento.generar_pensamiento_contextual(contexto)
                    print(f"\n💭 {pensamiento_resultado}")
                else:
                    print("❌ Contexto no encontrado")
            
            elif opcion == '3':
                resultado = pensamiento.detectar_oportunidades_automatizacion()
                print("\n" + resultado)
            
            elif opcion == '4':
                resultado = pensamiento.analizar_patrones_personales()
                print("\n" + resultado)
            
            elif opcion == '5':
                proyectos = sistema.categorias.get('proyectos', [])[:3]
                print(f"🔬 Analizando convergencia entre: {', '.join(proyectos)}")
                resultado = pensamiento.experimento_convergencia_proyectos(proyectos)
                print("\n" + resultado)
            
            elif opcion == '6':
                print("🎨 Generando visualización...")
                sistema.visualizar_lucas()
            
            elif opcion == '7':
                print("👋 ¡Hasta pronto!")
                break
                
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta pronto!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        demo_interactivo()
    else:
        test_completo_ianae_lucas()
