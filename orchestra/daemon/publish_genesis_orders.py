"""
Publicar ordenes de genesis para darle vida a IANAE.
Estas ordenes seran detectadas por el worker_executor y ejecutadas autonomamente.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docs_client import DocsClient

client = DocsClient("http://localhost:25500")

# Verificar docs-service
health = client.health_check()
if not health:
    print("[ERROR] docs-service no responde")
    sys.exit(1)

orders = [
    {
        "title": "ORDEN-CORE-01: Implementar ThoughtNode — unidad atomica de pensamiento simbolico",
        "content": """# Orden para worker-core

## Objetivo
Crear `src/core/pensamiento_simbolico.py` con la clase `ThoughtNode` — la unidad atomica del lenguaje interno de IANAE.

IANAE necesita dejar de "pensar en español" y operar con un protocolo simbolico recursivo. Un ThoughtNode representa un estado mental, no una palabra.

## Especificacion

```python
@dataclass
class ThoughtNode:
    concept_id: str           # Nombre del concepto origen
    activation: float         # Nivel de activacion (0-1)
    vector: np.ndarray        # Vector de 15 dimensiones
    coherence: float          # Auto-evaluacion de coherencia (0-1)
    origin: str               # 'propagation' | 'emergence' | 'refinement'
    children: list            # ThoughtNodes derivados
    depth: int                # Profundidad en el arbol
    timestamp: float          # time.time() de creacion

class ThoughtTree:
    def __init__(self, root_concept: str, nucleo):
        # Construye arbol desde una activacion del nucleo
        pass

    def evaluate_coherence(self) -> float:
        # Calcula coherencia del arbol completo
        # Penaliza nodos contradictorios (vectores opuestos)
        # Premia conexiones cross-categoria
        pass

    def prune(self, min_coherence=0.3):
        # Elimina ramas incoherentes
        pass

    def merge(self, other: 'ThoughtTree') -> 'ThoughtTree':
        # Fusiona dos arboles de pensamiento
        # Los nodos compartidos se refuerzan
        pass

    def to_symbolic(self) -> str:
        # Representacion simbolica: no prosa, notacion logica
        # Ejemplo: "Python(0.9) -> [OpenCV(0.7), Pandas(0.6)] ~> Emergent(vision+data, 0.4)"
        pass

    def depth_stats(self) -> dict:
        # Estadisticas por profundidad del arbol
        pass
```

## Integracion con nucleo.py
- `ThoughtTree.__init__` debe llamar a `nucleo.activar(concepto, pasos=3, temperatura=0.5)`
- Cada paso de activacion genera un nivel de profundidad en el arbol
- Los nodos se crean desde los resultados de propagacion (conceptos con activacion > 0.1)

## Coherencia
La coherencia de un nodo se calcula como:
- `cosine_similarity(vector_nodo, vector_padre)` si tiene padre
- Bonus +0.2 si el nodo es de categoria diferente al padre (emergencia cross-category)
- Penalizacion -0.3 si activacion < 0.15 (ruido)

## Tests requeridos
Crear `tests/core/test_pensamiento_simbolico.py`:
- test_thought_node_creation
- test_thought_tree_from_activation
- test_coherence_evaluation
- test_prune_removes_weak_nodes
- test_to_symbolic_format (sin prosa humana)
- test_merge_two_trees

## Reglas
- NO usar strings largos en español para representar pensamiento
- El formato simbolico debe ser parseable (no decorativo)
- Importar ConceptosLucas desde nucleo.py (o nucleo_lucas)
""",
        "tags": ["worker-core", "genesis", "pensamiento-simbolico", "orden"],
    },
    {
        "title": "ORDEN-CORE-02: Implementar genesis de conceptos dinamicos en nucleo.py",
        "content": """# Orden para worker-core

## Objetivo
Agregar a la clase ConceptosLucas en `src/core/nucleo.py` la capacidad de CREAR conceptos nuevos autonomamente durante el pensamiento.

Actualmente todos los conceptos se hardcodean. IANAE necesita crear conceptos emergentes cuando detecta patrones.

## Especificacion

Agregar estos metodos a ConceptosLucas:

```python
def genesis_concepto(self, padres: list, nombre_emergente: str = None) -> str:
    \"\"\"
    Crea un concepto nuevo a partir de la fusion de conceptos padres.

    - Vector = promedio ponderado de vectores padres + ruido
    - Nombre auto-generado si no se da: "EMG_{padre1}_{padre2}_{timestamp}"
    - Categoria siempre 'emergentes'
    - Conexiones automaticas con los padres (fuerza = 0.7)
    - Registra linaje en concepto['genesis'] = {'padres': [...], 'timestamp': ...}

    Returns: nombre del concepto creado
    \"\"\"

def detectar_candidatos_genesis(self, umbral_coactivacion=0.5) -> list:
    \"\"\"
    Analiza historial_activaciones reciente.
    Busca pares de conceptos de DIFERENTE categoria que se co-activan
    frecuentemente por encima del umbral.

    Returns: lista de (concepto1, concepto2, frecuencia_coactivacion)
    \"\"\"

def ciclo_genesis(self, max_nuevos=3):
    \"\"\"
    Ejecuta un ciclo completo de genesis:
    1. detectar_candidatos_genesis()
    2. Para cada candidato, genesis_concepto()
    3. Registrar en metricas['conceptos_emergentes_creados']
    4. Retornar lista de conceptos nuevos creados
    \"\"\"
```

