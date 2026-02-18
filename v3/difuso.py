"""
Ianae v3 - Motor de Inferencia Difusa
=======================================
Aqui es donde Ianae deja de tirar dados y empieza a "decidir".

En vez de: "20% de probabilidad de generar idea" (arbitrario)
Ahora:     "SI activacion ES alta Y novedad ES alta ENTONCES generar_idea ES muy_probable"

Las decisiones de Ianae (explorar, olvidar, conectar, crear, sonar)
emergen de reglas difusas que operan sobre el estado real de sus conceptos.

Funciones de pertenencia: trapezoidal y triangular
Inferencia: Mamdani (min para AND, max para OR, centroide para defuzzificar)
"""

import math


# ══════════════════════════════════════════════
#  FUNCIONES DE PERTENENCIA
# ══════════════════════════════════════════════

def triangular(x, a, b, c):
    """Funcion de pertenencia triangular.
    a = inicio, b = pico, c = fin. Devuelve grado [0,1]."""
    if x <= a or x >= c:
        return 0.0
    if x <= b:
        return (x - a) / (b - a) if b != a else 1.0
    return (c - x) / (c - b) if c != b else 1.0


def trapezoidal(x, a, b, c, d):
    """Funcion de pertenencia trapezoidal.
    a = inicio subida, b = inicio meseta, c = fin meseta, d = fin bajada."""
    if x <= a or x >= d:
        return 0.0
    if a < x <= b:
        return (x - a) / (b - a) if b != a else 1.0
    if b < x <= c:
        return 1.0
    return (d - x) / (d - c) if d != c else 1.0


# ══════════════════════════════════════════════
#  VARIABLES DIFUSAS
# ══════════════════════════════════════════════
#  Cada variable tiene conjuntos difusos (etiquetas)
#  definidos como funciones de pertenencia sobre [0, 1]

class VariableDifusa:
    """Una variable linguistica con sus conjuntos difusos."""

    def __init__(self, nombre, conjuntos):
        """
        nombre: str
        conjuntos: dict de {etiqueta: funcion(x) -> grado}
        """
        self.nombre = nombre
        self.conjuntos = conjuntos

    def fuzzificar(self, valor):
        """Dado un valor crisp, devuelve los grados de pertenencia a cada conjunto."""
        return {etiqueta: fn(valor) for etiqueta, fn in self.conjuntos.items()}

    def __repr__(self):
        return f"<VarDifusa: {self.nombre} [{', '.join(self.conjuntos.keys())}]>"


# ── Variables de entrada ──

ACTIVACION = VariableDifusa("activacion", {
    "baja":     lambda x: trapezoidal(x, 0.0, 0.0, 0.15, 0.3),
    "media":    lambda x: triangular(x, 0.15, 0.4, 0.65),
    "alta":     lambda x: trapezoidal(x, 0.5, 0.7, 1.0, 1.0),
})

NOVEDAD = VariableDifusa("novedad", {
    "vieja":    lambda x: trapezoidal(x, 0.0, 0.0, 0.2, 0.4),
    "reciente": lambda x: triangular(x, 0.2, 0.5, 0.8),
    "nueva":    lambda x: trapezoidal(x, 0.6, 0.8, 1.0, 1.0),
})

FUERZA = VariableDifusa("fuerza", {
    "debil":    lambda x: trapezoidal(x, 0.0, 0.0, 0.2, 0.4),
    "moderada": lambda x: triangular(x, 0.2, 0.5, 0.8),
    "fuerte":   lambda x: trapezoidal(x, 0.6, 0.8, 1.0, 1.0),
})

CURIOSIDAD = VariableDifusa("curiosidad", {
    "baja":     lambda x: trapezoidal(x, 0.0, 0.0, 0.2, 0.4),
    "media":    lambda x: triangular(x, 0.2, 0.5, 0.8),
    "alta":     lambda x: trapezoidal(x, 0.6, 0.8, 1.0, 1.0),
})

DENSIDAD_RED = VariableDifusa("densidad_red", {
    "dispersa": lambda x: trapezoidal(x, 0.0, 0.0, 0.2, 0.4),
    "normal":   lambda x: triangular(x, 0.2, 0.5, 0.8),
    "densa":    lambda x: trapezoidal(x, 0.6, 0.8, 1.0, 1.0),
})

