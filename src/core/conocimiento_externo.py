"""
Conocimiento Externo — Fase 13: IANAE se abre al mundo.

Sistema de forrajeo de conocimiento externo con 5 etapas (digestion):
  Appetite   → La curiosidad decide QUE buscar
  Foraging   → Un adaptador obtiene contenido crudo de una fuente
  Digestion  → NLP extrae conceptos; filtro de calidad puntua relevancia
  Absorption → Solo conceptos que superan umbral entran al grafo (rate-limited)
  Integration→ Pipeline estandar de reflexion/integracion evalua resultado

Fuentes implementadas (stdlib only, sin dependencias nuevas):
  - Wikipedia (MediaWiki API, español por defecto)
  - RSS/Atom (xml.etree.ElementTree)
  - Web (DuckDuckGo Instant Answer API)
  - Archivos locales (.txt, .md, .json, .csv, .py, .html)
"""
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

logger = logging.getLogger(__name__)


# ======================================================================
# Fuentes externas (ABC + implementaciones)
# ======================================================================


class FuenteExterna(ABC):
    """Clase base para todas las fuentes de conocimiento."""

    @abstractmethod
    def buscar(self, consulta: str, max_resultados: int = 5) -> List[Dict]:
        """Busca contenido. Retorna lista de {titulo, texto, fuente, relevancia}."""
        ...

    @abstractmethod
    def disponible(self) -> bool:
        """Indica si la fuente puede responder ahora."""
        ...

    def estado(self) -> Dict[str, Any]:
        """Estado de la fuente."""
        return {
            "tipo": self.__class__.__name__,
            "disponible": self.disponible(),
        }


# ----------------------------------------------------------------------
# Wikipedia
# ----------------------------------------------------------------------


class FuenteWikipedia(FuenteExterna):
    """MediaWiki API — busqueda + extractos, español primero."""

    OPENSEARCH = "https://{lang}.wikipedia.org/w/api.php"

    def __init__(self, lang: str = "es", cooldown: float = 1.0, timeout: float = 5.0):
        self._lang = lang
        self._cooldown = cooldown
        self._timeout = timeout
        self._ultimo_request: float = 0.0
        self._busquedas: int = 0
        self._errores: int = 0

    def disponible(self) -> bool:
        return (time.time() - self._ultimo_request) >= self._cooldown

    def buscar(self, consulta: str, max_resultados: int = 3) -> List[Dict]:
        self._esperar_cooldown()
        titulos = self._opensearch(consulta, max_resultados)
        resultados: List[Dict] = []
        for titulo in titulos:
            texto = self._extraer(titulo)
            if texto:
                resultados.append({
                    "titulo": titulo,
                    "texto": texto[:5000],
                    "fuente": f"wikipedia_{self._lang}",
                    "relevancia": 1.0,
                })
        self._busquedas += 1
        return resultados

    def estado(self) -> Dict[str, Any]:
        return {
            **super().estado(),
            "lang": self._lang,
            "busquedas": self._busquedas,
            "errores": self._errores,
        }

    # -- helpers --

    def _esperar_cooldown(self):
        ahora = time.time()
        restante = self._cooldown - (ahora - self._ultimo_request)
        if restante > 0:
            time.sleep(restante)
        self._ultimo_request = time.time()

    def _opensearch(self, consulta: str, limit: int) -> List[str]:
        params = urlencode({
            "action": "opensearch",
            "search": consulta,
            "limit": limit,
            "namespace": 0,
            "format": "json",
        })
        url = f"{self.OPENSEARCH.format(lang=self._lang)}?{params}"
        try:
            req = Request(url, headers={"User-Agent": "IANAE/1.0"})
            with urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # opensearch returns [query, [titles], [descriptions], [urls]]
            return data[1] if len(data) > 1 else []
        except Exception:
            self._errores += 1
            logger.debug("Wikipedia opensearch error para '%s'", consulta)
            return []

    def _extraer(self, titulo: str) -> str:
        params = urlencode({
            "action": "query",
            "titles": titulo,
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "format": "json",
        })
        url = f"{self.OPENSEARCH.format(lang=self._lang)}?{params}"
        try:
            req = Request(url, headers={"User-Agent": "IANAE/1.0"})
            with urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                if extract:
                    return extract
        except Exception:
            self._errores += 1
            logger.debug("Wikipedia extract error para '%s'", titulo)
        return ""


