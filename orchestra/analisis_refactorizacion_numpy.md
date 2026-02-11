# Análisis y Plan de Refactorización Numpy - IANAE nucleo.py

**Worker:** worker-core
**Fecha:** 2026-02-10
**Archivos Analizados:**
- `src/core/nucleo.py` (752 líneas)
- `src/core/emergente.py` (882 líneas)

---

## HALLAZGO IMPORTANTE

**El código YA usa numpy extensivamente**. La migración a numpy ya está implementada en gran medida. Sin embargo, se identificaron oportunidades significativas de optimización vectorial y mejoras de rendimiento.

---

## 1. ANÁLISIS DEL CÓDIGO ACTUAL

### 1.1 Uso Actual de Numpy

**Operaciones que YA usan numpy:**
- ✅ Vectores de conceptos: `np.array()` (líneas 110, 213, 216, 219)
- ✅ Normalización vectorial: `np.linalg.norm()` (línea 216)
- ✅ Random normal: `np.random.normal()` (líneas 213, 219, 532)
- ✅ Producto punto: `np.dot()` (línea 254)
- ✅ Random choice: `np.random.choice()` (línea 707)

### 1.2 Estructuras de Datos Identificadas

```python
# Concepto individual (líneas 220-230)
self.conceptos[nombre] = {
    'base': np.array,          # ✅ numpy array
    'actual': np.array,        # ✅ numpy array
    'historial': [np.array],   # ⚠️ lista de numpy arrays
    'creado': int,
    'activaciones': int,
    'ultima_activacion': int,
    'fuerza': float,
    'categoria': str,
    'conexiones_proyecto': int
}

# Relaciones (línea 257)
self.relaciones[concepto1] = [(concepto2, fuerza), ...]  # ⚠️ lista de tuplas

# Activaciones (línea 513)
activacion = {c: 0.0 for c in self.conceptos}  # ⚠️ diccionario, no numpy
```

### 1.3 Cuellos de Botella Identificados

#### **Cuello #1: Propagación de Activación (líneas 518-540)**
```python
for paso in range(pasos):
    nueva_activacion = activacion.copy()  # ⚠️ copia de diccionario

    for concepto, nivel in activacion.items():  # ⚠️ iteración Python pura
        if nivel > 0.1:
            for vecino, fuerza in self.relaciones[concepto]:  # ⚠️ nested loops
                factor_aleatorio = np.random.uniform(1 - temperatura, 1 + temperatura)
                propagacion = nivel * fuerza * factor_aleatorio
                nueva_activacion[vecino] = max(nueva_activacion[vecino], propagacion)
```

**Problema:** Triple loop anidado con operaciones Python puras. Complejidad O(pasos × conceptos × relaciones_promedio).

**Estimación:** Para 1000 conceptos con 10 relaciones cada uno, 3 pasos = ~30,000 operaciones.

#### **Cuello #2: Normalización Manual (líneas 529-533)**
```python
total = sum(nueva_activacion.values()) + 1e-10  # ⚠️ sum() de diccionario
for c in nueva_activacion:
    nueva_activacion[c] = nueva_activacion[c] / total
    nueva_activacion[c] += np.random.normal(0, temperatura * 0.5)
    nueva_activacion[c] = max(0, min(1, nueva_activacion[c]))
```

**Problema:** Operaciones elemento por elemento en Python. No aprovecha vectorización numpy.

#### **Cuello #3: Auto-modificación (líneas 564-584)**
```python
for i in range(len(conceptos_activos)):
    for j in range(i+1, len(conceptos_activos)):  # ⚠️ O(n²) loops
        c1, c2 = conceptos_activos[i], conceptos_activos[j]
        if self.grafo.has_edge(c1, c2):  # ⚠️ lookup individual
            # Actualizar relaciones uno por uno
            for idx, (vecino, peso) in enumerate(self.relaciones[c1]):
                if vecino == c2:
                    self.relaciones[c1][idx] = (vecino, nuevo_peso)
```

