# Flujos de Trabajo y Ciclos de Vida en IANAE

Este documento proporciona una descripción detallada de los principales flujos de trabajo y ciclos de vida dentro del sistema IANAE. Está dirigido a desarrolladores y usuarios avanzados que necesitan comprender cómo interactúan los diferentes componentes y procesos a lo largo del tiempo.

## 1. Ciclo de Vida de Conceptos

### 1.1 Modelo Detallado del Ciclo de Vida

```
                                   +---------------------+
                                   |                     |
                                   v                     |
+---------------+    +---------+    +-------------+    +----------------+
| Creación      |    | Inicial |    | Activo      |    | Consolidado    |
| - Vector base |--->| - Sin   |--->| - Múltiples |--->| - Conexiones   |
| - Vector con  |    |   hist. |    |   activ.    |    |   estables     |
|   incertidum. |    | - Pocas |    | - Nuevas    |    | - Alta         |
|               |    |   conex.|    |   conexiones|    |   centralidad  |
+---------------+    +---------+    +-------------+    +----------------+
                                          |                    |
                                          v                    v
                                   +-------------+    +----------------+
                                   | Debilitado  |    | Central        |
                                   | - Sin activ.|    | - Núcleo red   |
                                   | - Conexiones|    | - Alta         |
                                   |   débiles   |    |   influencia   |
                                   +-------------+    +----------------+
```

### 1.2 Estados de los Conceptos

#### Creación
- **Descripción**: Momento inicial en que se añade un concepto al sistema.
- **Características**:
  - Se genera o proporciona un vector base (dimensionalidad fija).
  - Se añade un componente de incertidumbre (ruido gaussiano).
  - Se inicializan contadores y métricas (activaciones: 0).
  - Se asigna una "edad" basada en el estado actual del sistema.
- **Código relevante**:
  ```python
  def añadir_concepto(self, nombre, atributos=None, incertidumbre=None):
      # Vector base + incertidumbre
      # Inicialización de métricas
  ```

#### Inicial
- **Descripción**: Etapa temprana de la vida de un concepto.
- **Características**:
  - Pocas o ninguna activación previa.
  - Número limitado de conexiones con otros conceptos.
  - Alta plasticidad (susceptible a cambios rápidos).
- **Indicadores**:
  - `concepto['activaciones'] < 5`
  - Pocos vecinos en el grafo.

#### Activo
- **Descripción**: Concepto que participa frecuentemente en procesos de activación.
- **Características**:
  - Múltiples activaciones recientes.
  - Formación activa de nuevas conexiones.
  - Puede participar en la generación de nuevos conceptos.
- **Indicadores**:
  - `concepto['activaciones'] > 5`
  - `concepto['ultima_activacion']` reciente.

#### Consolidado
- **Descripción**: Concepto con rol estable en la red.
- **Características**:
  - Conexiones estables y fuertes con otros conceptos.
  - Patrón de activación predecible.
  - Menor plasticidad que conceptos más nuevos.
- **Indicadores**:
  - Alto valor de centralidad en el grafo.
  - Pesos de conexiones estables.

#### Debilitado
- **Descripción**: Concepto que ha perdido relevancia en el sistema.
- **Características**:
  - Sin activaciones recientes.
  - Conexiones debilitadas progresivamente.
  - Puede eventualmente ser "olvidado" o reemplazado.
- **Indicadores**:
  - `concepto['ultima_activacion']` muy antigua.
  - Conexiones con pesos bajos.

#### Central
- **Descripción**: Concepto que forma parte del núcleo de la red.
- **Características**:
  - Alta centralidad e influencia.
  - Numerosas conexiones con otros conceptos importantes.
  - Fundamental para la coherencia del sistema.
- **Indicadores**:
  - Alto grado en el grafo (`len(relaciones[concepto])`).
  - Alto valor de centralidad de intermediación (betweenness centrality).

### 1.3 Transiciones entre Estados