# ----------------------------------------------------------------------
# RSS / Atom
# ----------------------------------------------------------------------


class FuenteRSS(FuenteExterna):
    """Lector RSS/Atom con cache y busqueda por keywords."""

    DEFAULT_FEEDS = [
        "https://hnrss.org/newest?q=python",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
    ]

    def __init__(self, feeds: Optional[List[str]] = None, cache_ttl: float = 3600.0,
                 timeout: float = 5.0):
        self._feeds: List[str] = list(feeds) if feeds is not None else list(self.DEFAULT_FEEDS)
        self._cache_ttl = cache_ttl
        self._timeout = timeout
        self._cache: Dict[str, Dict] = {}  # url -> {items, timestamp}
        self._busquedas: int = 0
        self._errores: int = 0

    def disponible(self) -> bool:
        return len(self._feeds) > 0

    def buscar(self, consulta: str, max_resultados: int = 5) -> List[Dict]:
        keywords = set(consulta.lower().split())
        resultados: List[Dict] = []
        for feed_url in self._feeds:
            items = self._obtener_items(feed_url)
            for item in items:
                titulo = item.get("titulo", "").lower()
                descripcion = item.get("descripcion", "").lower()
                texto_completo = titulo + " " + descripcion
                matches = sum(1 for k in keywords if k in texto_completo)
                if matches > 0:
                    relevancia = min(1.0, matches / max(1, len(keywords)))
                    resultados.append({
                        "titulo": item.get("titulo", ""),
                        "texto": item.get("descripcion", "")[:5000],
                        "fuente": f"rss:{feed_url}",
                        "relevancia": relevancia,
                    })
        resultados.sort(key=lambda r: r["relevancia"], reverse=True)
        self._busquedas += 1
        return resultados[:max_resultados]

    def agregar_feed(self, url: str) -> None:
        if url not in self._feeds:
            self._feeds.append(url)

    def quitar_feed(self, url: str) -> bool:
        if url in self._feeds:
            self._feeds.remove(url)
            self._cache.pop(url, None)
            return True
        return False

    def listar_feeds(self) -> List[str]:
        return list(self._feeds)

    def estado(self) -> Dict[str, Any]:
        return {
            **super().estado(),
            "feeds": len(self._feeds),
            "busquedas": self._busquedas,
            "errores": self._errores,
            "items_en_cache": sum(
                len(c.get("items", [])) for c in self._cache.values()
            ),
        }

    # -- helpers --

    def _obtener_items(self, feed_url: str) -> List[Dict]:
        cached = self._cache.get(feed_url)
        if cached and (time.time() - cached["timestamp"]) < self._cache_ttl:
            return cached["items"]

        items = self._parsear_feed(feed_url)
        self._cache[feed_url] = {"items": items, "timestamp": time.time()}
        return items

    def _parsear_feed(self, feed_url: str) -> List[Dict]:
        try:
            req = Request(feed_url, headers={"User-Agent": "IANAE/1.0"})
            with urlopen(req, timeout=self._timeout) as resp:
                xml_bytes = resp.read()
            return self._parsear_xml(xml_bytes)
        except Exception:
            self._errores += 1
            logger.debug("RSS fetch error para '%s'", feed_url)
            return []

    def _parsear_xml(self, xml_bytes: bytes) -> List[Dict]:
        items: List[Dict] = []
        try:
            root = ElementTree.fromstring(xml_bytes)
        except ElementTree.ParseError:
            return items

        # RSS 2.0
        for item in root.iter("item"):
            titulo = self._text(item, "title")
            desc = self._text(item, "description")
            link = self._text(item, "link")
            if titulo:
                items.append({"titulo": titulo, "descripcion": desc, "link": link})

        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            titulo = self._text(entry, "{http://www.w3.org/2005/Atom}title")
            summary = self._text(entry, "{http://www.w3.org/2005/Atom}summary")
            content = self._text(entry, "{http://www.w3.org/2005/Atom}content")
            if titulo:
                items.append({
                    "titulo": titulo,
                    "descripcion": summary or content or "",
                    "link": "",
                })

        return items

    @staticmethod
    def _text(element, tag: str) -> str:
        el = element.find(tag)
        return (el.text or "").strip() if el is not None else ""