**Problema:** Actualización secuencial de relaciones. O(n²) para n conceptos activos.

#### **Cuello #4: Relaciones como Listas de Tuplas**
```python
self.relaciones[concepto1].append((concepto2, fuerza))  # línea 257
```

**Problema:**
- Búsqueda lineal O(n) para encontrar vecino específico
- No hay operaciones vectoriales posibles
- Difícil de paralelizar

### 1.4 Operaciones Críticas por Frecuencia

| Operación | Frecuencia | Vectorizable | Impacto |
|-----------|------------|--------------|---------|
| Propagación activación | Alta (cada `activar()`) | ✅ Sí | 🔴 **CRÍTICO** |
| Normalización | Alta (cada paso) | ✅ Sí | 🔴 **CRÍTICO** |
| Búsqueda vecinos | Alta (cada propagación) | ✅ Sí | 🟡 Alto |
| Auto-modificación | Media (ciclos) | ⚠️ Parcial | 🟡 Alto |
| Guardar/cargar | Baja | ❌ No | 🟢 Bajo |

---

## 2. DISEÑO DE LA MIGRACIÓN

### 2.1 Matriz de Adyacencia para Relaciones

**Propuesta:** Reemplazar `self.relaciones` (dict de listas de tuplas) por matriz de adyacencia numpy.

**Estructura actual:**
```python
self.relaciones = {
    'Python': [('VBA', 0.9), ('OpenCV', 0.85), ...],
    'VBA': [('Python', 0.9), ('Excel', 0.95), ...],
    ...
}
```

**Estructura propuesta:**
```python
self.conceptos_idx = {'Python': 0, 'VBA': 1, 'OpenCV': 2, ...}  # mapeo nombre → índice
self.matriz_relaciones = np.zeros((n_conceptos, n_conceptos), dtype=np.float32)
# matriz_relaciones[i, j] = fuerza de relación entre concepto[i] y concepto[j]
```

**Ventajas:**
- ✅ Lookup O(1) en vez de O(n)
- ✅ Operaciones vectoriales (broadcasting, slicing)
- ✅ Compatible con álgebra lineal
- ✅ Fácil de guardar/cargar (np.save/np.load)

**Trade-off:**
- ⚠️ Memoria: O(n²) en vez de O(e) donde e = número de edges
- Para 1000 conceptos: 1000² × 4 bytes = 4 MB (aceptable)
- Para 10000 conceptos: 10000² × 4 bytes = 400 MB (considerar sparse matrix)

### 2.2 Vector de Activaciones

**Propuesta:** Reemplazar diccionario por numpy array.

**Estructura actual:**
```python
activacion = {c: 0.0 for c in self.conceptos}  # diccionario
```

**Estructura propuesta:**
```python
activacion = np.zeros(n_conceptos, dtype=np.float32)
# activacion[idx] = nivel de activación del concepto[idx]
```

**Ventajas:**
- ✅ Operaciones vectoriales directas
- ✅ Broadcasting automático
- ✅ Más rápido (contiguo en memoria)

### 2.3 Propagación Vectorizada

**Algoritmo actual (líneas 518-540):**
```python
# O(pasos × conceptos × relaciones_promedio)
for paso in range(pasos):
    for concepto, nivel in activacion.items():
        if nivel > 0.1:
            for vecino, fuerza in self.relaciones[concepto]:
                propagacion = nivel * fuerza * factor
                nueva_activacion[vecino] = max(...)
```

