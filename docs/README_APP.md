# IANAE: Inteligencia Adaptativa No Algorítmica Emergente
## Guía de Usuario y Documentación

## Introducción

IANAE (Inteligencia Adaptativa No Algorítmica Emergente) es un proyecto experimental que explora un nuevo paradigma de inteligencia artificial basado en conceptos difusos, relaciones probabilísticas y comportamientos emergentes, en lugar de reglas algorítmicas tradicionales.

A diferencia de los sistemas de IA convencionales que siguen reglas deterministas, IANAE utiliza:

- **Conceptos representados como vectores difusos**: Cada concepto tiene una representación vectorial con incertidumbre inherente.
- **Relaciones probabilísticas**: Las conexiones entre conceptos tienen diferentes fuerzas y evolucionan con el tiempo.
- **Propagación no determinística**: La activación se propaga a través de la red con elementos estocásticos.
- **Auto-modificación**: El sistema puede alterar sus propias estructuras basándose en la experiencia.
- **Emergencia de nuevos conceptos**: El sistema puede generar nuevos conceptos combinando los existentes.

## Estructura del Proyecto

El proyecto está organizado en los siguientes archivos:

- `nucleo.py`: El componente central con la implementación del sistema de conceptos difusos.
- `emergente.py`: Extensión que proporciona capacidades de pensamiento emergente.
- `main.py`: Interfaz interactiva principal para usar el sistema.
- `experimento.py`: Script para ejecutar experimentos que demuestran las capacidades del sistema.

## Instalación

1. Asegúrate de tener Python 3.6 o superior instalado.
2. Instala las dependencias requeridas:
   ```
   pip install numpy matplotlib networkx
   ```
3. Clona o descarga los archivos del proyecto.

## Uso Básico

### A través de la interfaz interactiva

Para iniciar la interfaz interactiva:

```bash
python main.py
```

Esta interfaz te permitirá:
- Visualizar el estado actual del sistema
- Añadir nuevos conceptos
- Activar conceptos y observar la propagación
- Ejecutar ciclos de vida del sistema
- Generar nuevos conceptos
- Auto-modificar el sistema
- Guardar y cargar el estado

### A través de experimentos

Para ejecutar el menú de experimentos:

```bash
python experimento.py
```

Para ejecutar directamente el experimento completo:

```bash
python experimento.py completo
```

## Conceptos Fundamentales

### Conceptos Difusos

En IANAE, un concepto no es simplemente una etiqueta, sino un vector multidimensional con incertidumbre inherente:

```python
concepto = {
    'base': vector_base,              # Vector base que representa al concepto
    'actual': vector_base + ruido,    # Vector con incertidumbre
    'historial': [vector_base],       # Historial de evolución
    'creado': edad_sistema,           # Cuándo se creó
    'activaciones': 0,                # Contador de activaciones
    'ultima_activacion': 0,           # Cuándo se activó por última vez
    'fuerza': 1.0                     # Fuerza inicial del concepto
}
```

### Relaciones Probabilísticas

Las relaciones entre conceptos no son binarias (existe/no existe), sino que tienen una fuerza que puede variar con el tiempo:

```python
relaciones[concepto1].append((concepto2, fuerza))
```

### Propagación de Activación

Cuando un concepto se activa, esta activación se propaga a través de la red siguiendo las relaciones:

1. La propagación depende de la fuerza de las relaciones
2. Incluye elementos estocásticos controlados por el parámetro "temperatura"
3. La normalización y no-linealidades introducen comportamientos emergentes

### Auto-modificación

El sistema puede modificar sus propias estructuras basándose en patrones de activación:

1. Refuerza conexiones entre conceptos activados simultáneamente
2. Debilita conexiones poco utilizadas
3. Crea nuevas conexiones cuando es apropiado

### Generación de Conceptos

IANAE puede generar nuevos conceptos combinando los existentes:

1. Selecciona conceptos base (preferentemente los más activos)
2. Combina sus vectores con factores aleatorios
3. Añade ruido para fomentar novedad
4. Relaciona el nuevo concepto con sus conceptos padre

## Ejemplos de Uso

### Ejemplo 1: Crear y relacionar conceptos básicos

```python
from nucleo import ConceptosDifusos

# Crear sistema
sistema = ConceptosDifusos(dim_vector=10)

# Añadir conceptos
sistema.añadir_concepto("pensamiento")
sistema.añadir_concepto("lenguaje")
sistema.añadir_concepto("conocimiento")

# Relacionar conceptos
sistema.relacionar("pensamiento", "lenguaje")
sistema.relacionar("lenguaje", "conocimiento")
sistema.relacionar("pensamiento", "conocimiento")

# Visualizar
sistema.visualizar()
```

