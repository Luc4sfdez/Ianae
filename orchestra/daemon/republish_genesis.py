"""Reenviar ordenes de genesis #80 y #81 con max_tokens=30000."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docs_client import DocsClient

client = DocsClient("http://localhost:25500")
if not client.health_check():
    print("[ERROR] docs-service no responde"); sys.exit(1)

orders = [
    {
        "title": "ORDEN-CORE-02b: Implementar genesis de conceptos dinamicos en nucleo.py",
        "content": """# Orden para worker-core (reenvio con mas tokens)

## Objetivo
Agregar a la clase ConceptosLucas en `src/core/nucleo.py` la capacidad de CREAR conceptos nuevos autonomamente durante el pensamiento.

Actualmente todos los conceptos se hardcodean manualmente. IANAE necesita crear conceptos emergentes cuando detecta patrones de co-activacion.

## Que agregar

Agregar SOLO estos 3 metodos nuevos al final de la clase ConceptosLucas en nucleo.py. NO reescribas el archivo completo, solo agrega los metodos.

### Metodo 1: genesis_concepto
```python
def genesis_concepto(self, padres, nombre_emergente=None):
    # Crea concepto nuevo fusionando vectores de conceptos padres
    # Vector = promedio ponderado de vectores padres + ruido gaussiano
    # Nombre auto: "EMG_{padre1}_{padre2}_{timestamp}" si no se da
    # Categoria siempre 'emergentes'
    # Crear conexiones con cada padre (fuerza=0.7)
    # Guardar linaje: concepto['genesis'] = {'padres': padres, 'ts': timestamp}
    # Retorna nombre del concepto creado
```

### Metodo 2: detectar_candidatos_genesis
```python
def detectar_candidatos_genesis(self, umbral_coactivacion=0.5):
    # Analiza self.historial_activaciones (ultimas 5 activaciones)
    # Busca pares de conceptos de DIFERENTE categoria
    # que se co-activan frecuentemente por encima del umbral
    # Retorna lista de (concepto1, concepto2, frecuencia)
```

### Metodo 3: ciclo_genesis
```python
def ciclo_genesis(self, max_nuevos=3):
    # 1. detectar_candidatos_genesis()
    # 2. Para cada candidato (hasta max_nuevos), genesis_concepto()
    # 3. Incrementar metricas
    # 4. Retornar lista de nombres de conceptos nuevos creados
```

## Archivo de tests
Crear `tests/core/test_genesis.py` con:
- test_genesis_concepto_crea_con_vector_fusionado: crear 2 conceptos, hacer genesis, verificar que el vector resultante es promedio + ruido
- test_genesis_nombre_autogenerado: verificar formato EMG_padre1_padre2_...
- test_genesis_conexiones_con_padres: verificar que se crearon relaciones bidireccionales
- test_detectar_candidatos_cross_categoria: crear conceptos de diferentes categorias, activarlos juntos, detectar candidatos
- test_ciclo_genesis_limita_max_nuevos: verificar que no crea mas de max_nuevos

## IMPORTANTE
- Usa `self.anadir_concepto()` y `self.relacionar()` que ya existen
- El vector fusionado se calcula: promedio de vectores 'actual' de los padres + ruido gaussiano (self.incertidumbre_base * 0.5)
- Los conceptos padres DEBEN existir en self.conceptos, si no -> ValueError
""",
        "tags": ["worker-core", "genesis", "conceptos-dinamicos", "orden"],
    },
    {
        "title": "ORDEN-CORE-03b: Implementar ciclo recursivo pensar-evaluar-refinar en emergente.py",
        "content": """# Orden para worker-core (reenvio con mas tokens)

## Objetivo
Agregar a la clase PensamientoLucas en `src/core/emergente.py` un metodo de pensamiento recursivo real: pensar -> evaluar -> refinar -> pensar (hasta convergencia).

## Que agregar

Agregar estos 3 metodos a la clase PensamientoLucas en emergente.py:

### Metodo 1: pensar_recursivo
```python
def pensar_recursivo(self, semilla, max_ciclos=5, umbral_convergencia=0.05):
    \"\"\"
    Ciclo recursivo de pensamiento.

    Algoritmo:
    1. activar(semilla) -> mapa de activaciones
    2. evaluar coherencia del resultado
    3. si coherencia < 0.6: refinar (ajustar temperatura, reactivar)
    4. si cambio entre ciclos < umbral_convergencia: convergencia alcanzada
    5. repetir hasta convergencia o max_ciclos

    Returns: {
        'ciclos': int,
        'convergencia': bool,
        'activaciones_finales': dict,
        'coherencia_final': float,
        'traza': list,  # [(ciclo, coherencia, top_3_conceptos), ...]
    }
    \"\"\"
    traza = []
    activaciones_previas = {}
    temperatura = 0.5

    for ciclo in range(max_ciclos):
        # Activar
        resultados = self.sistema.activar(semilla, pasos=3, temperatura=temperatura)

        # Obtener activaciones del ultimo paso
        activaciones = resultados[-1] if resultados else {}

        # Evaluar coherencia
        coherencia = self._evaluar_coherencia_activacion(activaciones)

        # Top 3 para traza
        top3 = sorted(activaciones.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_str = [f"{c}:{v:.2f}" for c, v in top3]
        traza.append((ciclo + 1, round(coherencia, 3), top3_str))

        # Verificar convergencia
        if activaciones_previas:
            conceptos_comunes = set(activaciones.keys()) & set(activaciones_previas.keys())
            if conceptos_comunes:
                delta = sum(abs(activaciones.get(c, 0) - activaciones_previas.get(c, 0))
                           for c in conceptos_comunes) / len(conceptos_comunes)
                if delta < umbral_convergencia:
                    return {
                        'ciclos': ciclo + 1,
                        'convergencia': True,
                        'activaciones_finales': activaciones,
                        'coherencia_final': coherencia,
                        'traza': traza,
                    }

        # Refinar si coherencia baja
        temperatura = self._refinar_activacion(activaciones, coherencia, temperatura)
        activaciones_previas = activaciones

    return {
        'ciclos': max_ciclos,
        'convergencia': False,
        'activaciones_finales': activaciones_previas,
        'coherencia_final': coherencia,
        'traza': traza,
    }
```

