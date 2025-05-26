# Arquitectura IANAE - Documentación Técnica

## 1. Visión General del Sistema

IANAE (Inteligencia Adaptativa No Algorítmica Emergente) es un sistema experimental que explora un nuevo paradigma de inteligencia artificial basado en conceptos difusos, relaciones probabilísticas y comportamientos emergentes, en contraste con los enfoques algorítmicos tradicionales.

Este documento describe la arquitectura técnica del sistema, sus componentes principales, los flujos de trabajo y los principios de diseño que lo sustentan.

## 2. Diagrama de Componentes

```
+------------------+       +------------------+
|     nucleo.py    |<------|   emergente.py   |
| ConceptosDifusos |       | PensamientoEmer. |
+------------------+       +------------------+
        ^                         ^
        |                         |
        |                         |
        v                         v
+------------------+       +------------------+
|     main.py      |------>|  experimento.py  |
| Interfaz Usuario |       | Demostraciones   |
+------------------+       +------------------+
```

### Descripción de Componentes

#### 2.1 nucleo.py - El Núcleo Cognitivo

**Propósito**: Implementa la estructura fundamental del sistema: conceptos difusos y sus relaciones.

**Responsabilidades**:
- Gestionar la representación vectorial de conceptos
- Implementar el mecanismo de relaciones probabilísticas
- Proporcionar funcionalidad de propagación de activación
- Manejar la auto-modificación del sistema
- Gestionar la creación y evolución de conceptos
- Visualizar la red conceptual
- Guardar/cargar el estado del sistema

**Clase Principal**: `ConceptosDifusos`

#### 2.2 emergente.py - Pensamiento Emergente

**Propósito**: Extiende el núcleo cognitivo con capacidades de pensamiento de nivel superior.

**Responsabilidades**:
- Proporcionar interfaz para extraer conceptos de texto
- Implementar exploración de asociaciones conceptuales
- Generar cadenas de pensamiento coherentes
- Facilitar la asociación entre conceptos distantes
- Visualizar procesos de pensamiento
- Ejecutar experimentos de divergencia creativa

**Clase Principal**: `PensamientoEmergente`

#### 2.3 main.py - Interfaz Interactiva

**Propósito**: Proporciona una interfaz de usuario para interactuar con el sistema.

**Responsabilidades**:
- Presentar menú de opciones para el usuario
- Facilitar la creación y manipulación de sistemas IANAE
- Permitir la visualización de estados y métricas
- Gestionar la persistencia (guardar/cargar)
- Proporcionar retroalimentación al usuario

**Función Principal**: `main()`

#### 2.4 experimento.py - Demostraciones

**Propósito**: Implementa experimentos que demuestran las capacidades del sistema.

**Responsabilidades**:
- Ejecutar flujos de trabajo predefinidos
- Mostrar capacidades del sistema paso a paso
- Proporcionar ejemplos de uso para usuarios nuevos
- Servir como referencia para implementaciones personalizadas

**Función Principal**: `ejecutar_experimento()`

## 3. Flujos de Trabajo y Ciclos de Vida

### 3.1 Ciclo de Vida de un Concepto

```
Creación           Activación          Auto-modificación       Posible
del Concepto  -->  y Propagación  -->  de Conexiones     -->  Desvanecimiento
(añadir_concepto)  (activar)           (auto_modificar)        (debilitamiento)
```

1. **Creación**: Un concepto se crea con un vector base y un componente de incertidumbre
2. **Activación**: El concepto se activa, propagando esta activación a través de sus conexiones
3. **Auto-modificación**: Las conexiones se fortalecen o debilitan según patrones de activación
4. **Evolución**: Con el tiempo, algunos conceptos ganan prominencia mientras otros pueden desvanecerse

### 3.2 Ciclo de Vida del Sistema

```
   +--------------------------------+
   |                                |
   v                                |
Inicialización --> Activación --> Auto-modificación --> Generación de
(crear sistema)    (activar)      (auto_modificar)     Conceptos Nuevos
                                                        (generar_concepto)
```

1. **Inicialización**: Se crea el sistema con conceptos semilla
2. **Ciclo de Vida Continuo**:
   - Activación de conceptos (dirigida por el usuario o automática)
   - Auto-modificación de conexiones basada en patrones de activación
   - Generación ocasional de nuevos conceptos
   - Estas fases se repiten, permitiendo que el sistema evolucione

### 3.3 Flujo de Trabajo de Pensamiento Emergente

```
Entrada de         Exploración de       Generación de
Conceptos     -->  Asociaciones    -->  Pensamiento   --> Visualización
(texto/manual)     (exploraciones)      (cadenas)
```

1. **Entrada**: Los conceptos entran al sistema (manualmente o desde texto)
2. **Exploración**: Se exploran asociaciones entre conceptos existentes
3. **Generación**: Se producen cadenas de pensamiento como secuencias coherentes de conceptos
4. **Visualización**: Se visualizan y analizan los resultados

### 3.4 Ciclo de Experimentación

```
Creación de       Ejecución de         Análisis de         Ajuste de
Sistema Base -->  Experimentos    -->  Resultados     -->  Parámetros
                  (divergencia,        (visualización)     (temperatura,
                   asociaciones)                            dimensionalidad)
```