# ----------------------------------------------------------------------
# Web (DuckDuckGo Instant Answer)
# ----------------------------------------------------------------------


class FuenteWeb(FuenteExterna):
    """DuckDuckGo Instant Answer API (sin API key)."""

    DDG_URL = "https://api.duckduckgo.com/"

    def __init__(self, cooldown: float = 2.0, timeout: float = 5.0,
                 searxng_url: Optional[str] = None):
        self._cooldown = cooldown
        self._timeout = timeout
        self._searxng_url = searxng_url
        self._ultimo_request: float = 0.0
        self._busquedas: int = 0
        self._errores: int = 0

    def disponible(self) -> bool:
        return (time.time() - self._ultimo_request) >= self._cooldown

    def buscar(self, consulta: str, max_resultados: int = 3) -> List[Dict]:
        self._esperar_cooldown()
        if self._searxng_url:
            return self._buscar_searxng(consulta, max_resultados)
        return self._buscar_ddg(consulta, max_resultados)

    def estado(self) -> Dict[str, Any]:
        return {
            **super().estado(),
            "backend": "searxng" if self._searxng_url else "duckduckgo",
            "busquedas": self._busquedas,
            "errores": self._errores,
        }

    # -- helpers --

    def _esperar_cooldown(self):
        ahora = time.time()
        restante = self._cooldown - (ahora - self._ultimo_request)
        if restante > 0:
            time.sleep(restante)
        self._ultimo_request = time.time()

    def _buscar_ddg(self, consulta: str, max_resultados: int) -> List[Dict]:
        params = urlencode({"q": consulta, "format": "json", "no_html": 1, "skip_disambig": 1})
        url = f"{self.DDG_URL}?{params}"
        try:
            req = Request(url, headers={"User-Agent": "IANAE/1.0"})
            with urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._busquedas += 1
            return self._parsear_ddg(data, max_resultados)
        except Exception:
            self._errores += 1
            logger.debug("DDG search error para '%s'", consulta)
            return []

    def _parsear_ddg(self, data: Dict, max_resultados: int) -> List[Dict]:
        resultados: List[Dict] = []

        # Abstract (main answer)
        abstract = data.get("AbstractText", "")
        if abstract:
            resultados.append({
                "titulo": data.get("Heading", ""),
                "texto": abstract[:5000],
                "fuente": "duckduckgo",
                "relevancia": 1.0,
            })

        # Related topics
        for topic in data.get("RelatedTopics", []):
            if len(resultados) >= max_resultados:
                break
            text = topic.get("Text", "")
            if text:
                resultados.append({
                    "titulo": topic.get("FirstURL", ""),
                    "texto": text[:5000],
                    "fuente": "duckduckgo",
                    "relevancia": 0.6,
                })

        return resultados[:max_resultados]

    def _buscar_searxng(self, consulta: str, max_resultados: int) -> List[Dict]:
        params = urlencode({"q": consulta, "format": "json"})
        url = f"{self._searxng_url}?{params}"
        try:
            req = Request(url, headers={"User-Agent": "IANAE/1.0"})
            with urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._busquedas += 1
            resultados: List[Dict] = []
            for r in data.get("results", [])[:max_resultados]:
                resultados.append({
                    "titulo": r.get("title", ""),
                    "texto": r.get("content", "")[:5000],
                    "fuente": "searxng",
                    "relevancia": 0.8,
                })
            return resultados
        except Exception:
            self._errores += 1
            logger.debug("SearxNG search error para '%s'", consulta)
            return []


# ----------------------------------------------------------------------
# Archivos locales
# ----------------------------------------------------------------------