# ── Variables de salida ──

EXPLORAR = VariableDifusa("explorar", {
    "poco":     lambda x: trapezoidal(x, 0.0, 0.0, 0.2, 0.4),
    "algo":     lambda x: triangular(x, 0.2, 0.5, 0.8),
    "mucho":    lambda x: trapezoidal(x, 0.6, 0.8, 1.0, 1.0),
})

GENERAR = VariableDifusa("generar_idea", {
    "improbable":   lambda x: trapezoidal(x, 0.0, 0.0, 0.15, 0.35),
    "posible":      lambda x: triangular(x, 0.2, 0.5, 0.8),
    "probable":     lambda x: trapezoidal(x, 0.65, 0.85, 1.0, 1.0),
})

OLVIDAR = VariableDifusa("olvidar", {
    "conservar":    lambda x: trapezoidal(x, 0.0, 0.0, 0.2, 0.4),
    "quiza":        lambda x: triangular(x, 0.2, 0.5, 0.8),
    "olvidar":      lambda x: trapezoidal(x, 0.6, 0.8, 1.0, 1.0),
})

SONAR = VariableDifusa("sonar", {
    "no":       lambda x: trapezoidal(x, 0.0, 0.0, 0.25, 0.45),
    "quiza":    lambda x: triangular(x, 0.3, 0.5, 0.7),
    "si":       lambda x: trapezoidal(x, 0.55, 0.75, 1.0, 1.0),
})

CONECTAR = VariableDifusa("conectar", {
    "debil":    lambda x: trapezoidal(x, 0.0, 0.0, 0.2, 0.4),
    "media":    lambda x: triangular(x, 0.2, 0.5, 0.8),
    "fuerte":   lambda x: trapezoidal(x, 0.6, 0.8, 1.0, 1.0),
})


# ══════════════════════════════════════════════
#  REGLAS DIFUSAS
# ══════════════════════════════════════════════

class Regla:
    """Una regla IF-THEN difusa."""

    def __init__(self, antecedentes, consecuente_var, consecuente_etiqueta, peso=1.0):
        """
        antecedentes: list de (variable, etiqueta) -> AND entre todos
        consecuente_var: str (nombre de variable de salida)
        consecuente_etiqueta: str
        peso: importancia relativa de la regla [0,1]
        """
        self.antecedentes = antecedentes
        self.consecuente_var = consecuente_var
        self.consecuente_etiqueta = consecuente_etiqueta
        self.peso = peso

    def evaluar(self, valores_fuzz):
        """Evalua la regla con los valores fuzzificados.
        valores_fuzz: {nombre_var: {etiqueta: grado}}
        Devuelve: grado de disparo (min de antecedentes * peso)."""
        grados = []
        for var_nombre, etiqueta in self.antecedentes:
            grado = valores_fuzz.get(var_nombre, {}).get(etiqueta, 0.0)
            grados.append(grado)

        if not grados:
            return 0.0

        # AND = min (Mamdani)
        return min(grados) * self.peso


# ── Base de reglas de Ianae ──