1. **Configuración**: Se configura un sistema base con conceptos y relaciones iniciales
2. **Experimentación**: Se ejecutan diversos experimentos (divergencia, asociaciones, etc.)
3. **Análisis**: Se analizan los resultados mediante visualización y métricas
4. **Refinamiento**: Se ajustan parámetros para mejorar los resultados

## 4. Principios de Diseño y Patrones

### 4.1 Principios Fundamentales

#### 4.1.1 Incertidumbre Inherente
IANAE está diseñado bajo el principio de que la incertidumbre no es un error a minimizar, sino una característica esencial de la inteligencia. Esto se refleja en:
- La representación de conceptos como vectores con componentes aleatorios
- La propagación estocástica de activación
- El uso de factores de temperatura para controlar la aleatoriedad

#### 4.1.2 Emergencia sobre Determinismo
El sistema favorece propiedades emergentes sobre reglas explícitas:
- No hay reglas predefinidas sobre cómo deben relacionarse los conceptos
- Las estructuras conceptuales surgen de interacciones locales simples
- Los patrones globales no están programados, sino que emergen naturalmente

#### 4.1.3 Auto-modificación
IANAE puede alterar sus propias estructuras:
- Las conexiones se refuerzan o debilitan basándose en la experiencia
- Nuevos conceptos pueden generarse combinando los existentes
- El sistema evoluciona sin intervención externa directa

#### 4.1.4 Representación Vectorial Difusa
Los conceptos no son unidades discretas sino espacios vectoriales continuos:
- Permite representar matices y similitudes parciales
- Facilita la combinación y transformación de conceptos
- Permite calcular distancias y similitudes de manera natural

### 4.2 Patrones de Diseño Utilizados

#### 4.2.1 Composición sobre Herencia
El sistema utiliza composición para extender funcionalidades:
- `PensamientoEmergente` contiene una instancia de `ConceptosDifusos`
- Las nuevas capacidades se construyen sobre la funcionalidad existente

#### 4.2.2 Inmutabilidad Parcial
Algunos aspectos del sistema son inmutables después de la creación:
- La dimensionalidad de los vectores conceptuales
- Los vectores base de los conceptos (aunque su manifestación 'actual' varía)

#### 4.2.3 Persistencia y Serialización
El sistema implementa mecanismos para guardar y restaurar su estado:
- Serialización a formato JSON para almacenamiento
- Capacidad de reconstruir el sistema completo desde un archivo guardado

#### 4.2.4 Visualización Integrada
La visualización no es un componente separado sino parte integral del sistema:
- Métodos de visualización incorporados en las clases principales
- Retroalimentación visual durante la experimentación

## 5. Interacción entre Componentes

### 5.1 Flujo de Datos Principal

```
Usuario ---> main.py ---> nucleo.py <---> emergente.py
                |            |              |
                v            v              v
             Salida      Visualización   Experimentos
             Consola                    
```

- El usuario interactúa principalmente a través de `main.py`
- `main.py` crea y manipula instancias de `ConceptosDifusos`
- `emergente.py` extiende la funcionalidad básica de `nucleo.py`
- Los resultados se muestran mediante visualizaciones y salida de consola

### 5.2 Dependencias de Componentes

- `nucleo.py` no tiene dependencias de otros módulos IANAE
- `emergente.py` depende de `nucleo.py`
- `main.py` depende de `nucleo.py` pero no de `emergente.py`
- `experimento.py` depende tanto de `nucleo.py` como de `emergente.py`

Esta estructura minimiza el acoplamiento y permite que cada componente evolucione de manera relativamente independiente.

## 6. Decisiones de Implementación Clave

### 6.1 Representación de Conceptos

Los conceptos se representan como vectores multidimensionales en lugar de símbolos discretos, lo que permite:
- Capturar similitudes parciales entre conceptos
- Implementar operaciones como combinación y transformación
- Introducir incertidumbre de manera natural

### 6.2 Propagación de Activación

La propagación de activación utiliza un enfoque estocástico:
- La activación se propaga según la fuerza de las conexiones
- Se añade ruido controlado por un parámetro de temperatura
- Se aplica normalización para mantener niveles de activación manejables

### 6.3 Auto-modificación

El sistema puede modificar sus propias estructuras mediante:
- Reforzamiento de conexiones entre conceptos activados simultáneamente
- Debilitamiento de conexiones poco utilizadas
- Generación de nuevos conceptos combinando los existentes

### 6.4 Visualización

El sistema prioriza la visualización como herramienta de comprensión:
- Representación gráfica de la red conceptual
- Codificación de color para representar activación y otras propiedades
- Filtrado inteligente para manejar redes grandes

## 7. Limitaciones Actuales y Áreas de Mejora

### 7.1 Escalabilidad

El sistema actual tiene limitaciones de escalabilidad:
- La representación en memoria limita el número de conceptos (~1000)
- La visualización se vuelve menos útil con redes muy grandes
- La serialización a JSON no es óptima para sistemas grandes

### 7.2 Integración con NLP

La extracción de conceptos desde texto es básica:
- Utiliza técnicas simples de tokenización y filtrado
- No aprovecha técnicas modernas de embeddings
- Carece de detección avanzada de relaciones semánticas

### 7.3 Persistencia

El almacenamiento actual es simple pero limitado:
- Serialización a JSON sin estructura optimizada
- No hay soporte para consultas complejas
- Falta indexación para acceso eficiente

Estas limitaciones constituyen las principales áreas de mejora planificadas en el roadmap.