class FuenteArchivos(FuenteExterna):
    """Escanea archivos locales (.txt, .md, .json, .csv, .py, .html)."""

    EXTENSIONES = {".txt", ".md", ".json", ".csv", ".py", ".html"}
    MAX_FILE_SIZE = 50_000  # 50KB

    def __init__(self, directorios: Optional[List[str]] = None):
        self._directorios: List[str] = list(directorios or [])
        self._busquedas: int = 0

    def disponible(self) -> bool:
        return len(self._directorios) > 0 and any(
            os.path.isdir(d) for d in self._directorios
        )

    def buscar(self, consulta: str, max_resultados: int = 5) -> List[Dict]:
        keywords = set(consulta.lower().split())
        resultados: List[Dict] = []

        for directorio in self._directorios:
            if not os.path.isdir(directorio):
                continue
            for root, _dirs, files in os.walk(directorio):
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in self.EXTENSIONES:
                        continue
                    ruta = os.path.join(root, fname)
                    resultado = self._buscar_en_archivo(ruta, keywords)
                    if resultado:
                        resultados.append(resultado)

        resultados.sort(key=lambda r: r["relevancia"], reverse=True)
        self._busquedas += 1
        return resultados[:max_resultados]

    def estado(self) -> Dict[str, Any]:
        return {
            **super().estado(),
            "directorios": len(self._directorios),
            "busquedas": self._busquedas,
        }

    def _buscar_en_archivo(self, ruta: str, keywords: set) -> Optional[Dict]:
        try:
            size = os.path.getsize(ruta)
            if size > self.MAX_FILE_SIZE:
                return None
            with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                contenido = f.read()
        except (OSError, IOError):
            return None

        contenido_lower = contenido.lower()
        nombre_lower = os.path.basename(ruta).lower()

        # Fase 14: para .py, enriquecer con nombres de clases/metodos via AST
        texto_busqueda = contenido_lower
        if ruta.endswith(".py"):
            try:
                from src.core.introspeccion import ExtractorCodigo
                modulo = ExtractorCodigo.extraer_modulo(ruta)
                if modulo:
                    nombres_ast = []
                    for cls in modulo.get("clases", []):
                        nombres_ast.append(cls["nombre"].lower())
                        nombres_ast.extend(m.lower() for m in cls.get("metodos", []))
                    nombres_ast.extend(f.lower() for f in modulo.get("funciones", []))
                    texto_busqueda = contenido_lower + " " + " ".join(nombres_ast)
            except Exception:
                pass

        matches = sum(1 for k in keywords if k in texto_busqueda or k in nombre_lower)
        if matches == 0:
            return None

        relevancia = min(1.0, matches / max(1, len(keywords)))
        return {
            "titulo": os.path.basename(ruta),
            "texto": contenido[:5000],
            "fuente": f"archivo:{ruta}",
            "relevancia": relevancia,
        }


# ======================================================================
# Filtro de digestion — control de calidad
# ======================================================================