**Algoritmo propuesto:**
```python
# O(pasos × conceptos) — operaciones matriciales
for paso in range(pasos):
    # Vectorizar propagación
    activos_mask = activacion > 0.1
    factor_aleatorio = np.random.uniform(
        1 - temperatura, 1 + temperatura,
        size=(n_conceptos, n_conceptos)
    )

    # Propagación vectorizada (¡UNA LÍNEA!)
    nueva_activacion = np.maximum(
        nueva_activacion,
        (activacion[:, np.newaxis] * self.matriz_relaciones * factor_aleatorio).max(axis=0)
    )

    # Normalización vectorizada
    nueva_activacion /= (nueva_activacion.sum() + 1e-10)
    nueva_activacion += np.random.normal(0, temperatura * 0.5, n_conceptos)
    nueva_activacion = np.clip(nueva_activacion, 0, 1)
```

**Mejora estimada:** 10-50x más rápido (depende de n_conceptos).

### 2.4 Historial Optimizado

**Propuesta:** Usar numpy array 2D para historial de vectores.

**Estructura actual:**
```python
self.conceptos[nombre]['historial'] = [np.array1, np.array2, ...]  # lista
```

**Estructura propuesta:**
```python
self.conceptos[nombre]['historial'] = np.vstack([np.array1, np.array2, ...])
# Shape: (n_historiales, dim_vector)
```

**Ventajas:**
- ✅ Análisis temporal vectorizado
- ✅ Cálculo de tendencias con np.mean(), np.std()
- ✅ Detección de drift con operaciones matriciales

---

## 3. PLAN DE IMPLEMENTACIÓN

### Fase 1: Infraestructura Base (PRIORIDAD ALTA)
**Objetivo:** Preparar estructuras sin romper funcionalidad existente.

**Tareas:**
1. Crear mapeo bidireccional concepto ↔ índice
   ```python
   self.conceptos_idx = {}  # nombre → índice
   self.idx_conceptos = []  # índice → nombre
   ```

2. Inicializar matriz de relaciones
   ```python
   self.matriz_relaciones = np.zeros((max_conceptos, max_conceptos), dtype=np.float32)
   ```

3. Migrar relaciones existentes a matriz
   ```python
   def _migrar_relaciones_a_matriz(self):
       for c1, vecinos in self.relaciones.items():
           idx1 = self.conceptos_idx[c1]
           for c2, fuerza in vecinos:
               idx2 = self.conceptos_idx[c2]
               self.matriz_relaciones[idx1, idx2] = fuerza
   ```

4. Mantener compatibilidad con API existente (wrapper methods)

**Criterio de hecho:**
- ✅ Tests existentes pasan sin cambios
- ✅ Matriz de relaciones refleja self.relaciones
- ✅ Rendimiento igual o mejor

**Tests necesarios:**
```python
def test_matriz_relaciones_equivalente():
    # Verificar que matriz y diccionario son equivalentes
    assert all(sistema.matriz_relaciones[i, j] == fuerza
               for c1, vecinos in sistema.relaciones.items()
               for c2, fuerza in vecinos)
```

### Fase 2: Refactorizar activar() (PRIORIDAD ALTA)
**Objetivo:** 2-10x mejora en propagación.

**Tareas:**
1. Convertir activación a vector numpy
   ```python
   activacion = np.zeros(len(self.conceptos), dtype=np.float32)
   activacion[self.conceptos_idx[concepto_inicial]] = 1.0
   ```

2. Implementar propagación vectorizada (ver 2.3)

3. Agregar parámetro legacy_mode para comparación
   ```python
   def activar(self, concepto, pasos=3, temperatura=0.1, vectorizado=True):
       if vectorizado:
           return self._activar_vectorizado(...)
       else:
           return self._activar_legacy(...)  # mantener original
   ```

4. Benchmark comparativo

**Criterio de hecho:**
- ✅ Resultados equivalentes (±0.01 por ruido estocástico)
- ✅ Mejora de rendimiento >2x
- ✅ Tests pasan con vectorizado=True