#### De Inicial a Activo
- **Desencadenante**: Múltiples activaciones en corto tiempo.
- **Proceso**:
  - Incremento del contador de activaciones.
  - Formación de nuevas conexiones durante la propagación.
- **Código relevante**:
  ```python
  # En activar():
  self.conceptos[concepto_inicial]['activaciones'] += 1
  self.conceptos[concepto_inicial]['ultima_activacion'] = self.metricas['ciclos_pensamiento']
  ```

#### De Activo a Consolidado
- **Desencadenante**: Activación consistente durante un período prolongado.
- **Proceso**:
  - Estabilización de conexiones a través de auto-modificación.
  - Participación frecuente en cadenas de pensamiento.
- **Código relevante**:
  ```python
  # En auto_modificar():
  # Refuerzo de conexiones usadas frecuentemente
  nuevo_peso = min(1.0, peso_actual + fuerza * np.random.random())
  ```

#### De Activo/Consolidado a Debilitado
- **Desencadenante**: Falta de activación durante múltiples ciclos.
- **Proceso**:
  - Debilitamiento gradual de conexiones.
  - Reducción de probabilidad de selección para activación.
- **Código relevante**:
  ```python
  # En auto_modificar():
  # Debilitar conexiones poco usadas
  if (self.metricas['ciclos_pensamiento'] - self.conceptos[c1]['ultima_activacion'] > 10 and
      self.metricas['ciclos_pensamiento'] - self.conceptos[vecino]['ultima_activacion'] > 10):
      nuevo_peso = max(0.05, peso - fuerza * 0.2 * np.random.random())
  ```

#### De Consolidado a Central
- **Desencadenante**: Alta centralidad y múltiples conexiones fuertes.
- **Proceso**:
  - Desarrollo natural a través de múltiples ciclos de vida del sistema.
  - Formación de un "núcleo semántico" en la red.
- **Relación con métricas**:
  - No hay transición explícita en el código, emerge del patrón de conexiones.

## 2. Ciclo de Vida del Sistema

### 2.1 Modelo Detallado del Ciclo de Vida del Sistema

```
                                Ciclo Principal
                      +--------------------------------+
                      |                                |
                      v                                |
+--------------+    +---------+    +-------------+    +----------------+
| Inicializa-  |    | Activa- |    | Auto-       |    | Generación     |
| ción         |--->| ción    |--->| modificación|--->| de Conceptos   |
| - Conceptos  |    | - Propa-|    | - Refuerzo  |    | - Combinación  |
|   semilla    |    |   gación|    |   conexiones|    |   conceptos    |
| - Relaciones |    | - Activ.|    | - Debilita- |    | - Creación     |
|   iniciales  |    |   selec.|    |   miento    |    |   conexiones   |
+--------------+    +---------+    +-------------+    +----------------+
       |                                |                      |
       |                                v                      |
       |                         +-------------+               |
       |                         | Medición    |               |
       |                         | - Métricas  |               |
       |                         | - Ajuste    |               |
       |                         | - Visual.   |               |
       |                         +-------------+               |
       |                                                       |
       v                                                       v
+--------------+                                        +----------------+
| Guardado     |<---------------------------------------| Evolución      |
| - Serializa- |                                        | - Emergencia   |
|   ción       |                                        |   estructuras  |
| - Persistenc.|                                        | - Auto-        |
|              |                                        |   organización |
+--------------+                                        +----------------+
```

### 2.2 Fases del Ciclo de Vida

#### Inicialización
- **Descripción**: Creación y configuración inicial del sistema.
- **Procesos**:
  - Creación de la instancia de `ConceptosDifusos`.
  - Adición de conceptos semilla.
  - Establecimiento de relaciones iniciales.
  - Configuración de parámetros (dimensionalidad, incertidumbre).
- **Código relevante**:
  ```python
  def crear_sistema_nuevo():
      sistema = ConceptosDifusos(dim_vector=dim)
      # Añadir conceptos semilla
      for c in conceptos_base:
          sistema.añadir_concepto(c)
      # Establecer relaciones iniciales
      for c1, c2 in pares:
          sistema.relacionar(c1, c2)
  ```