class FiltroDigestion:
    """Pipeline de calidad: extrae conceptos, puntua relevancia, rate-limita."""

    def __init__(
        self,
        sistema=None,
        max_conceptos_por_ciclo: int = 5,
        umbral_relevancia: float = 0.3,
        incertidumbre_externa: float = 0.3,
        factor_relacion: float = 0.6,
    ):
        self.sistema = sistema
        self.max_conceptos_por_ciclo = max_conceptos_por_ciclo
        self.umbral_relevancia = umbral_relevancia
        self.incertidumbre_externa = incertidumbre_externa
        self.factor_relacion = factor_relacion

        self._absorbidos: int = 0
        self._rechazados: int = 0
        self._extractor = None

    def digerir(self, resultados: List[Dict]) -> Dict[str, Any]:
        """Procesa resultados de fuente y retorna conceptos filtrados."""
        conceptos_extraidos: List[Dict] = []

        for resultado in resultados:
            texto = resultado.get("texto", "")
            if not texto:
                continue
            relevancia_fuente = resultado.get("relevancia", 0.5)
            extraidos = self._extraer_conceptos(texto)
            for c in extraidos:
                c["relevancia_fuente"] = relevancia_fuente
                c["fuente"] = resultado.get("fuente", "desconocida")
            conceptos_extraidos.extend(extraidos)

        # Score de relevancia
        scored = self._puntuar(conceptos_extraidos)

        # Filtrar por umbral
        aptos = [c for c in scored if c["score"] >= self.umbral_relevancia]

        # Rate limit
        absorbidos = aptos[:self.max_conceptos_por_ciclo]
        rechazados = len(scored) - len(absorbidos)

        self._absorbidos += len(absorbidos)
        self._rechazados += rechazados

        return {
            "conceptos": absorbidos,
            "total_extraidos": len(scored),
            "absorbidos": len(absorbidos),
            "rechazados": rechazados,
        }

    def absorber(self, conceptos: List[Dict]) -> List[str]:
        """Inyecta conceptos filtrados en el grafo del sistema."""
        if self.sistema is None:
            return []

        nombres_absorbidos: List[str] = []
        for c in conceptos:
            nombre = c.get("nombre", "")
            if not nombre:
                continue

            # Si ya existe, solo activar
            if nombre in self.sistema.conceptos:
                try:
                    self.sistema.activar(nombre, pasos=1, temperatura=0.05)
                except Exception:
                    pass
                continue

            # Añadir con incertidumbre alta y categoria especial
            try:
                self.sistema.añadir_concepto(
                    nombre,
                    incertidumbre=self.incertidumbre_externa,
                    categoria="conocimiento_externo",
                )
                nombres_absorbidos.append(nombre)
            except Exception:
                logger.debug("Error al absorber concepto '%s'", nombre)
                continue

            # Crear relaciones debiles con conceptos existentes relacionados
            self._crear_relaciones_debiles(nombre, c)

        return nombres_absorbidos

    def estado(self) -> Dict[str, Any]:
        return {
            "absorbidos_total": self._absorbidos,
            "rechazados_total": self._rechazados,
            "umbral_relevancia": self.umbral_relevancia,
            "max_por_ciclo": self.max_conceptos_por_ciclo,
        }

    # -- helpers --

    def _extraer_conceptos(self, texto: str) -> List[Dict]:
        """Extrae conceptos del texto (NLP si disponible, basico si no)."""
        # Intentar NLP
        extractor = self._get_extractor()
        if extractor is not None:
            try:
                return extractor.extraer_conceptos(texto, max_conceptos=10)
            except Exception:
                pass

        # Fallback basico: palabras frecuentes significativas
        return self._extraccion_basica(texto)

    def _extraccion_basica(self, texto: str) -> List[Dict]:
        """Extraccion por frecuencia de palabras significativas."""
        STOPWORDS = {
            "de", "la", "el", "en", "un", "una", "es", "se", "que", "por",
            "con", "del", "los", "las", "para", "como", "son", "sus", "mas",
            "al", "lo", "su", "este", "esta", "sin", "hay", "ya", "fue",
            "the", "is", "in", "and", "of", "to", "a", "an", "for", "on",
            "are", "was", "it", "as", "be", "or", "at", "by", "this", "that",
            "from", "with", "has", "its", "not", "but", "which", "also",
        }
        # Limpiar y tokenizar
        texto_limpio = re.sub(r"[^\w\s]", " ", texto.lower())
        palabras = texto_limpio.split()
        palabras = [p for p in palabras if len(p) > 3 and p not in STOPWORDS and p.isalpha()]

        freq = Counter(palabras)
        total = max(1, sum(freq.values()))

        conceptos: List[Dict] = []
        for palabra, count in freq.most_common(10):
            conceptos.append({
                "nombre": palabra,
                "relevancia": min(1.0, count / total * 10),
                "tipo": "keyword",
            })
        return conceptos

    def _puntuar(self, conceptos: List[Dict]) -> List[Dict]:
        """Calcula score combinando relevancia, overlap con grafo, y penaliza ruido."""
        existentes = set(self.sistema.conceptos.keys()) if self.sistema else set()

        for c in conceptos:
            nombre = c.get("nombre", "")
            relevancia_nlp = c.get("relevancia", 0.5)
            relevancia_fuente = c.get("relevancia_fuente", 0.5)

            # Base: promedio de relevancia NLP y relevancia de fuente
            score = (relevancia_nlp + relevancia_fuente) / 2.0

            # Boost: concepto overlaps con grafo existente (+0.2)
            if nombre.lower() in {e.lower() for e in existentes}:
                score += 0.2

            # Boost: nombre tiene parte comun con conceptos del grafo
            for existente in existentes:
                if (len(nombre) > 3 and nombre.lower() in existente.lower()) or \
                   (len(existente) > 3 and existente.lower() in nombre.lower()):
                    score += 0.1
                    break

            # Penalizar ruido: palabras muy cortas o demasiado genericas
            if len(nombre) <= 3:
                score *= 0.5
            if nombre.lower() in {"dato", "tipo", "cosa", "parte", "forma", "modo"}:
                score *= 0.3

            c["score"] = round(min(1.0, max(0.0, score)), 4)

        # Ordenar por score descendente
        conceptos.sort(key=lambda x: x.get("score", 0), reverse=True)
        return conceptos

    def _get_extractor(self):
        """Lazy load del extractor NLP."""
        if self._extractor is not None:
            return self._extractor
        try:
            from src.nlp.extractor import ExtractorConceptos
            self._extractor = ExtractorConceptos(modo="basico")
            return self._extractor
        except ImportError:
            return None

    def _crear_relaciones_debiles(self, nombre: str, concepto_data: Dict) -> None:
        """Crea relaciones debiles entre concepto nuevo y existentes."""
        if self.sistema is None:
            return

        existentes = list(self.sistema.conceptos.keys())
        if not existentes:
            return

        # Buscar conceptos con nombres relacionados
        nombre_lower = nombre.lower()
        relacionados = []
        for existente in existentes:
            if existente == nombre:
                continue
            if nombre_lower in existente.lower() or existente.lower() in nombre_lower:
                relacionados.append(existente)

        # Si no hay relacion por nombre, conectar a los mas activos de la misma categoria
        if not relacionados:
            conceptos_activos = sorted(
                existentes,
                key=lambda c: self.sistema.conceptos[c].get("activaciones", 0),
                reverse=True,
            )
            relacionados = conceptos_activos[:2]

        # Crear relaciones debiles
        for rel in relacionados[:3]:
            try:
                fuerza_base = self.sistema.relacionar(nombre, rel)
                # Debilitar: multiplicar por factor_relacion
                if self.sistema.grafo.has_edge(nombre, rel):
                    self.sistema.grafo[nombre][rel]["weight"] = round(
                        float(fuerza_base) * self.factor_relacion, 4
                    )
            except Exception:
                pass