## Ejemplo de uso
```python
nucleo = ConceptosLucas()
# ... despues de varias activaciones ...
nuevos = nucleo.ciclo_genesis()
# nuevos = ['EMG_Python_OpenCV_1707...', 'EMG_Docker_Automatizacion_1707...']
```

## Tests requeridos
Agregar a `tests/core/test_nucleo_extras.py` o crear `tests/core/test_genesis.py`:
- test_genesis_concepto_crea_con_vector_fusionado
- test_genesis_nombre_autogenerado
- test_genesis_conexiones_con_padres
- test_detectar_candidatos_cross_categoria
- test_ciclo_genesis_limita_max_nuevos

## Reglas
- genesis_concepto debe llamar a self.anadir_concepto() y self.relacionar()
- El vector fusionado NO es promedio simple: ponderar por activacion de cada padre
- Agregar ruido gaussiano al vector (self.incertidumbre_base * 0.5)
""",
        "tags": ["worker-core", "genesis", "conceptos-dinamicos", "orden"],
    },
    {
        "title": "ORDEN-CORE-03: Implementar ciclo recursivo pensar-evaluar-refinar",
        "content": """# Orden para worker-core

## Objetivo
Agregar a `src/core/emergente.py` un metodo de pensamiento recursivo real.
El pensamiento actual es un solo paso de propagacion. Necesitamos ciclos:
pensar -> evaluar -> refinar -> pensar (hasta convergencia o max iteraciones).

## Especificacion

Agregar a la clase PensamientoLucas (o crear PensamientoRecursivo):

```python
def pensar_recursivo(self, semilla: str, max_ciclos: int = 5, umbral_convergencia: float = 0.05) -> dict:
    \"\"\"
    Ciclo recursivo de pensamiento.

    Algoritmo:
    1. activar(semilla) -> obtener mapa de activaciones
    2. evaluar_coherencia() -> score de 0 a 1
    3. si coherencia < 0.6: refinar (ajustar temperatura, reactivar)
    4. si cambio entre ciclos < umbral_convergencia: convergencia alcanzada
    5. repetir hasta convergencia o max_ciclos

    Returns: {
        'ciclos': int,
        'convergencia': bool,
        'activaciones_finales': dict,
        'coherencia_final': float,
        'conceptos_emergentes': list,  # nuevos conceptos creados durante el ciclo
        'traza': list,  # [(ciclo, coherencia, top_conceptos), ...]
    }
    \"\"\"

def _evaluar_coherencia_activacion(self, activaciones: dict) -> float:
    \"\"\"
    Evalua la coherencia de un conjunto de activaciones.
    - Calcula distancia promedio entre vectores activos
    - Penaliza si hay >70% de la misma categoria (echo chamber)
    - Premia diversidad controlada (2-3 categorias)
    \"\"\"

def _refinar_activacion(self, activaciones: dict, coherencia: float) -> dict:
    \"\"\"
    Refina una activacion incoherente.
    - Si coherencia baja: subir temperatura (explorar mas)
    - Si coherencia alta pero pocos nodos: bajar temperatura (profundizar)
    - Reactivar desde el concepto mas coherente
    \"\"\"
```

## Convergencia
Calcular delta entre ciclos:
`delta = sum(abs(act_actual[c] - act_anterior[c]) for c en conceptos) / len(conceptos)`
Si delta < umbral_convergencia -> convergencia alcanzada.

## Integracion con genesis
En cada ciclo, si coherencia > 0.7 Y hay co-activacion cross-categoria:
llamar a `nucleo.genesis_concepto()` para crear concepto emergente.

## Tests requeridos
En `tests/core/test_emergente.py`:
- test_pensar_recursivo_converge
- test_pensar_recursivo_max_ciclos
- test_coherencia_penaliza_echo_chamber
- test_refinamiento_sube_temperatura
- test_genesis_durante_pensamiento

## Reglas
- La traza debe ser compacta: solo numeros, no prosa
- Formato traza: [(1, 0.45, ['Python:0.9', 'OpenCV:0.7']), (2, 0.62, ...), ...]
""",
        "tags": ["worker-core", "genesis", "pensamiento-recursivo", "orden"],
    },
]

print(f"[GENESIS] Publicando {len(orders)} ordenes de vida para IANAE...\n")

for i, order in enumerate(orders, 1):
    result = client.publish_order(
        title=order["title"],
        content=order["content"],
        tags=order["tags"],
        priority="alta",
    )
    if result:
        doc_id = result.get("id", "?")
        print(f"  [{i}/{len(orders)}] Orden #{doc_id}: {order['title'][:60]}")
    else:
        print(f"  [{i}/{len(orders)}] ERROR publicando: {order['title'][:60]}")

print(f"\n[GENESIS] Ordenes publicadas. El worker executor las detectara automaticamente.")
print(f"[GENESIS] IANAE esta a punto de empezar a pensar por si misma.")