### Ejemplo 2: Explorar asociaciones

```python
from nucleo import ConceptosDifusos
from emergente import PensamientoEmergente

# Crear sistema con conceptos
sistema = ConceptosDifusos(dim_vector=10)
sistema.añadir_concepto("creativo")
sistema.añadir_concepto("arte")
sistema.añadir_concepto("ciencia")
sistema.añadir_concepto("música")
sistema.añadir_concepto("matemáticas")

# Relacionar algunos conceptos
sistema.relacionar("creativo", "arte")
sistema.relacionar("arte", "música")
sistema.relacionar("ciencia", "matemáticas")
sistema.relacionar("creativo", "ciencia")

# Crear sistema de pensamiento
pensamiento = PensamientoEmergente(sistema=sistema)

# Explorar asociaciones
resultado = pensamiento.explorar_asociaciones("creativo", profundidad=3, anchura=5)
print(resultado)

# Visualizar
pensamiento.visualizar_pensamiento(-1)
```

### Ejemplo 3: Generar cadenas de pensamiento

```python
from nucleo import ConceptosDifusos
from emergente import PensamientoEmergente

# Crear y configurar sistema
sistema = ConceptosDifusos(dim_vector=15)
# Añadir múltiples conceptos y relaciones...

# Crear sistema de pensamiento
pensamiento = PensamientoEmergente(sistema=sistema)

# Generar cadena de pensamiento
cadena = pensamiento.generar_pensamiento(semilla="creatividad", longitud=5)
print(cadena)
```

### Ejemplo 4: Ejecutar ciclo de vida autónomo

```python
from nucleo import ConceptosDifusos

# Crear y configurar sistema
sistema = ConceptosDifusos(dim_vector=15)
# Añadir conceptos iniciales...

# Ejecutar ciclo de vida
sistema.ciclo_vital(num_ciclos=20, visualizar_cada=5)

# Guardar estado
sistema.guardar("mi_sistema_evolucionado.json")
```

## Experimentación Avanzada

### Modificar Parámetros de Incertidumbre

El parámetro `incertidumbre_base` controla el nivel de aleatoriedad inherente en los conceptos. Valores más altos (0.3-0.5) fomentan la creatividad y exploración, mientras que valores más bajos (0.1-0.2) producen comportamientos más estables.

### Ajustar la Temperatura

El parámetro `temperatura` en la función `activar()` controla la aleatoriedad en la propagación de activación. Valores más altos producen resultados más variados y explorativos.

### Dimensionalidad de Conceptos

La dimensionalidad de los vectores conceptuales (`dim_vector`) afecta la expresividad del sistema:
- Dimensiones bajas (5-10): Asociaciones más fuertes pero menos matizadas
- Dimensiones medias (15-30): Buen equilibrio para la mayoría de experimentos
- Dimensiones altas (50+): Mayor expresividad pero menor generalización

## Limitaciones y Consideraciones

- **Rendimiento**: Con muchos conceptos (>1000), el sistema puede volverse lento debido a la representación vectorial y visualización.
- **Interpretabilidad**: Las representaciones vectoriales de conceptos son difíciles de interpretar directamente.
- **Estabilidad**: El sistema puede mostrar comportamientos caóticos con ciertos parámetros.

## Próximos Pasos

El proyecto IANAE está en desarrollo continuo. Algunas direcciones futuras incluyen:

1. **Integración multimodal**: Permitir que los conceptos se vinculen con imágenes, sonidos u otras modalidades.
2. **Mecanismos de atención**: Implementar sistemas que dirijan selectivamente los recursos cognitivos.
3. **Intencionalidad y metas**: Añadir estructuras que permitan comportamientos dirigidos a objetivos.
4. **Memoria episódica**: Implementar un sistema para recordar secuencias de activaciones pasadas.
5. **Interfaz de lenguaje natural**: Mejorar la interpretación y generación de lenguaje para comunicación más fluida.

## Contribución

Este proyecto es una exploración experimental y toda contribución es bienvenida. Si deseas contribuir:

1. Explora el código y familiarízate con los conceptos fundamentales.
2. Identifica áreas que te interesen para mejorar o expandir.
3. Experimenta con parámetros y funcionalidades.
4. Comparte tus ideas y resultados.

## Licencia

Este proyecto se distribuye bajo licencia MIT. Siéntete libre de usarlo, modificarlo y distribuirlo respetando los términos de la licencia.

---

**IANAE: Repensando la inteligencia desde los fundamentos**