# ======================================================================
# Orquestador principal
# ======================================================================


class ConocimientoExterno:
    """Orquesta fuentes + filtro de digestion para integrar conocimiento externo."""

    def __init__(
        self,
        sistema=None,
        habilitado: Optional[bool] = None,
        probabilidad_externa: float = 0.20,
        max_conceptos_por_ciclo: int = 5,
        umbral_relevancia: float = 0.3,
        directorios_archivos: Optional[List[str]] = None,
    ):
        # Habilitar via env var o parametro
        if habilitado is None:
            env = os.environ.get("IANAE_CONOCIMIENTO_EXTERNO", "false")
            habilitado = env.lower() in ("true", "1", "yes", "si")
        self._habilitado = habilitado
        self._probabilidad_externa = probabilidad_externa

        # Fuentes
        self.wikipedia = FuenteWikipedia()
        self.rss = FuenteRSS()
        self.web = FuenteWeb()
        self.archivos = FuenteArchivos(directorios=directorios_archivos)

        # Filtro
        self.filtro = FiltroDigestion(
            sistema=sistema,
            max_conceptos_por_ciclo=max_conceptos_por_ciclo,
            umbral_relevancia=umbral_relevancia,
        )

        self._sistema = sistema
        self._exploraciones: int = 0
        self._ultima_exploracion: float = 0.0

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------

    def explorar_externo(
        self,
        concepto: str,
        fuente: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Busca, filtra y absorbe conocimiento externo sobre un concepto."""
        if not self._habilitado:
            return {"status": "deshabilitado", "absorbidos": []}

        # Seleccionar fuente
        fuente_obj = self._seleccionar_fuente(concepto, fuente)
        if fuente_obj is None:
            return {"status": "sin_fuente_disponible", "absorbidos": []}

        # Forrajear
        try:
            resultados = fuente_obj.buscar(concepto)
        except Exception:
            logger.debug("Error buscando '%s' en %s", concepto, type(fuente_obj).__name__)
            return {"status": "error_busqueda", "absorbidos": []}

        if not resultados:
            return {"status": "sin_resultados", "absorbidos": []}

        # Digerir
        digestion = self.filtro.digerir(resultados)

        # Absorber
        absorbidos = self.filtro.absorber(digestion.get("conceptos", []))

        self._exploraciones += 1
        self._ultima_exploracion = time.time()

        return {
            "status": "ok",
            "concepto_buscado": concepto,
            "fuente": type(fuente_obj).__name__,
            "resultados_encontrados": len(resultados),
            "total_extraidos": digestion.get("total_extraidos", 0),
            "absorbidos": absorbidos,
            "rechazados": digestion.get("rechazados", 0),
        }

    def deberia_explorar_externo(self) -> bool:
        """Gate probabilistico: retorna True con probabilidad_externa %."""
        if not self._habilitado:
            return False
        import random
        return random.random() < self._probabilidad_externa

    def configurar(self, **kwargs) -> Dict[str, Any]:
        """Reconfigura en runtime."""
        if "habilitado" in kwargs:
            self._habilitado = bool(kwargs["habilitado"])
        if "probabilidad_externa" in kwargs:
            self._probabilidad_externa = float(kwargs["probabilidad_externa"])
        if "max_conceptos_por_ciclo" in kwargs:
            self.filtro.max_conceptos_por_ciclo = int(kwargs["max_conceptos_por_ciclo"])
        if "umbral_relevancia" in kwargs:
            self.filtro.umbral_relevancia = float(kwargs["umbral_relevancia"])
        return self.estado()

    def estado(self) -> Dict[str, Any]:
        """Estado completo del sistema de conocimiento externo."""
        return {
            "habilitado": self._habilitado,
            "probabilidad_externa": self._probabilidad_externa,
            "exploraciones": self._exploraciones,
            "ultima_exploracion": self._ultima_exploracion,
            "filtro": self.filtro.estado(),
            "fuentes": {
                "wikipedia": self.wikipedia.estado(),
                "rss": self.rss.estado(),
                "web": self.web.estado(),
                "archivos": self.archivos.estado(),
            },
        }

    # ------------------------------------------------------------------
    # Seleccion de fuente
    # ------------------------------------------------------------------

    def _seleccionar_fuente(
        self, concepto: str, fuente_hint: Optional[str] = None,
    ) -> Optional[FuenteExterna]:
        """Auto-selecciona fuente: archivos > rss (tech) > wikipedia > web."""
        mapa = {
            "wikipedia": self.wikipedia,
            "rss": self.rss,
            "web": self.web,
            "archivos": self.archivos,
        }

        # Si se especifica fuente
        if fuente_hint and fuente_hint in mapa:
            f = mapa[fuente_hint]
            return f if f.disponible() else None

        # Auto-seleccion
        # 1. Archivos locales primero
        if self.archivos.disponible():
            return self.archivos

        # 2. RSS para terminos tech
        tech_terms = {
            "python", "javascript", "rust", "golang", "java", "linux",
            "docker", "kubernetes", "api", "machine", "learning", "deep",
            "neural", "transformer", "llm", "cloud", "devops", "database",
            "framework", "react", "node", "web", "server", "algorithm",
            "redis", "sql", "nosql", "microservice", "data", "ai",
        }
        if any(t in concepto.lower() for t in tech_terms):
            if self.rss.disponible():
                return self.rss

        # 3. Wikipedia por defecto
        if self.wikipedia.disponible():
            return self.wikipedia

        # 4. Web como fallback
        if self.web.disponible():
            return self.web

        return None