REGLAS = [
    # === EXPLORAR ===
    # Si activacion alta y novedad nueva -> explorar mucho
    Regla([("activacion", "alta"), ("novedad", "nueva")], "explorar", "mucho"),
    # Si activacion media y curiosidad alta -> explorar algo
    Regla([("activacion", "media"), ("curiosidad", "alta")], "explorar", "algo"),
    # Si activacion baja y novedad vieja -> explorar poco
    Regla([("activacion", "baja"), ("novedad", "vieja")], "explorar", "poco"),
    # Si curiosidad alta y red dispersa -> explorar mucho
    Regla([("curiosidad", "alta"), ("densidad_red", "dispersa")], "explorar", "mucho"),

    # === GENERAR IDEAS ===
    # Si activacion alta y curiosidad alta -> generar probable
    Regla([("activacion", "alta"), ("curiosidad", "alta")], "generar_idea", "probable"),
    # Si activacion alta y novedad nueva -> generar posible
    Regla([("activacion", "alta"), ("novedad", "nueva")], "generar_idea", "posible"),
    # Si activacion baja -> generar improbable
    Regla([("activacion", "baja")], "generar_idea", "improbable"),
    # Si fuerza fuerte y curiosidad alta -> generar probable
    Regla([("fuerza", "fuerte"), ("curiosidad", "alta")], "generar_idea", "probable"),
    # Si red densa y curiosidad media -> generar posible (tiene material)
    Regla([("densidad_red", "densa"), ("curiosidad", "media")], "generar_idea", "posible"),

    # === OLVIDAR ===
    # Si fuerza debil y novedad vieja -> olvidar
    Regla([("fuerza", "debil"), ("novedad", "vieja")], "olvidar", "olvidar"),
    # Si fuerza debil y activacion baja -> olvidar quiza
    Regla([("fuerza", "debil"), ("activacion", "baja")], "olvidar", "quiza"),
    # Si fuerza fuerte -> conservar
    Regla([("fuerza", "fuerte")], "olvidar", "conservar"),
    # Si fuerza moderada y novedad reciente -> conservar
    Regla([("fuerza", "moderada"), ("novedad", "reciente")], "olvidar", "conservar"),

    # === SONAR ===
    # Si red densa y activacion media -> sonar quiza
    Regla([("densidad_red", "densa"), ("activacion", "media")], "sonar", "quiza"),
    # Si curiosidad alta y novedad vieja -> sonar si (reprocessar memorias)
    Regla([("curiosidad", "alta"), ("novedad", "vieja")], "sonar", "si"),
    # Si activacion baja y fuerza moderada -> sonar quiza
    Regla([("activacion", "baja"), ("fuerza", "moderada")], "sonar", "quiza"),
    # Si activacion alta -> no sonar (ya esta activa, no necesita sonar)
    Regla([("activacion", "alta")], "sonar", "no"),

    # === CONECTAR ===
    # Si activacion alta y novedad nueva -> conexion fuerte
    Regla([("activacion", "alta"), ("novedad", "nueva")], "conectar", "fuerte"),
    # Si fuerza fuerte y curiosidad alta -> conexion fuerte
    Regla([("fuerza", "fuerte"), ("curiosidad", "alta")], "conectar", "fuerte"),
    # Si activacion media -> conexion media
    Regla([("activacion", "media")], "conectar", "media"),
    # Si activacion baja y fuerza debil -> conexion debil
    Regla([("activacion", "baja"), ("fuerza", "debil")], "conectar", "debil"),
]


# ══════════════════════════════════════════════
#  MOTOR DE INFERENCIA
# ══════════════════════════════════════════════

def defuzzificar_centroide(activaciones_salida, variable):
    """Defuzzificacion por centroide (centro de gravedad).
    activaciones_salida: {etiqueta: grado_disparo}
    variable: VariableDifusa de salida
    Devuelve: valor crisp [0, 1]"""
    n_puntos = 101
    xs = [i / (n_puntos - 1) for i in range(n_puntos)]

    numerador = 0.0
    denominador = 0.0

    for x in xs:
        # Para cada punto, calcular el maximo de las funciones recortadas
        grado_max = 0.0
        for etiqueta, disparo in activaciones_salida.items():
            if disparo <= 0:
                continue
            # Recortar la funcion de pertenencia al grado de disparo
            mu = variable.conjuntos[etiqueta](x)
            recortado = min(mu, disparo)
            grado_max = max(grado_max, recortado)

        numerador += x * grado_max
        denominador += grado_max

    if denominador == 0:
        return 0.5  # neutro si no hay informacion
    return numerador / denominador


