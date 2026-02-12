"""
Motor de Insights Automaticos para IANAE.

Analisis estructural del grafo: comunidades, centralidad, clustering,
PageRank, predicciones. Todo local, sin LLM.
"""
import logging
from typing import Dict, List, Tuple, Optional, Any

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


class InsightsEngine:
    """
    Genera insights automaticos a partir del grafo de conceptos IANAE.

    Tres ejes:
      - detectar_patrones(): comunidades, puentes, clusters
      - generar_recomendaciones(): explorar, conectar, automatizar
      - analisis_predictivo(): tendencias, gaps, predicciones
    """

    def __init__(self, sistema, pensamiento=None):
        self.sistema = sistema
        self.pensamiento = pensamiento

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _grafo(self) -> nx.Graph:
        return self.sistema.grafo

    def _nodos_insuficientes(self) -> bool:
        return self._grafo.number_of_nodes() < 2

    # ------------------------------------------------------------------
    # 1. DETECTOR DE PATRONES
    # ------------------------------------------------------------------

    def _detectar_comunidades(self) -> List[List[str]]:
        if self._nodos_insuficientes():
            return []
        try:
            comunidades = nx.community.louvain_communities(
                self._grafo, weight="weight", seed=42
            )
        except Exception:
            return [list(self._grafo.nodes)]
        resultado = [sorted(list(c)) for c in comunidades]
        resultado.sort(key=len, reverse=True)
        return resultado

    def _detectar_puentes(self, top_k: int = 5) -> List[Tuple[str, float]]:
        if self._nodos_insuficientes():
            return []
        bc = nx.betweenness_centrality(self._grafo, weight="weight")
        ranking = sorted(bc.items(), key=lambda x: x[1], reverse=True)
        return [(nombre, round(valor, 4)) for nombre, valor in ranking[:top_k]]

    def _analizar_clustering(self, umbral_alto: float = 0.6) -> Dict[str, Any]:
        if self._nodos_insuficientes():
            return {"clusters_densos": [], "conceptos_aislados": [], "media": 0.0}
        coefs = nx.clustering(self._grafo, weight="weight")
        valores = list(coefs.values())
        media = float(np.mean(valores)) if valores else 0.0
        clusters_densos = [
            {"concepto": c, "coeficiente": round(v, 4)}
            for c, v in coefs.items()
            if v >= umbral_alto
        ]
        clusters_densos.sort(key=lambda x: x["coeficiente"], reverse=True)
        conceptos_aislados = [c for c, v in coefs.items() if v == 0.0]
        return {
            "clusters_densos": clusters_densos,
            "conceptos_aislados": sorted(conceptos_aislados),
            "media": round(media, 4),
        }

    def _narrar_patrones(self, comunidades, puentes, clustering) -> str:
        partes = []
        n_com = len(comunidades)
        partes.append(
            f"Se detectaron {n_com} comunidades en el grafo."
        )
        if comunidades:
            mayor = comunidades[0]
            partes.append(
                f"La comunidad mas grande tiene {len(mayor)} conceptos: "
                + ", ".join(mayor[:5])
                + ("..." if len(mayor) > 5 else "")
                + "."
            )
        if puentes:
            top = puentes[0]
            partes.append(
                f"El principal puente es '{top[0]}' con centralidad {top[1]}."
            )
        media = clustering.get("media", 0)
        partes.append(f"Coeficiente de clustering medio: {media}.")
        n_densos = len(clustering.get("clusters_densos", []))
        n_aislados = len(clustering.get("conceptos_aislados", []))
        if n_densos:
            partes.append(f"Hay {n_densos} conceptos en clusters densos.")
        if n_aislados:
            partes.append(f"Hay {n_aislados} conceptos aislados (clustering 0).")
        return " ".join(partes)

    def detectar_patrones(self) -> Dict[str, Any]:
        if self._nodos_insuficientes():
            return {
                "comunidades": [],
                "puentes": [],
                "clusters_densos": [],
                "conceptos_aislados": [],
                "patrones_emergentes": "",
                "candidatos_genesis": [],
                "narrativa": "Grafo insuficiente para detectar patrones.",
            }

        comunidades = self._detectar_comunidades()
        puentes = self._detectar_puentes()
        clustering = self._analizar_clustering()

        # Sub-resultados del sistema
        emergentes = self.sistema.detectar_emergencias()
        if not isinstance(emergentes, str):
            emergentes = str(emergentes)

        candidatos = self.sistema.detectar_candidatos_genesis()

        narrativa = self._narrar_patrones(comunidades, puentes, clustering)

        return {
            "comunidades": comunidades,
            "puentes": [{"concepto": c, "centralidad": v} for c, v in puentes],
            "clusters_densos": clustering["clusters_densos"],
            "conceptos_aislados": clustering["conceptos_aislados"],
            "patrones_emergentes": emergentes,
            "candidatos_genesis": [
                {"concepto1": c1, "concepto2": c2, "frecuencia": round(f, 4)}
                for c1, c2, f in candidatos
            ],
            "narrativa": narrativa,
        }

    # ------------------------------------------------------------------
    # 2. RECOMENDACIONES
    # ------------------------------------------------------------------

    def _calcular_pagerank(self, top_k: int = 10) -> List[Tuple[str, float]]:
        if self._nodos_insuficientes():
            return []
        pr = nx.pagerank(self._grafo, weight="weight")
        ranking = sorted(pr.items(), key=lambda x: x[1], reverse=True)
        return [(nombre, round(valor, 4)) for nombre, valor in ranking[:top_k]]

    def _encontrar_conexiones_faltantes(
        self, concepto: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if concepto not in self._grafo:
            return []
        vecinos = set(self._grafo.neighbors(concepto))
        sugerencias = []
        try:
            distancias = nx.single_source_shortest_path_length(
                self._grafo, concepto, cutoff=2
            )
        except nx.NetworkXError:
            return []
        for nodo, dist in distancias.items():
            if dist == 2 and nodo not in vecinos and nodo != concepto:
                # Calcular similitud vectorial si es posible
                sim = 0.0
                if concepto in self.sistema.conceptos and nodo in self.sistema.conceptos:
                    v1 = self.sistema.conceptos[concepto]["actual"]
                    v2 = self.sistema.conceptos[nodo]["actual"]
                    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                    if n1 > 0 and n2 > 0:
                        sim = float(np.dot(v1, v2) / (n1 * n2))
                sugerencias.append({
                    "concepto": nodo,
                    "distancia": dist,
                    "similitud": round(sim, 4),
                    "categoria": self.sistema.conceptos.get(nodo, {}).get(
                        "categoria", "emergentes"
                    ),
                })
        sugerencias.sort(key=lambda x: x["similitud"], reverse=True)
        return sugerencias[:top_k]

    def _sugerir_exploraciones_por_comunidad(
        self, concepto: str
    ) -> List[Dict[str, Any]]:
        if concepto not in self._grafo:
            return []
        comunidades = self._detectar_comunidades()
        comunidad_origen = None
        for com in comunidades:
            if concepto in com:
                comunidad_origen = set(com)
                break
        if comunidad_origen is None:
            return []
        sugerencias = []
        for com in comunidades:
            com_set = set(com)
            if com_set == comunidad_origen:
                continue
            for nodo in com:
                if nodo == concepto:
                    continue
                sim = 0.0
                if concepto in self.sistema.conceptos and nodo in self.sistema.conceptos:
                    v1 = self.sistema.conceptos[concepto]["actual"]
                    v2 = self.sistema.conceptos[nodo]["actual"]
                    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                    if n1 > 0 and n2 > 0:
                        sim = float(np.dot(v1, v2) / (n1 * n2))
                sugerencias.append({
                    "concepto": nodo,
                    "similitud": round(sim, 4),
                    "categoria": self.sistema.conceptos.get(nodo, {}).get(
                        "categoria", "emergentes"
                    ),
                    "tipo": "cross-community",
                })
        sugerencias.sort(key=lambda x: x["similitud"], reverse=True)
        return sugerencias[:5]

    def _narrar_recomendaciones(
        self, explorar, conectar, concepto=None
    ) -> str:
        partes = []
        if concepto:
            partes.append(
                f"Recomendaciones para '{concepto}':"
            )
        else:
            partes.append("Recomendaciones globales para el sistema:")
        if explorar:
            top = explorar[0]
            partes.append(
                f"Se sugiere explorar '{top['concepto']}' "
                f"(similitud {top.get('similitud', 'N/A')})."
            )
        if conectar:
            top = conectar[0]
            partes.append(
                f"Conexion faltante principal: '{top['concepto']}' "
                f"a distancia {top.get('distancia', 2)}."
            )
        if not explorar and not conectar:
            partes.append("No se encontraron recomendaciones especificas.")
        return " ".join(partes)

    def generar_recomendaciones(
        self, concepto: Optional[str] = None, max_resultados: int = 5
    ) -> Dict[str, Any]:
        if self._nodos_insuficientes():
            return {
                "explorar": [],
                "conectar": [],
                "automatizar": None,
                "convergencias": None,
                "narrativa": "Grafo insuficiente para generar recomendaciones.",
            }

        # Si concepto no existe, retornar vacio con mensaje
        if concepto is not None and concepto not in self.sistema.conceptos:
            return {
                "explorar": [],
                "conectar": [],
                "automatizar": None,
                "convergencias": None,
                "narrativa": f"Concepto '{concepto}' no encontrado.",
            }

        if concepto:
            explorar = self._sugerir_exploraciones_por_comunidad(concepto)[
                :max_resultados
            ]
            conectar = self._encontrar_conexiones_faltantes(
                concepto, top_k=max_resultados
            )
        else:
            # Recomendaciones globales: usar pagerank
            pr = self._calcular_pagerank(top_k=max_resultados)
            explorar = [
                {
                    "concepto": nombre,
                    "pagerank": valor,
                    "categoria": self.sistema.conceptos.get(nombre, {}).get(
                        "categoria", "emergentes"
                    ),
                }
                for nombre, valor in pr
            ]
            # Conexiones faltantes del concepto mas central
            if pr:
                top_concepto = pr[0][0]
                conectar = self._encontrar_conexiones_faltantes(
                    top_concepto, top_k=max_resultados
                )
            else:
                conectar = []

        # Sub-resultados opcionales del pensamiento
        automatizar = None
        convergencias = None
        if self.pensamiento is not None:
            try:
                automatizar = self.pensamiento.detectar_oportunidades_automatizacion()
            except Exception:
                pass
            try:
                convergencias = self.pensamiento.experimento_convergencia_proyectos()
            except Exception:
                pass

        narrativa = self._narrar_recomendaciones(explorar, conectar, concepto)

        return {
            "explorar": explorar,
            "conectar": conectar,
            "automatizar": automatizar,
            "convergencias": convergencias,
            "narrativa": narrativa,
        }

    # ------------------------------------------------------------------
    # 3. ANALISIS PREDICTIVO
    # ------------------------------------------------------------------

    def _analizar_tendencias_activacion(
        self, ventana: int = 20
    ) -> List[Dict[str, Any]]:
        historial = self.sistema.historial_activaciones
        if not historial:
            return []
        ultimas = historial[-ventana:]
        # Contar frecuencia y recencia por concepto
        freq: Dict[str, int] = {}
        recencia: Dict[str, int] = {}
        for i, entry in enumerate(ultimas):
            if isinstance(entry, dict) and "resultado" in entry:
                activos = entry["resultado"]
            elif isinstance(entry, dict):
                activos = entry
            else:
                continue
            for c, v in activos.items():
                if isinstance(v, (int, float)) and v > 0.1:
                    freq[c] = freq.get(c, 0) + 1
                    recencia[c] = max(recencia.get(c, 0), i)

        if not freq:
            return []

        n = len(ultimas)
        tendencias = []
        for concepto, count in freq.items():
            rec = recencia.get(concepto, 0)
            ratio_freq = count / n
            ratio_rec = rec / max(n - 1, 1)
            # Tendencia ascendente si frecuente Y reciente
            if ratio_freq > 0.3 and ratio_rec > 0.5:
                direccion = "ascendente"
            elif ratio_freq < 0.15 or ratio_rec < 0.3:
                direccion = "descendente"
            else:
                direccion = "estable"
            tendencias.append({
                "concepto": concepto,
                "frecuencia": round(ratio_freq, 4),
                "recencia": round(ratio_rec, 4),
                "direccion": direccion,
            })
        tendencias.sort(key=lambda x: x["frecuencia"], reverse=True)
        return tendencias

    def _detectar_gaps_conocimiento(self) -> List[Dict[str, Any]]:
        if self._nodos_insuficientes():
            return []
        # Intentar eigenvector centrality, fallback a degree
        try:
            centrality = nx.eigenvector_centrality_numpy(
                self._grafo, weight="weight"
            )
        except Exception:
            centrality = nx.degree_centrality(self._grafo)

        # Agrupar por categoria y calcular densidad
        categorias: Dict[str, List[float]] = {}
        for nodo, cent in centrality.items():
            cat = self.sistema.conceptos.get(nodo, {}).get(
                "categoria", "emergentes"
            )
            categorias.setdefault(cat, []).append(cent)

        if not categorias:
            return []

        media_global = float(np.mean(list(centrality.values())))
        gaps = []
        for cat, valores in categorias.items():
            media_cat = float(np.mean(valores))
            if media_cat < media_global * 0.8:
                gaps.append({
                    "categoria": cat,
                    "centralidad_media": round(media_cat, 4),
                    "centralidad_global": round(media_global, 4),
                    "deficit": round(media_global - media_cat, 4),
                    "conceptos": len(valores),
                })
        gaps.sort(key=lambda x: x["deficit"], reverse=True)
        return gaps

    def _predecir_proximas_tecnologias(
        self, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if self._nodos_insuficientes():
            return []
        # Centralidad alta + activaciones bajas = potencial no explorado
        try:
            centrality = nx.eigenvector_centrality_numpy(
                self._grafo, weight="weight"
            )
        except Exception:
            centrality = nx.degree_centrality(self._grafo)

        predicciones = []
        for nodo, cent in centrality.items():
            if nodo not in self.sistema.conceptos:
                continue
            activaciones = self.sistema.conceptos[nodo].get("activaciones", 0)
            # Centralidad alta pero pocas activaciones = potencial
            if cent > 0.01 and activaciones < 5:
                q_score = 0.0
                if hasattr(self.sistema, "aprendizaje"):
                    q_vals = [
                        self.sistema.aprendizaje.get_q(nodo, v)
                        for v in self._grafo.neighbors(nodo)
                    ]
                    q_score = float(np.mean(q_vals)) if q_vals else 0.0
                score = cent * (1.0 + abs(q_score))
                predicciones.append({
                    "concepto": nodo,
                    "centralidad": round(cent, 4),
                    "activaciones": activaciones,
                    "q_score": round(q_score, 4),
                    "score_prediccion": round(score, 4),
                    "categoria": self.sistema.conceptos[nodo].get(
                        "categoria", "emergentes"
                    ),
                })
        predicciones.sort(key=lambda x: x["score_prediccion"], reverse=True)
        return predicciones[:top_k]

    def _narrar_predictivo(self, tendencias, gaps, predicciones) -> str:
        partes = []
        asc = [t for t in tendencias if t["direccion"] == "ascendente"]
        desc = [t for t in tendencias if t["direccion"] == "descendente"]
        if asc:
            nombres = ", ".join(t["concepto"] for t in asc[:3])
            partes.append(f"Tendencias ascendentes: {nombres}.")
        if desc:
            nombres = ", ".join(t["concepto"] for t in desc[:3])
            partes.append(f"Tendencias descendentes: {nombres}.")
        if not tendencias:
            partes.append("Sin historial suficiente para detectar tendencias.")
        if gaps:
            cats = ", ".join(g["categoria"] for g in gaps[:3])
            partes.append(f"Gaps de conocimiento en: {cats}.")
        if predicciones:
            top = predicciones[0]
            partes.append(
                f"Prediccion principal: '{top['concepto']}' "
                f"(score {top['score_prediccion']})."
            )
        return " ".join(partes)

    def analisis_predictivo(self) -> Dict[str, Any]:
        if self._nodos_insuficientes():
            return {
                "tendencias": [],
                "gaps_conocimiento": [],
                "proximas_tecnologias": [],
                "patrones_personales": None,
                "narrativa": "Grafo insuficiente para analisis predictivo.",
            }

        tendencias = self._analizar_tendencias_activacion()
        gaps = self._detectar_gaps_conocimiento()
        predicciones = self._predecir_proximas_tecnologias()

        # Sub-resultado opcional del pensamiento
        patrones_personales = None
        if self.pensamiento is not None:
            try:
                patrones_personales = self.pensamiento.analizar_patrones_personales()
            except Exception:
                pass

        narrativa = self._narrar_predictivo(tendencias, gaps, predicciones)

        return {
            "tendencias": tendencias,
            "gaps_conocimiento": gaps,
            "proximas_tecnologias": predicciones,
            "patrones_personales": patrones_personales,
            "narrativa": narrativa,
        }