**Tests necesarios:**
```python
def test_activar_vectorizado_equivalente():
    resultado_legacy = sistema.activar('Python', vectorizado=False)
    resultado_nuevo = sistema.activar('Python', vectorizado=True)
    assert np.allclose(resultado_legacy, resultado_nuevo, atol=0.05)

def test_activar_vectorizado_mas_rapido():
    import time
    t0 = time.time()
    sistema.activar('Python', pasos=10, vectorizado=False)
    t_legacy = time.time() - t0

    t0 = time.time()
    sistema.activar('Python', pasos=10, vectorizado=True)
    t_nuevo = time.time() - t0

    assert t_nuevo < t_legacy * 0.5  # Al menos 2x más rápido
```

### Fase 3: Optimizar auto_modificar() (PRIORIDAD MEDIA)
**Objetivo:** Actualización batch de relaciones.

**Tareas:**
1. Identificar pares a reforzar en una sola pasada
2. Actualizar matriz con operaciones vectoriales
   ```python
   # En vez de loops anidados
   conceptos_activos_idx = np.where(activacion > 0.2)[0]
   pares = np.meshgrid(conceptos_activos_idx, conceptos_activos_idx)
   mask_pares = pares[0] < pares[1]  # solo upper triangle

   # Actualizar en batch
   self.matriz_relaciones[pares] = np.clip(
       self.matriz_relaciones[pares] + fuerza * np.random.random(pares.shape),
       0, 1
   )
   ```

**Criterio de hecho:**
- ✅ Misma lógica de refuerzo
- ✅ Más rápido (3-5x)
- ✅ Tests de regresión pasan

### Fase 4: Historial Vectorizado (PRIORIDAD BAJA)
**Objetivo:** Análisis temporal eficiente.

**Tareas:**
1. Migrar historial a np.array 2D
2. Implementar métricas temporales vectorizadas
   ```python
   def analizar_drift_concepto(self, nombre):
       historial = self.conceptos[nombre]['historial']  # shape (n, dim)
       drift = np.diff(historial, axis=0)  # cambios temporales
       magnitud_drift = np.linalg.norm(drift, axis=1)
       return {
           'drift_promedio': magnitud_drift.mean(),
           'drift_max': magnitud_drift.max(),
           'estabilidad': 1.0 / (magnitud_drift.std() + 1e-10)
       }
   ```

**Criterio de hecho:**
- ✅ Análisis temporal 5-10x más rápido
- ✅ Nuevas métricas disponibles
- ✅ Compatible con visualizaciones

### Fase 5: Sparse Matrix para Escalabilidad (FUTURO)
**Objetivo:** Escalar a 10,000+ conceptos.

**Condición:** Solo si n_conceptos > 5000 (matriz densa = 400MB+).

**Tareas:**
1. Usar scipy.sparse.csr_matrix para matriz de relaciones
2. Adaptar operaciones a formato sparse
3. Benchmark memoria vs velocidad

**Trade-off:**
- ✅ Menos memoria (solo guardar edges no-cero)
- ⚠️ Operaciones sparse pueden ser más lentas para matrices densas
- ⚠️ Mayor complejidad de código

---

## 4. ESTIMACIÓN DE IMPACTO

### 4.1 Rendimiento

| Operación | Actual | Con Refactorización | Mejora |
|-----------|--------|---------------------|--------|
| Propagación (n=100) | ~10 ms | ~1 ms | **10x** |
| Propagación (n=1000) | ~200 ms | ~15 ms | **13x** |
| Auto-modificación (n=100) | ~5 ms | ~1 ms | **5x** |
| Normalización | ~2 ms | ~0.1 ms | **20x** |
| Guardar estado | ~100 ms | ~50 ms | **2x** |

**Mejora global estimada:** 3-10x en operaciones críticas, 2-3x en ciclo completo.

### 4.2 Memoria

| Estructura | Actual | Propuesta | Cambio |
|------------|--------|-----------|--------|
| 100 conceptos | ~50 KB | ~100 KB | +50 KB |
| 1000 conceptos | ~500 KB | ~4 MB | +3.5 MB |
| 10000 conceptos | ~5 MB | ~400 MB | +395 MB ⚠️ |