class MotorDifuso:
    """Motor de inferencia difusa de Ianae.
    Toma el estado de la mente y produce decisiones difusas."""

    def __init__(self, reglas=None):
        self.reglas = reglas or REGLAS
        self.variables_entrada = {
            "activacion": ACTIVACION,
            "novedad": NOVEDAD,
            "fuerza": FUERZA,
            "curiosidad": CURIOSIDAD,
            "densidad_red": DENSIDAD_RED,
        }
        self.variables_salida = {
            "explorar": EXPLORAR,
            "generar_idea": GENERAR,
            "olvidar": OLVIDAR,
            "sonar": SONAR,
            "conectar": CONECTAR,
        }

    def inferir(self, entradas):
        """Ejecuta la inferencia difusa completa.

        entradas: dict de {nombre_var: valor_crisp [0,1]}
            Ejemplo: {"activacion": 0.7, "novedad": 0.9, "fuerza": 0.5,
                       "curiosidad": 0.8, "densidad_red": 0.4}

        Devuelve: dict de {nombre_var_salida: valor_crisp [0,1]}
            Ejemplo: {"explorar": 0.82, "generar_idea": 0.71, "olvidar": 0.12,
                       "sonar": 0.3, "conectar": 0.75}
        """
        # 1. Fuzzificar entradas
        valores_fuzz = {}
        for nombre, variable in self.variables_entrada.items():
            valor = entradas.get(nombre, 0.5)
            valor = max(0.0, min(1.0, valor))
            valores_fuzz[nombre] = variable.fuzzificar(valor)

        # 2. Evaluar reglas
        activaciones_salida = {nombre: {} for nombre in self.variables_salida}

        for regla in self.reglas:
            disparo = regla.evaluar(valores_fuzz)
            if disparo > 0:
                var_salida = regla.consecuente_var
                etiqueta = regla.consecuente_etiqueta
                # MAX para OR (agregacion)
                actual = activaciones_salida[var_salida].get(etiqueta, 0.0)
                activaciones_salida[var_salida][etiqueta] = max(actual, disparo)

        # 3. Defuzzificar
        resultados = {}
        for nombre, variable in self.variables_salida.items():
            if activaciones_salida[nombre]:
                resultados[nombre] = defuzzificar_centroide(
                    activaciones_salida[nombre], variable
                )
            else:
                resultados[nombre] = 0.5  # neutro

        return resultados

    def decidir_concepto(self, concepto, mente):
        """Genera decisiones difusas para un concepto especifico.

        Calcula las variables de entrada a partir del estado real del concepto
        y de la mente, y produce decisiones.
        """
        import time as _time

        # Calcular variables de entrada
        horas_vida = concepto.edad_horas()
        horas_sin_uso = (_time.time() - concepto.ultimo_acceso) / 3600

        # Activacion: basada en accesos recientes
        activacion = min(1.0, concepto.accesos / max(1, horas_vida + 1) * 0.3)

        # Novedad: inversamente proporcional a la edad
        novedad = 1.0 / (1.0 + horas_vida * 0.5)

        # Fuerza: directa
        fuerza = concepto.fuerza

        # Curiosidad: directa
        curiosidad = concepto.curiosidad

        # Densidad de la red: cuantas conexiones tiene relativo al total
        n_conceptos = max(1, len(mente.conceptos))
        n_conexiones = len(mente.conexiones.get(concepto.nombre, {}))
        densidad = min(1.0, n_conexiones / max(1, n_conceptos * 0.3))

        entradas = {
            "activacion": activacion,
            "novedad": novedad,
            "fuerza": fuerza,
            "curiosidad": curiosidad,
            "densidad_red": densidad,
        }

        return self.inferir(entradas), entradas

    def decidir_ciclo(self, mente):
        """Decisiones globales para el ciclo actual.
        Agrega las decisiones de los conceptos mas activos."""
        if not mente.conceptos:
            return {
                "explorar": 0.8,
                "generar_idea": 0.2,
                "olvidar": 0.1,
                "sonar": 0.1,
                "conectar": 0.5,
            }

        # Tomar los 10 conceptos mas interesantes
        vivos = sorted(
            mente.conceptos.values(),
            key=lambda c: c.interes(),
            reverse=True,
        )[:10]

        # Promediar sus decisiones
        acumulado = {}
        for concepto in vivos:
            decisiones, _ = self.decidir_concepto(concepto, mente)
            for k, v in decisiones.items():
                acumulado[k] = acumulado.get(k, 0) + v

        n = len(vivos)
        return {k: v / n for k, v in acumulado.items()}


# ══════════════════════════════════════════════
#  INSTANCIA GLOBAL
# ══════════════════════════════════════════════

motor = MotorDifuso()