#### Activación
- **Descripción**: Proceso de activación y propagación en la red conceptual.
- **Procesos**:
  - Selección de conceptos para activar (manual o automática).
  - Propagación de activación a través de la red.
  - Registro de patrones de activación.
- **Código relevante**:
  ```python
  def activar(self, concepto_inicial, pasos=3, temperatura=0.1):
      # Inicializar activación
      # Propagar a través de la red
      # Registrar resultados
  ```

#### Auto-modificación
- **Descripción**: Proceso mediante el cual el sistema modifica su propia estructura.
- **Procesos**:
  - Refuerzo de conexiones entre conceptos co-activados.
  - Debilitamiento de conexiones poco utilizadas.
  - Ajuste de pesos basado en patrones de activación.
- **Código relevante**:
  ```python
  def auto_modificar(self, fuerza=0.1):
      # Reforzar conexiones entre conceptos activos
      # Debilitar conexiones poco usadas
  ```

#### Generación de Conceptos
- **Descripción**: Creación de nuevos conceptos combinando los existentes.
- **Procesos**:
  - Selección de conceptos base (preferentemente activos).
  - Combinación de vectores con factores aleatorios.
  - Establecimiento de conexiones iniciales para nuevos conceptos.
- **Código relevante**:
  ```python
  def generar_concepto(self, conceptos_base=None, numero=1):
      # Seleccionar conceptos base
      # Combinar vectores
      # Crear nuevos conceptos
      # Establecer relaciones iniciales
  ```

#### Medición
- **Descripción**: Evaluación del estado y comportamiento del sistema.
- **Procesos**:
  - Registro de métricas (conceptos, conexiones, ciclos).
  - Visualización de la red conceptual.
  - Análisis de patrones emergentes.
- **Código relevante**:
  ```python
  # En ciclo_vital():
  # Actualización de métricas
  self.metricas['edad'] += 1
  
  # Visualización
  if visualizar_cada > 0 and i % visualizar_cada == 0:
      self.visualizar(activaciones=resultado[-1])
  ```

#### Guardado
- **Descripción**: Persistencia del estado del sistema.
- **Procesos**:
  - Serialización de conceptos y relaciones.
  - Almacenamiento en formato JSON.
  - Registro de metadatos (timestamp, métricas).
- **Código relevante**:
  ```python
  def guardar(self, ruta='ianae_estado.json'):
      # Preparar estado para serialización
      # Convertir arrays numpy a listas
      # Guardar a archivo JSON
  ```

#### Evolución
- **Descripción**: Cambios a largo plazo en la estructura del sistema.
- **Procesos**:
  - Emergencia de estructuras organizadas.
  - Formación de "comunidades" conceptuales.
  - Especialización de regiones de la red.
- **Relación con el código**:
  - No implementada explícitamente, emerge de los procesos anteriores.
  - Observable a través de visualizaciones después de múltiples ciclos.

### 2.3 Ciclo Vital Automatizado

El método `ciclo_vital()` implementa un proceso automatizado que ejecuta múltiples fases del ciclo de vida en secuencia:

```python
def ciclo_vital(self, num_ciclos=1, auto_mod=True, visualizar_cada=5):
    for i in range(num_ciclos):
        self.metricas['edad'] += 1
        
        # Seleccionar concepto para activar
        concepto_inicial = np.random.choice(conceptos, p=probabilidades)
        
        # Activar el concepto
        resultado = self.activar(concepto_inicial, pasos=pasos, temperatura=0.2)
        
        # Auto-modificación del sistema
        if auto_mod and random.random() < 0.8:
            self.auto_modificar(fuerza=0.15)
            
        # Ocasionalmente generar nuevos conceptos
        if random.random() < 0.2:
            self.generar_concepto(numero=random.randint(1, 2))
```

Este método permite que el sistema evolucione autónomamente a lo largo del tiempo, siguiendo patrones emergentes de activación y modificación.

## 3. Flujos de Trabajo del Usuario