**Recomendación:**
- Para n < 5000: matriz densa (óptimo)
- Para n >= 5000: migrar a sparse matrix (Fase 5)

### 4.3 Escalabilidad

**Límites actuales:**
- ~1000 conceptos antes de latencia notable
- ~5000 conceptos máximo práctico

**Límites con refactorización:**
- ~10,000 conceptos sin problemas (matriz densa)
- ~100,000+ conceptos posible (sparse matrix)

---

## 5. RIESGOS Y BREAKING CHANGES

### 5.1 Breaking Changes Identificados

#### **Cambio #1: API de activar() retorna numpy array**
**Antes:**
```python
resultado = sistema.activar('Python')  # retorna [dict, dict, dict]
resultado[-1]['Python']  # acceso por nombre
```

**Después:**
```python
resultado = sistema.activar('Python')  # retorna [np.array, np.array, np.array]
idx = sistema.conceptos_idx['Python']
resultado[-1][idx]  # acceso por índice
```

**Mitigación:**
- Mantener modo legacy con parámetro
- Crear helper: `sistema.get_activacion(resultado, nombre_concepto)`

#### **Cambio #2: Orden de conceptos importa**
Con matriz, el orden de conceptos está fijo por índices. Añadir concepto nuevo requiere:
- Redimensionar matriz (costoso)
- O reservar espacio (waste de memoria)

**Mitigación:**
- Pre-allocar matriz para max_conceptos (ej: 10,000)
- Lazy initialization: solo crecer cuando necesario

#### **Cambio #3: Serialización diferente**
Guardar/cargar debe manejar matrices numpy.

**Antes:**
```python
json.dump(self.relaciones, f)  # dict serializable
```

**Después:**
```python
np.save(f, self.matriz_relaciones)  # formato numpy
```

**Mitigación:**
- Mantener compatibilidad con formato antiguo
- Detectar formato automáticamente al cargar

### 5.2 Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Tests fallan por diferencias numéricas | Alta | Medio | Tolerancia ±0.05 |
| Regresión de rendimiento en casos pequeños | Media | Bajo | Benchmark continuo |
| Uso excesivo de memoria | Baja | Alto | Sparse matrix (Fase 5) |
| Breaking API externa | Media | Alto | Mantener wrappers legacy |

---

## 6. ESTRATEGIA DE TESTING

### 6.1 Tests Unitarios Nuevos

```python
# test_nucleo_numpy.py

def test_matriz_relaciones_equivalencia():
    """Verificar matriz equivale a dict de relaciones"""
    ...

def test_propagacion_vectorizada_determinista():
    """Con seed fija, resultados deben ser reproducibles"""
    np.random.seed(42)
    ...

def test_activar_vectorizado_vs_legacy():
    """Comparar resultados con método original"""
    ...

def test_rendimiento_propagacion():
    """Benchmark: vectorizado debe ser >2x más rápido"""
    ...

def test_auto_modificacion_batch():
    """Verificar actualización batch de relaciones"""
    ...

def test_memoria_matriz_vs_dict():
    """Comparar uso de memoria"""
    ...

def test_serialización_matriz():
    """Guardar y cargar matriz"""
    ...
```

### 6.2 Tests de Regresión

Ejecutar TODOS los tests existentes:
```bash
pytest tests/test_nucleo.py -v
pytest tests/test_emergente.py -v
```

Todos deben pasar sin modificaciones.

### 6.3 Benchmarks

