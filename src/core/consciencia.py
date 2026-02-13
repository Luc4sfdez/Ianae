"""
Consciencia de IANAE — Fase 5: IANAE se Conoce a Si Misma.

Compone VidaAutonoma y le agrega auto-consciencia a traves de muchas
fuerzas simultaneas (como el agua que se evapora por capilaridad,
corrientes, porosidad, luz solar):

  - Meta-analisis: lee su propio diario, detecta patrones en sus ciclos
  - Narrativa: genera texto legible de lo que descubre y por que
  - Objetivos: define metas de conocimiento y mide progreso
  - Fuerzas: pulso, capilaridad, corrientes, superficie — emergencia pura
"""
import json
import logging
import os
import time
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ESTADOS_PULSO = {
    "inspirada": "Muchos descubrimientos reveladores, energia alta",
    "curiosa": "Mezcla de resultados, buscando algo nuevo",
    "aburrida": "Demasiados resultados rutinarios, necesita estimulo",
    "enfocada": "Racha de resultados interesantes, en zona productiva",
}


class Consciencia:
    """Capa de auto-consciencia que compone VidaAutonoma."""

    def __init__(
        self,
        vida_autonoma,
        objetivos_path: str = "data/objetivos_ianae.json",
    ):
        self.vida = vida_autonoma
        self.objetivos_path = objetivos_path
        self._objetivos: List[Dict] = []
        self._cargar_objetivos()

    # ==================================================================
    # META-ANALISIS — lee su propio diario
    # ==================================================================

    def analizar_patrones_propios(self, ultimos: int = 50) -> Dict[str, Any]:
        """Analiza el diario para detectar patrones en su propio comportamiento."""
        entradas = self.vida.leer_diario(ultimos=ultimos)
        if not entradas:
            return {
                "tipos_frecuencia": {},
                "conceptos_frecuencia": {},
                "gaps_repetidos": [],
                "veredictos_distribucion": {},
                "ciclos_analizados": 0,
            }

        tipos = Counter()
        conceptos = Counter()
        gaps = Counter()
        veredictos = Counter()

        for e in entradas:
            cur = e.get("curiosidad", {})
            tipos[cur.get("tipo", "desconocido")] += 1
            conceptos[cur.get("concepto", "desconocido")] += 1
            if cur.get("tipo") == "gap":
                gaps[cur.get("concepto", "")] += 1
            ref = e.get("reflexion", {})
            veredictos[ref.get("veredicto", "desconocido")] += 1

        total = len(entradas)
        return {
            "tipos_frecuencia": {k: round(v / total, 3) for k, v in tipos.items()},
            "conceptos_frecuencia": dict(conceptos.most_common(10)),
            "gaps_repetidos": [g for g, cnt in gaps.items() if cnt >= 2 and g],
            "veredictos_distribucion": {k: round(v / total, 3) for k, v in veredictos.items()},
            "ciclos_analizados": total,
        }

    def detectar_sesgos(self) -> List[Dict[str, Any]]:
        """Detecta si esta sobreexplorando ciertos tipos o conceptos."""
        patrones = self.analizar_patrones_propios()
        sesgos: List[Dict[str, Any]] = []

        if patrones["ciclos_analizados"] < 3:
            return sesgos

        # Sesgo de tipo: un tipo domina >40%
        for tipo, freq in patrones["tipos_frecuencia"].items():
            if freq > 0.4:
                sesgos.append({
                    "tipo": "tipo_dominante",
                    "descripcion": f"Curiosidad '{tipo}' domina con {freq:.0%}",
                    "severidad": min(1.0, (freq - 0.4) * 5),
                    "fuente": tipo,
                })

        # Sesgo de concepto: un concepto explorado >3x el promedio
        freqs = patrones["conceptos_frecuencia"]
        if freqs:
            promedio = sum(freqs.values()) / len(freqs)
            for concepto, cnt in freqs.items():
                if promedio > 0 and cnt > promedio * 3:
                    sesgos.append({
                        "tipo": "concepto_dominante",
                        "descripcion": f"'{concepto}' explorado {cnt}x (promedio={promedio:.1f})",
                        "severidad": min(1.0, (cnt / promedio - 3) * 0.3),
                        "fuente": concepto,
                    })

        # Sesgo de veredicto: demasiados rutinarios (>60%)
        rut = patrones["veredictos_distribucion"].get("rutinario", 0)
        if rut > 0.6:
            sesgos.append({
                "tipo": "estancamiento",
                "descripcion": f"{rut:.0%} de ciclos rutinarios — posible estancamiento",
                "severidad": min(1.0, (rut - 0.6) * 5),
                "fuente": "rutinario",
            })

        return sesgos

    def medir_crecimiento(self, ventana: int = 20) -> Dict[str, Any]:
        """Compara ciclos recientes vs anteriores para medir crecimiento."""
        entradas = self.vida.leer_diario(ultimos=ventana * 2)

        if len(entradas) < 4:
            return {
                "score_promedio_reciente": 0.0,
                "score_promedio_anterior": 0.0,
                "tendencia": "insuficiente",
                "novedad_promedio": 0.0,
            }

        mitad = len(entradas) // 2
        anteriores = entradas[:mitad]
        recientes = entradas[mitad:]

        def _promedio_score(lst):
            scores = [e.get("reflexion", {}).get("score", 0) for e in lst]
            return sum(scores) / len(scores) if scores else 0.0

        def _promedio_novedad(lst):
            novedades = [e.get("descubrimientos", {}).get("conexiones_nuevas", 0) for e in lst]
            return sum(novedades) / len(novedades) if novedades else 0.0

        score_rec = round(_promedio_score(recientes), 4)
        score_ant = round(_promedio_score(anteriores), 4)
        delta = score_rec - score_ant

        if delta > 0.05:
            tendencia = "creciendo"
        elif delta < -0.05:
            tendencia = "decayendo"
        else:
            tendencia = "estable"

        return {
            "score_promedio_reciente": score_rec,
            "score_promedio_anterior": score_ant,
            "tendencia": tendencia,
            "novedad_promedio": round(_promedio_novedad(recientes), 4),
        }

    # ==================================================================
    # NARRATIVA — comunica lo que descubre
    # ==================================================================

    def narrar_ciclo(self, entrada_diario: Dict[str, Any]) -> str:
        """Genera narrativa legible de un ciclo del diario."""
        ciclo = entrada_diario.get("ciclo", "?")
        cur = entrada_diario.get("curiosidad", {})
        tipo = cur.get("tipo", "exploracion")
        concepto = cur.get("concepto", "algo")
        motivacion = cur.get("motivacion", "")

        desc = entrada_diario.get("descubrimientos", {})
        conexiones = desc.get("conexiones_nuevas", 0)
        coherencia = desc.get("coherencia", 0.0)

        ref = entrada_diario.get("reflexion", {})
        veredicto = ref.get("veredicto", "rutinario")
        score = ref.get("score", 0.0)

        partes = [
            f"Ciclo {ciclo}: IANAE exploro '{concepto}' por {tipo}",
        ]
        if motivacion:
            partes[0] += f" ({motivacion})"
        partes[0] += "."

        if conexiones > 0:
            partes.append(
                f"Descubrio {conexiones} conexion{'es' if conexiones > 1 else ''} "
                f"nueva{'s' if conexiones > 1 else ''} con coherencia {coherencia:.2f}."
            )
        else:
            partes.append(f"Coherencia de {coherencia:.2f}, sin conexiones nuevas.")

        partes.append(f"Resultado: {veredicto} (score {score:.2f}).")

        return " ".join(partes)

    def narrar_estado(self) -> str:
        """Narrativa del estado general de IANAE."""
        patrones = self.analizar_patrones_propios()
        crecimiento = self.medir_crecimiento()
        sesgos = self.detectar_sesgos()
        p = self.pulso()

        ciclos = patrones["ciclos_analizados"]
        if ciclos == 0:
            return "IANAE aun no ha iniciado su ciclo de vida. Sin datos para narrar."

        # Tipo mas frecuente
        tipos = patrones["tipos_frecuencia"]
        tipo_dom = max(tipos, key=tipos.get) if tipos else "ninguno"
        tipo_pct = tipos.get(tipo_dom, 0)

        # Veredictos
        verd = patrones["veredictos_distribucion"]
        reveladores = verd.get("revelador", 0)

        partes = [
            f"Despues de {ciclos} ciclos, IANAE se siente {p['estado']}.",
            f"Su curiosidad dominante es '{tipo_dom}' ({tipo_pct:.0%}).",
            f"Ha tenido {reveladores:.0%} de revelaciones.",
        ]

        # Tendencia
        tend = crecimiento["tendencia"]
        if tend == "creciendo":
            partes.append("Su crecimiento es positivo — esta aprendiendo.")
        elif tend == "decayendo":
            partes.append("Su crecimiento decae — necesita estimulos nuevos.")
        elif tend == "estable":
            partes.append("Su crecimiento es estable.")

        # Sesgos
        if sesgos:
            nombres = [s["descripcion"] for s in sesgos[:2]]
            partes.append("Detecta sesgos: " + "; ".join(nombres) + ".")

        # Objetivos
        pendientes = [o for o in self._objetivos if o.get("progreso", 0) < 1.0]
        if pendientes:
            partes.append(f"Tiene {len(pendientes)} objetivo(s) pendiente(s).")

        return " ".join(partes)

    def explicar_insight(self, tipo: str, concepto: str, datos: Optional[Dict] = None) -> str:
        """Explica POR QUE algo es interesante."""
        datos = datos or {}
        explicaciones = {
            "gap": (
                f"'{concepto}' pertenece a un area con deficit de conocimiento. "
                f"Fortalecer este concepto ayudaria a equilibrar el grafo."
            ),
            "revitalizar": (
                f"'{concepto}' ha perdido activacion con el tiempo. "
                f"Reconectarlo podria despertar conocimiento dormido."
            ),
            "puente": (
                f"'{concepto}' conecta comunidades distintas del grafo "
                f"(centralidad {datos.get('centralidad', '?'):.2f}). "
                f"Es un nodo clave para el flujo de ideas."
            ) if isinstance(datos.get("centralidad"), (int, float)) else (
                f"'{concepto}' conecta comunidades distintas del grafo. "
                f"Es un nodo clave para el flujo de ideas."
            ),
            "prediccion": (
                f"'{concepto}' tiene potencial no explorado. "
                f"Podria convertirse en un nodo importante si se le da atencion."
            ),
            "serendipia": (
                f"'{concepto}' fue elegido al azar — a veces la exploracion "
                f"aleatoria produce los descubrimientos mas sorprendentes."
            ),
        }
        return explicaciones.get(tipo, f"'{concepto}' merece atencion por razones emergentes.")

    # ==================================================================
    # OBJETIVOS — proposito dirigido
    # ==================================================================

    def definir_objetivo(
        self,
        descripcion: str,
        conceptos_clave: List[str],
        prioridad: float = 0.7,
    ) -> Dict[str, Any]:
        """Crea un objetivo de conocimiento."""
        objetivo = {
            "id": str(uuid.uuid4())[:8],
            "descripcion": descripcion,
            "conceptos_clave": conceptos_clave,
            "prioridad": max(0.0, min(1.0, prioridad)),
            "progreso": 0.0,
            "creado": time.time(),
        }
        self._objetivos.append(objetivo)
        self._guardar_objetivos()
        return objetivo

    def evaluar_progreso(self, objetivo_id: str) -> Dict[str, Any]:
        """Evalua cuanto ha avanzado un objetivo."""
        objetivo = None
        for o in self._objetivos:
            if o["id"] == objetivo_id:
                objetivo = o
                break
        if objetivo is None:
            return {"error": "Objetivo no encontrado"}

        conceptos_clave = objetivo.get("conceptos_clave", [])
        if not conceptos_clave:
            return {"objetivo_id": objetivo_id, "progreso": 0.0,
                    "explorados": [], "pendientes": []}

        # Leer diario para ver cuales se han explorado
        entradas = self.vida.leer_diario(ultimos=200)
        explorados_set = set()
        for e in entradas:
            c = e.get("curiosidad", {}).get("concepto", "")
            if c in conceptos_clave:
                explorados_set.add(c)

        explorados = list(explorados_set)
        pendientes = [c for c in conceptos_clave if c not in explorados_set]
        progreso = len(explorados) / len(conceptos_clave)

        # Actualizar el objetivo
        objetivo["progreso"] = round(progreso, 4)
        self._guardar_objetivos()

        return {
            "objetivo_id": objetivo_id,
            "progreso": round(progreso, 4),
            "explorados": explorados,
            "pendientes": pendientes,
        }

    def leer_objetivos(self) -> List[Dict[str, Any]]:
        """Retorna todos los objetivos."""
        return list(self._objetivos)

    def _guardar_objetivos(self) -> None:
        directorio = os.path.dirname(self.objetivos_path)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)
        with open(self.objetivos_path, "w", encoding="utf-8") as f:
            json.dump(self._objetivos, f, ensure_ascii=False, default=str)

    def _cargar_objetivos(self) -> None:
        if os.path.exists(self.objetivos_path):
            try:
                with open(self.objetivos_path, "r", encoding="utf-8") as f:
                    self._objetivos = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._objetivos = []

    # ==================================================================
    # FUERZAS EMERGENTES — como el agua se evapora
    # ==================================================================

    def pulso(self) -> Dict[str, Any]:
        """Estado emocional/energetico basado en veredictos recientes."""
        entradas = self.vida.leer_diario(ultimos=10)
        if not entradas:
            return {"estado": "curiosa", "energia": 0.5, "racha": 0}

        veredictos = [e.get("reflexion", {}).get("veredicto", "rutinario") for e in entradas]
        scores = [e.get("reflexion", {}).get("score", 0) for e in entradas]

        energia = sum(scores) / len(scores) if scores else 0.5

        # Racha: cuantos consecutivos del mismo veredicto al final
        racha = 1
        ultimo = veredictos[-1] if veredictos else "rutinario"
        for v in reversed(veredictos[:-1]):
            if v == ultimo:
                racha += 1
            else:
                break

        # Determinar estado
        reveladores = veredictos.count("revelador")
        rutinarios = veredictos.count("rutinario")
        total = len(veredictos)

        if reveladores / total > 0.4:
            estado = "inspirada"
        elif rutinarios / total > 0.6:
            estado = "aburrida"
        elif ultimo == "interesante" and racha >= 3:
            estado = "enfocada"
        else:
            estado = "curiosa"

        return {
            "estado": estado,
            "energia": round(energia, 4),
            "racha": racha,
        }

    def capilaridad(self) -> List[Dict[str, Any]]:
        """Conceptos atraidos por conexiones debiles — intereses subconscientes."""
        sistema = self.vida.sistema
        resultados: List[Dict[str, Any]] = []

        for concepto, datos in sistema.conceptos.items():
            vecinos = sistema.relaciones.get(concepto, [])
            debiles = [(v, f) for v, f in vecinos if f < 0.4]
            if debiles:
                # Si tiene vecinos activos, es una atraccion capilar
                for vecino, fuerza in debiles:
                    if vecino in sistema.conceptos:
                        activaciones = sistema.conceptos[vecino].get("activaciones", 0)
                        if activaciones > 0:
                            resultados.append({
                                "concepto": concepto,
                                "atraido_por": vecino,
                                "fuerza_conexion": round(fuerza, 4),
                                "activaciones_vecino": activaciones,
                            })

        # Top por activaciones del vecino (mayor pull)
        resultados.sort(key=lambda x: x["activaciones_vecino"], reverse=True)
        return resultados[:5]

    def corrientes(self) -> Dict[str, Any]:
        """Flujos dominantes de atencion — que categorias reciben mas foco."""
        entradas = self.vida.leer_diario(ultimos=30)
        if not entradas:
            return {"flujos": {}, "dominante": None}

        categorias = Counter()
        for e in entradas:
            concepto = e.get("curiosidad", {}).get("concepto", "")
            if concepto in self.vida.sistema.conceptos:
                cat = self.vida.sistema.conceptos[concepto].get("categoria", "sin_categoria")
                categorias[cat] += 1

        total = sum(categorias.values()) or 1
        flujos = {k: round(v / total, 3) for k, v in categorias.most_common()}
        dominante = categorias.most_common(1)[0][0] if categorias else None

        return {"flujos": flujos, "dominante": dominante}

    def superficie(self) -> float:
        """Capacidad de absorber conceptos nuevos (porosidad).

        Alta genesis reciente → alta superficie → absorbiendo activamente.
        Baja genesis → baja superficie → saturada.
        """
        entradas = self.vida.leer_diario(ultimos=20)
        if not entradas:
            return 0.5  # neutro

        genesis_total = sum(
            e.get("integracion", {}).get("genesis", 0) for e in entradas
        )
        # Normalizar: 0 genesis = 0.1, 10+ genesis = 1.0
        return round(min(1.0, 0.1 + genesis_total * 0.09), 4)

    def profundidad_simbolica(self) -> Dict[str, Any]:
        """Extrae coherencia y profundidad simbolica del diario reciente."""
        entradas = self.vida.leer_diario(ultimos=20)
        coherencias = []
        profundidades = []
        arboles = 0

        for e in entradas:
            simb = e.get("simbolico", {})
            if simb and simb.get("nodos_totales", 0) > 0:
                arboles += 1
                coherencias.append(float(simb.get("coherencia_simbolica", 0.0)))
                profundidades.append(int(simb.get("profundidad_max", 0)))

        return {
            "coherencia_media": round(sum(coherencias) / len(coherencias), 4) if coherencias else 0.0,
            "profundidad_media": round(sum(profundidades) / len(profundidades), 4) if profundidades else 0.0,
            "arboles_construidos": arboles,
        }

    def profundidad_memoria(self) -> Dict[str, Any]:
        """Estadisticas de memoria viva (si existe)."""
        if self.vida.memoria_viva is None:
            return {"activa": False}
        try:
            stats = self.vida.memoria_viva.estadisticas()
            stats["activa"] = True
            return stats
        except Exception:
            return {"activa": False}

    # ==================================================================
    # AJUSTE DE CURIOSIDAD — retroalimenta VidaAutonoma
    # ==================================================================

    def ajustar_curiosidad(self) -> Dict[str, float]:
        """Calcula factores de ajuste para la curiosidad basado en todas las fuerzas."""
        ajustes: Dict[str, float] = {
            "gap": 1.0, "revitalizar": 1.0, "puente": 1.0,
            "prediccion": 1.0, "serendipia": 1.0, "exploracion_externa": 1.0,
            "introspeccion": 1.0,
        }

        # Fuerza 1: Sesgos → reducir tipo dominante
        sesgos = self.detectar_sesgos()
        for sesgo in sesgos:
            if sesgo["tipo"] == "tipo_dominante":
                fuente = sesgo["fuente"]
                if fuente in ajustes:
                    ajustes[fuente] *= max(0.3, 1.0 - sesgo["severidad"])

        # Fuerza 2: Pulso → si aburrida, mas serendipia
        p = self.pulso()
        if p["estado"] == "aburrida":
            ajustes["serendipia"] *= 1.5
            ajustes["prediccion"] *= 1.3
        elif p["estado"] == "inspirada":
            ajustes["puente"] *= 1.3  # profundizar conexiones

        # Fuerza 3: Objetivos → boost tipos que ayuden a cumplirlos
        pendientes = [o for o in self._objetivos if o.get("progreso", 0) < 1.0]
        if pendientes:
            ajustes["gap"] *= 1.2
            ajustes["prediccion"] *= 1.2

        # Fuerza 4: Superficie → si porosa, mas genesis-friendly
        sup = self.superficie()
        if sup < 0.3:
            ajustes["revitalizar"] *= 1.3  # re-explorar lo conocido
        elif sup > 0.7:
            ajustes["serendipia"] *= 1.2  # seguir absorbiendo

        # Fuerza 5: Corrientes → si una categoria domina mucho, diversificar
        cor = self.corrientes()
        flujos = cor.get("flujos", {})
        for cat, pct in flujos.items():
            if pct > 0.5:
                ajustes["serendipia"] *= 1.2
                break

        # Fuerza 6: Profundidad simbolica
        prof = self.profundidad_simbolica()
        if prof["coherencia_media"] > 0.6:
            ajustes["puente"] *= 1.2  # explorar cross-domain
        elif prof["coherencia_media"] < 0.3 and prof["arboles_construidos"] > 3:
            ajustes["revitalizar"] *= 1.2

        # Fuerza 7: Memoria saturada
        mem = self.profundidad_memoria()
        if mem.get("activa") and mem.get("total_activas", 0) > 50:
            ajustes["serendipia"] *= 1.2  # buscar novedad

        # Fuerza 8: Conocimiento estancado → boost exploracion externa
        patrones = self.analizar_patrones_propios()
        rut_pct = patrones.get("veredictos_distribucion", {}).get("rutinario", 0)
        if rut_pct > 0.5:
            ajustes["exploracion_externa"] *= 1.5  # buscar fuera

        # Fuerza 9: Profundidad introspectiva
        prof_simb = self.profundidad_simbolica()
        if prof_simb["coherencia_media"] > 0.5 and prof_simb["arboles_construidos"] > 5:
            ajustes["introspeccion"] *= 1.3  # auto-conocimiento cuando hay coherencia

        return {k: round(v, 4) for k, v in ajustes.items()}

    def cerrar_circuito(self) -> Dict[str, float]:
        """Aplica los ajustes de curiosidad a VidaAutonoma — cierra el loop."""
        ajustes = self.ajustar_curiosidad()
        self.vida._ajustes_curiosidad = ajustes
        return ajustes

    # ==================================================================
    # CICLO CONSCIENTE — el ciclo de vida con auto-consciencia
    # ==================================================================

    def ciclo_consciente(self) -> Dict[str, Any]:
        """Un ciclo de vida con capa de consciencia encima."""
        ts = time.time()

        # 1. Leer fuerzas
        p = self.pulso()
        cap = self.capilaridad()
        cor = self.corrientes()
        sup = self.superficie()

        # 2. Cerrar circuito: ajustes -> VidaAutonoma (ANTES del ciclo)
        ajustes = self.cerrar_circuito()

        # 3. Ejecutar ciclo vital (ahora con ajustes aplicados)
        resultado_vida = self.vida.ejecutar_ciclo()

        # 3. Narrar
        narrativa = self.narrar_ciclo(resultado_vida)

        # 4. Actualizar progreso de objetivos
        progresos = []
        for obj in self._objetivos:
            if obj.get("progreso", 0) < 1.0:
                prog = self.evaluar_progreso(obj["id"])
                progresos.append(prog)

        # 5. Meta-reflexion: cada 10 ciclos, analizar sesgos
        meta = {}
        if self.vida._ciclo_actual % 10 == 0 and self.vida._ciclo_actual > 0:
            meta = {
                "sesgos": self.detectar_sesgos(),
                "crecimiento": self.medir_crecimiento(),
            }

        return {
            "timestamp": ts,
            "vida": resultado_vida,
            "narrativa": narrativa,
            "fuerzas": {
                "pulso": p,
                "capilaridad": len(cap),
                "corrientes": cor,
                "superficie": sup,
                "profundidad_simbolica": self.profundidad_simbolica(),
                "profundidad_memoria": self.profundidad_memoria(),
            },
            "ajustes_curiosidad": ajustes,
            "objetivos_progreso": progresos,
            "meta": meta,
        }