### 3.1 Creación y Exploración Básica

```
+----------------+    +----------------+    +----------------+
| Crear Sistema  |--->| Añadir         |--->| Explorar       |
| - Inicializar  |    | Conceptos      |    | Relaciones     |
| - Configurar   |    | - Manual       |    | - Visualizar   |
+----------------+    | - Desde texto  |    | - Activar      |
                      +----------------+    +----------------+
```

**Descripción**: Este flujo representa el uso básico del sistema, donde un usuario crea un sistema, añade conceptos y explora sus relaciones.

**Ejemplo de código**:
```python
# Crear sistema
sistema = ConceptosDifusos(dim_vector=15)

# Añadir conceptos
sistema.añadir_concepto("idea")
sistema.añadir_concepto("creatividad")
sistema.relacionar("idea", "creatividad")

# Explorar
sistema.visualizar()
sistema.activar("idea", pasos=3)
```

### 3.2 Experimentación Estructurada

```
+----------------+    +----------------+    +----------------+    +----------------+
| Configuración  |--->| Ejecución de   |--->| Análisis de    |--->| Modificación   |
| - Parámetros   |    | Experimentos   |    | Resultados     |    | - Ajuste de    |
| - Conceptos    |    | - Divergencia  |    | - Métricas     |    |   parámetros   |
| - Objetivos    |    | - Asociación   |    | - Patrones     |    | - Nuevos       |
+----------------+    +----------------+    +----------------+    |   experimentos |
                                                                  +----------------+
```

**Descripción**: Este flujo representa un enfoque más científico, donde el usuario configura experimentos específicos, los ejecuta y analiza los resultados para guiar futuras experimentaciones.

**Ejemplo de código**:
```python
# En experimento.py:
def ejecutar_experimento():
    # Configuración
    sistema = ConceptosDifusos(dim_vector=15)
    # Añadir conceptos iniciales
    
    # Crear sistema de pensamiento
    pensamiento = PensamientoEmergente(sistema=sistema)
    
    # Ejecutar experimentos
    resultado = pensamiento.explorar_asociaciones("emergencia", profundidad=3)
    
    # Analizar resultados
    pensamiento.visualizar_pensamiento(-1)
    
    # Ajustar y continuar
    resultado = pensamiento.experimento_divergencia("creatividad", num_rutas=4)
```

### 3.3 Desarrollo Evolutivo

```
+----------------+    +----------------+    +----------------+    +----------------+
| Configuración  |--->| Ejecución de   |--->| Guardado de    |--->| Continuar      |
| Inicial        |    | Ciclos de Vida |    | Estado         |    | Evolución      |
| - Semillas     |    | - Auto-modif.  |    | - Persistencia |    | - Cargar       |
| - Relaciones   |    | - Generación   |    | - Versiones    |    | - Nuevos ciclos|
+----------------+    +----------------+    +----------------+    +----------------+
```

**Descripción**: Este flujo se centra en el desarrollo evolutivo del sistema a lo largo del tiempo, permitiendo pausar, guardar y continuar el proceso de evolución.

**Ejemplo de código**:
```python
# Configuración inicial
sistema = ConceptosDifusos()
# Añadir conceptos semilla...

# Ejecutar ciclos de vida
sistema.ciclo_vital(num_ciclos=100, visualizar_cada=10)

# Guardar estado
sistema.guardar("evolucion_dia1.json")

# Más tarde... continuar evolución
sistema = ConceptosDifusos.cargar("evolucion_dia1.json")
sistema.ciclo_vital(num_ciclos=100, visualizar_cada=10)
```

### 3.4 Integración de Texto y Pensamiento

```
+----------------+    +----------------+    +----------------+    +----------------+
| Importación    |--->| Procesamiento  |--->| Generación de  |--->| Análisis de    |
| de Texto       |    | - Extracción   |    | Pensamiento    |    | Resultados     |
| - Archivos     |    |   conceptos    |    | - Asociaciones |    | - Visualización|
| - Entrada      |    | - Relaciones   |    | - Cadenas      |    | - Interpretac. |
+----------------+    +----------------+    +----------------+    +----------------+
```