```python
# benchmark_refactorizacion.py

import time
import numpy as np

def benchmark_activar(sistema, n_repeticiones=100):
    tiempos_legacy = []
    tiempos_nuevo = []

    for _ in range(n_repeticiones):
        t0 = time.time()
        sistema.activar('Python', vectorizado=False)
        tiempos_legacy.append(time.time() - t0)

        t0 = time.time()
        sistema.activar('Python', vectorizado=True)
        tiempos_nuevo.append(time.time() - t0)

    print(f"Legacy: {np.mean(tiempos_legacy)*1000:.2f}ms ± {np.std(tiempos_legacy)*1000:.2f}ms")
    print(f"Nuevo:  {np.mean(tiempos_nuevo)*1000:.2f}ms ± {np.std(tiempos_nuevo)*1000:.2f}ms")
    print(f"Speedup: {np.mean(tiempos_legacy)/np.mean(tiempos_nuevo):.2f}x")
```

---

## 7. DEPENDENCIAS

### 7.1 Ya Instaladas
- ✅ numpy>=1.20.0 (requirements.txt línea 1)
- ✅ matplotlib>=3.5.0 (visualización)
- ✅ networkx>=2.8.0 (grafo)

### 7.2 Opcionales (Fase 5)
- scipy>=1.9.0 (sparse matrices)
- numba>=0.56.0 (JIT compilation para loops inevitables)

---

## 8. RESUMEN EJECUTIVO

### Estado Actual
- ✅ nucleo.py YA usa numpy para vectores
- ⚠️ Operaciones de propagación SIN vectorizar (bucles Python)
- ⚠️ Relaciones como dict de listas (no vectorizable)

### Oportunidades de Optimización
1. **Matriz de adyacencia** → 10-50x más rápido en propagación
2. **Propagación vectorizada** → eliminar triple loop anidado
3. **Vectorización de activaciones** → broadcasting automático
4. **Batch updates** en auto-modificación → 5x más rápido

### Impacto Esperado
- 🚀 **3-10x mejora** en operaciones críticas
- 📈 **Escalabilidad** a 10,000+ conceptos
- 💾 **+4 MB** memoria (1000 conceptos) — aceptable

### Riesgos Controlados
- API compatible con wrappers legacy
- Tests de regresión completos
- Migración incremental por fases

---

## 9. PRÓXIMOS PASOS RECOMENDADOS

### Paso 1: Aprobar Plan
Lucas revisa y aprueba este análisis.

### Paso 2: Implementar Fase 1
Worker-core implementa infraestructura base (matriz de relaciones).

**Tiempo estimado:** 2-4 horas
**Archivos afectados:** src/core/nucleo.py (añadir métodos, no modificar existentes)

### Paso 3: Tests y Benchmark
Worker-infra crea tests unitarios y benchmarks.

**Tiempo estimado:** 1-2 horas
**Archivos nuevos:** tests/test_nucleo_numpy.py, tests/benchmark_refactorizacion.py

### Paso 4: Implementar Fase 2
Worker-core refactoriza activar() con vectorización.

**Tiempo estimado:** 3-5 horas
**Archivos afectados:** src/core/nucleo.py (método activar)

### Paso 5: Validación
Ejecutar todos los tests, benchmarks, y experimentos de validación.

**Tiempo estimado:** 1 hora

### Paso 6: Fases 3-4 (opcional, según resultados)
Continuar con auto_modificar() e historial si Fases 1-2 exitosas.

---

## 10. CONCLUSIÓN

El código actual de IANAE usa numpy para vectores individuales pero NO aprovecha vectorización para operaciones batch. La refactorización propuesta puede lograr **3-10x mejora de rendimiento** con riesgo controlado y sin breaking changes (mediante wrappers).

**Recomendación:** APROBAR e implementar en fases incrementales, comenzando con matriz de relaciones (Fase 1) y propagación vectorizada (Fase 2).

**Criterio de éxito global:**
- ✅ Mejora de rendimiento >2x en propagación
- ✅ Todos los tests existentes pasan
- ✅ Escalabilidad a 5000+ conceptos
- ✅ Sin breaking changes en API pública

---

**Reporte generado por:** worker-core
**Sistema:** claude-orchestra
**Arquitecto:** Daemon IA

