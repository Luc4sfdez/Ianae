# Crear un archivo ejemplo_optimizador.py
from nucleo import ConceptosDifusos
from emergente import PensamientoEmergente
from optimizador import IANAEOptimizado

# Opción 1: Iniciar con un sistema nuevo
optimizador = IANAEOptimizado(dim_vector=15)

# Opción 2: Cargar un sistema existente
# sistema = ConceptosDifusos.cargar('ianae_estado.json')
# optimizador = IANAEOptimizado(sistema=sistema)

# Añadir algunos conceptos iniciales al sistema
conceptos_base = [
    "pensamiento", "lenguaje", "conocimiento", 
    "emergencia", "adaptación", "evolución"
]

for c in conceptos_base:
    optimizador.sistema.añadir_concepto(c)

# Crear algunas relaciones
relaciones = [
    ("pensamiento", "lenguaje"), 
    ("lenguaje", "conocimiento"),
    ("emergencia", "adaptación"),
    ("adaptación", "evolución")
]

for c1, c2 in relaciones:
    optimizador.sistema.relacionar(c1, c2)

# Ejecutar ciclo vital optimizado (con pocos ciclos para probar)
optimizador.ciclo_vital_optimizado(
    num_ciclos_total=50,    # Total de ciclos a ejecutar
    ciclos_por_batch=10,    # Ciclos por lote antes de monitorear
    optimizar_cada=20,      # Optimizar cada 20 ciclos
    visualizar_cada=10      # Visualizar cada 10 ciclos
)

# Analizar los resultados
optimizador.visualizar_metricas_rendimiento()
optimizador.buscar_patrones_emergentes()
optimizador.generar_informe_sistema()