**Descripción**: Este flujo se enfoca en la importación de conocimiento desde texto y la generación de pensamiento basado en ese conocimiento.

**Ejemplo de código**:
```python
# Crear sistema de pensamiento
pensamiento = PensamientoEmergente()

# Importar texto
texto = "La inteligencia emergente es un fenómeno donde..."
conceptos = pensamiento.cargar_conceptos_desde_texto(texto)

# Generar pensamiento
for i in range(3):
    cadena = pensamiento.generar_pensamiento(longitud=6)
    print(cadena)

# Visualizar y analizar
pensamiento.visualizar_pensamiento(-1)
```

## 4. Flujos de Datos Internos

### 4.1 Flujo de Propagación de Activación

```
+----------------+    +----------------+    +----------------+    +----------------+
| Activación     |--->| Propagación a  |--->| Normalización  |--->| Registro de    |
| Inicial        |    | Vecinos        |    | - Suma unitaria|    | Estado Final   |
| - Concepto     |    | - Según fuerza |    | - Añadir ruido |    | - Historial    |
| - Valor 1.0    |    | - Con ruido    |    | - Limitación   |    | - Métricas     |
+----------------+    +----------------+    +----------------+    +----------------+
```

**Descripción**: Este flujo muestra cómo se propaga la activación internamente en cada paso.

**Código relevante**:
```python
# En activar():
# Activación inicial
activacion = {c: 0.0 for c in self.conceptos}
activacion[concepto_inicial] = 1.0

# Por cada paso
for _ in range(pasos):
    nueva_activacion = activacion.copy()
    
    # Propagación a vecinos
    for concepto, nivel in activacion.items():
        if nivel > 0.1:  # Umbral de activación
            for vecino, fuerza in self.relaciones[concepto]:
                propagacion = nivel * fuerza * factor_aleatorio
                nueva_activacion[vecino] = max(nueva_activacion[vecino], propagacion)
    
    # Normalización
    total = sum(nueva_activacion.values()) + 1e-10
    for c in nueva_activacion:
        nueva_activacion[c] = nueva_activacion[c] / total
        nueva_activacion[c] += np.random.normal(0, temperatura * 0.5)
        nueva_activacion[c] = max(0, min(1, nueva_activacion[c]))
    
    activacion = nueva_activacion
    resultados.append(activacion.copy())
```

### 4.2 Flujo de Auto-modificación

```
+----------------+    +----------------+    +----------------+
| Identificación |--->| Modificación   |--->| Actualización  |
| - Conceptos    |    | - Refuerzo     |    | - Grafo        |
|   activos      |    | - Debilitam.   |    | - Relaciones   |
| - Conexiones   |    | - Nuevas       |    | - Métricas     |
+----------------+    |   conexiones   |    |                |
                      +----------------+    +----------------+
```

**Descripción**: Este flujo muestra el proceso interno de auto-modificación.

**Código relevante**:
```python
def auto_modificar(self, fuerza=0.1):
    # Obtener la última activación
    ultima = self.historial_activaciones[-1]['resultado']
    conceptos_activos = [c for c, a in ultima.items() if a > 0.2]
    
    # Reforzar conexiones entre conceptos activos
    for i in range(len(conceptos_activos)):
        for j in range(i+1, len(conceptos_activos)):
            c1 = conceptos_activos[i]
            c2 = conceptos_activos[j]
            
            # Si ya hay conexión, reforzarla
            if self.grafo.has_edge(c1, c2):
                peso_actual = self.grafo[c1][c2]['weight']
                nuevo_peso = min(1.0, peso_actual + fuerza * np.random.random())
                
                # Actualizar en grafo y relaciones
                self.grafo[c1][c2]['weight'] = nuevo_peso
                # Actualizar en las listas de relaciones...
                
    # Debilitar conexiones poco usadas
    # ...
```

### 4.3 Flujo de Generación de Conceptos