### Metodo 2: _evaluar_coherencia_activacion
```python
def _evaluar_coherencia_activacion(self, activaciones):
    \"\"\"
    Evalua coherencia de un conjunto de activaciones.
    - Distancia promedio entre vectores activos (mas cercanos = mas coherente)
    - Penaliza si >70% es de la misma categoria (echo chamber)
    - Premia diversidad controlada (2-3 categorias distintas)
    \"\"\"
    if len(activaciones) < 2:
        return 1.0

    # Obtener vectores y categorias
    conceptos_activos = [c for c in activaciones if c in self.sistema.conceptos]
    if len(conceptos_activos) < 2:
        return 1.0

    vectores = [self.sistema.conceptos[c]['actual'] for c in conceptos_activos]
    categorias = [self.sistema.conceptos[c].get('categoria', 'emergentes') for c in conceptos_activos]

    # Similitud promedio entre pares
    import numpy as np
    sims = []
    for i in range(len(vectores)):
        for j in range(i+1, len(vectores)):
            cos_sim = np.dot(vectores[i], vectores[j]) / (
                np.linalg.norm(vectores[i]) * np.linalg.norm(vectores[j]) + 1e-10)
            sims.append(cos_sim)
    similitud_base = np.mean(sims) if sims else 0.5

    # Penalizacion echo chamber
    from collections import Counter
    cat_counts = Counter(categorias)
    max_ratio = max(cat_counts.values()) / len(categorias)
    echo_penalty = -0.2 if max_ratio > 0.7 else 0.0

    # Bonus diversidad
    n_cats = len(cat_counts)
    diversity_bonus = 0.15 if 2 <= n_cats <= 3 else 0.0

    coherencia = similitud_base + echo_penalty + diversity_bonus
    return max(0.0, min(1.0, coherencia))
```

### Metodo 3: _refinar_activacion
```python
def _refinar_activacion(self, activaciones, coherencia, temperatura_actual):
    \"\"\"
    Ajusta temperatura segun coherencia.
    - Coherencia baja (<0.4): subir temperatura (explorar mas)
    - Coherencia alta (>0.7) pero pocos nodos (<3): bajar temperatura (profundizar)
    - Coherencia media: mantener
    \"\"\"
    if coherencia < 0.4:
        return min(temperatura_actual + 0.15, 1.0)
    elif coherencia > 0.7 and len(activaciones) < 3:
        return max(temperatura_actual - 0.1, 0.1)
    return temperatura_actual
```

## Tests
Crear `tests/core/test_pensamiento_recursivo.py`:
- test_pensar_recursivo_retorna_estructura: verificar que retorna dict con las claves correctas
- test_pensar_recursivo_traza_formato: verificar que traza tiene formato [(ciclo, coherencia, top3), ...]
- test_coherencia_penaliza_echo_chamber: crear conceptos de misma categoria, verificar coherencia baja
- test_refinamiento_ajusta_temperatura: verificar que coherencia baja sube temperatura

## IMPORTANTE
- self.sistema es la instancia de ConceptosLucas (ya existe en PensamientoLucas.__init__)
- Usa self.sistema.activar() que ya existe
- Usa self.sistema.conceptos para acceder a vectores y categorias
- NO reescribas emergente.py completo, solo agrega los 3 metodos a la clase
""",
        "tags": ["worker-core", "genesis", "pensamiento-recursivo", "orden"],
    },
]

print(f"[GENESIS] Reenviando {len(orders)} ordenes con max_tokens=30000...\n")
for i, order in enumerate(orders, 1):
    result = client.publish_order(title=order["title"], content=order["content"], tags=order["tags"], priority="alta")
    if result:
        print(f"  [{i}/{len(orders)}] Orden #{result.get('id','?')}: {order['title'][:65]}")
    else:
        print(f"  [{i}/{len(orders)}] ERROR: {order['title'][:65]}")
print(f"\n[GENESIS] Ordenes reenviadas. Arranca el executor.")