```
+----------------+    +----------------+    +----------------+    +----------------+
| Selección de   |--->| Combinación    |--->| Creación de    |--->| Establecimiento|
| Conceptos Base |    | de Vectores    |    | Nuevo Concepto |    | de Relaciones  |
| - Por activac. |    | - Ponderada    |    | - Nombre       |    | - Con conceptos|
| - Aleatorios   |    | - Con ruido    |    | - Vector base  |    |   base         |
+----------------+    +----------------+    +----------------+    +----------------+
```

**Descripción**: Este flujo muestra el proceso de generación de nuevos conceptos.

**Código relevante**:
```python
def generar_concepto(self, conceptos_base=None, numero=1):
    # Elegir conceptos base
    if conceptos_base is None:
        conceptos_candidatos = list(self.conceptos.keys())
        # Selección ponderada por activaciones...
        
    # Para cada nuevo concepto a generar
    for _ in range(numero):
        # Combinar vectores base
        vector_combinado = np.zeros(self.dim_vector)
        for c in conceptos_base:
            vector_combinado += self.conceptos[c]['base'] * np.random.uniform(0.5, 1.5)
            
        # Normalizar y añadir ruido
        if np.linalg.norm(vector_combinado) > 0:
            vector_combinado = vector_combinado / np.linalg.norm(vector_combinado)
            vector_combinado += np.random.normal(0, 0.3, self.dim_vector)
            
            # Crear el nuevo concepto
            nuevo_nombre = f"concepto_{len(self.conceptos)}"
            self.añadir_concepto(nuevo_nombre, vector_combinado)
            
            # Relacionarlo con los conceptos base
            for c in conceptos_base:
                self.relacionar(nuevo_nombre, c)
```

## 5. Integración con Interfaces de Usuario

### 5.1 Interfaz de Línea de Comandos (main.py)

```
+----------------+    +----------------+    +----------------+
| Menú de        |--->| Ejecución de   |--->| Presentación   |
| Opciones       |    | Funcionalidad  |    | de Resultados  |
| - Selección    |    | - Llamadas a   |    | - Consola      |
| - Parámetros   |    |   métodos      |    | - Visualización|
+----------------+    +----------------+    +----------------+
```

**Descripción**: Flujo de interacción con el usuario a través de la interfaz de línea de comandos.

**Código relevante**:
```python
def main():
    # Menú principal
    while True:
        print("\nMenú Principal de IANAE")
        # Mostrar opciones...
        
        opcion = input("\nSelecciona una opción: ")
        
        if opcion == '1':
            sistema.visualizar()
        elif opcion == '2':
            nombre = input("Nombre del concepto: ")
            sistema.añadir_concepto(nombre)
            # ...
```

### 5.2 Experimentación Guiada (experimento.py)

```
+----------------+    +----------------+    +----------------+    +----------------+
| Presentación   |--->| Ejecución      |--->| Visualización  |--->| Transición a   |
| de Experimento |    | Secuencial     |    | de Resultados  |    | Siguiente Paso |
| - Descripción  |    | - Pasos        |    | - Gráficos     |    | - Confirmación |
| - Objetivos    |    | - Resultados   |    | - Texto        |    | - Automático   |
+----------------+    | intermedios    |    +----------------+    +----------------+
                      +----------------+
```

**Descripción**: Flujo de interacción en experimentos guiados.

**Código relevante**:
```python
def ejecutar_experimento():
    print("=== Experimento IANAE ===")
    print("Este experimento demostrará las capacidades del sistema IANAE")
    
    # Paso 1
    print("\n[1/6] Creando sistema conceptual base...")
    # Implementación...
    sistema.visualizar(titulo="Sistema conceptual inicial")
    
    # Paso 2
    print("\n[2/6] Importando conceptos adicionales desde texto...")
    # Implementación...
    
    # Y así sucesivamente...
```

Estos flujos de trabajo detallados proporcionan una visión completa de cómo funciona IANAE a lo largo del tiempo y cómo interactúan sus diferentes componentes.
