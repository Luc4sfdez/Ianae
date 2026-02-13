"""
Introspeccion — Fase 14: IANAE se Mira a Si Misma.

Usa ast.parse() para entender su propia estructura de codigo
(clases, metodos, imports, dependencias) y construye un mapa
interno que alimenta consciencia, dialogo y curiosidad.

Sin dependencias externas — solo ast (stdlib).
"""
import ast
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ======================================================================
# ExtractorCodigo — analisis AST de archivos Python
# ======================================================================


class ExtractorCodigo:
    """Analiza archivos .py con ast.parse() y extrae estructura."""

    @staticmethod
    def extraer_modulo(ruta_archivo: str) -> Optional[Dict[str, Any]]:
        """Parsea un .py y retorna estructura: clases, funciones, imports, docstring."""
        try:
            with open(ruta_archivo, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except (OSError, IOError):
            return None

        try:
            tree = ast.parse(source, filename=ruta_archivo)
        except SyntaxError:
            logger.debug("SyntaxError parseando %s", ruta_archivo)
            return None

        clases: List[Dict[str, Any]] = []
        funciones: List[str] = []
        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                metodos = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                docstring = ast.get_docstring(node) or ""
                clases.append({
                    "nombre": node.name,
                    "metodos": metodos,
                    "docstring": docstring[:200],
                    "lineas": node.end_lineno - node.lineno + 1
                    if hasattr(node, "end_lineno") and node.end_lineno
                    else len(metodos) + 1,
                })

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Solo top-level (no metodos de clase)
                if isinstance(node, ast.FunctionDef) and _is_top_level(tree, node):
                    funciones.append(node.name)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                modulo = node.module or ""
                imports.append(modulo)

        lineas = source.count("\n") + 1
        docstring_modulo = ast.get_docstring(tree) or ""

        return {
            "ruta": ruta_archivo,
            "nombre": os.path.splitext(os.path.basename(ruta_archivo))[0],
            "clases": clases,
            "funciones": funciones,
            "imports": imports,
            "docstring": docstring_modulo[:300],
            "lineas": lineas,
        }

    @staticmethod
    def extraer_directorio(ruta: str) -> List[Dict[str, Any]]:
        """Escanea recursivamente un directorio y extrae todos los .py."""
        modulos: List[Dict[str, Any]] = []
        if not os.path.isdir(ruta):
            return modulos

        for root, _dirs, files in os.walk(ruta):
            # Saltar __pycache__ y directorios ocultos
            if "__pycache__" in root or os.path.basename(root).startswith("."):
                continue
            for fname in sorted(files):
                if not fname.endswith(".py"):
                    continue
                ruta_archivo = os.path.join(root, fname)
                modulo = ExtractorCodigo.extraer_modulo(ruta_archivo)
                if modulo is not None:
                    modulos.append(modulo)
        return modulos


def _is_top_level(tree: ast.Module, node: ast.FunctionDef) -> bool:
    """Verifica si un FunctionDef es top-level (no metodo de clase)."""
    for top_node in tree.body:
        if top_node is node:
            return True
    return False


# ======================================================================
# MapaInterno — cache de autoconocimiento
# ======================================================================


class MapaInterno:
    """Mapa estructural interno de IANAE — se conoce a si misma."""

    def __init__(self, sistema=None, directorio_src: Optional[str] = None):
        self.sistema = sistema
        self._directorio_src = directorio_src or self._detectar_src()
        self._cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 300.0  # 5 minutos
        self._inyectado: bool = False

    def _detectar_src(self) -> str:
        """Detecta el directorio src/ relativo a este archivo."""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ------------------------------------------------------------------
    # Construir / cache
    # ------------------------------------------------------------------

    def construir(self) -> List[Dict[str, Any]]:
        """Construye o retorna el mapa interno (con cache TTL)."""
        ahora = time.time()
        if self._cache is not None and (ahora - self._cache_timestamp) < self._cache_ttl:
            return self._cache

        modulos = ExtractorCodigo.extraer_directorio(self._directorio_src)
        self._cache = modulos
        self._cache_timestamp = ahora

        # Inyectar autoconocimiento al grafo (una vez por construir)
        if not self._inyectado and self.sistema is not None:
            self.inyectar_autoconocimiento()
            self._inyectado = True

        return modulos

    def invalidar_cache(self) -> None:
        """Fuerza reconstruccion en el proximo acceso."""
        self._cache = None
        self._cache_timestamp = 0.0

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def quien_soy(self) -> str:
        """Narrativa de autoconocimiento estructural."""
        modulos = self.construir()
        if not modulos:
            return "Soy IANAE, pero aun no puedo analizar mi propia estructura."

        total_clases = sum(len(m.get("clases", [])) for m in modulos)
        total_metodos = sum(
            sum(len(c.get("metodos", [])) for c in m.get("clases", []))
            for m in modulos
        )
        total_lineas = sum(m.get("lineas", 0) for m in modulos)
        total_funciones = sum(len(m.get("funciones", [])) for m in modulos)

        # Extraer nombres de modulos core
        core_modulos = [
            m["nombre"] for m in modulos
            if "core" in m.get("ruta", "").replace("\\", "/")
            and m["nombre"] != "__init__"
        ]

        partes = [
            f"Soy IANAE, un organismo digital compuesto por {len(modulos)} modulos, "
            f"{total_clases} clases, {total_metodos} metodos y "
            f"{total_funciones} funciones, en {total_lineas:,} lineas de codigo.",
        ]

        if core_modulos:
            partes.append(
                f"Mi nucleo esta formado por: {', '.join(core_modulos[:8])}."
            )

        # Capacidades desde clases principales
        clases_principales = []
        for m in modulos:
            for c in m.get("clases", []):
                if c.get("docstring"):
                    clases_principales.append(c)

        if clases_principales:
            caps = [c["nombre"] for c in clases_principales[:5]]
            partes.append(
                f"Mis capacidades incluyen: {', '.join(caps)}."
            )

        return " ".join(partes)

    def que_puedo_hacer(self) -> List[str]:
        """Lista de capacidades extraidas de clases y docstrings."""
        modulos = self.construir()
        capacidades: List[str] = []

        for m in modulos:
            for clase in m.get("clases", []):
                nombre = clase["nombre"]
                doc = clase.get("docstring", "")
                if doc:
                    capacidades.append(f"{nombre}: {doc[:100]}")
                else:
                    metodos_pub = [
                        met for met in clase.get("metodos", [])
                        if not met.startswith("_")
                    ]
                    if metodos_pub:
                        capacidades.append(
                            f"{nombre}: {', '.join(metodos_pub[:5])}"
                        )
        return capacidades

    def modulos(self) -> List[Dict[str, Any]]:
        """Retorna todos los modulos con su estructura."""
        return self.construir()

    def buscar_en_codigo(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca clases/metodos/funciones por nombre."""
        modulos = self.construir()
        consulta_lower = consulta.lower()
        resultados: List[Dict[str, Any]] = []

        for m in modulos:
            # Buscar en nombre de modulo
            if consulta_lower in m["nombre"].lower():
                resultados.append({
                    "tipo": "modulo",
                    "nombre": m["nombre"],
                    "ruta": m.get("ruta", ""),
                    "docstring": m.get("docstring", "")[:200],
                })

            # Buscar en clases
            for clase in m.get("clases", []):
                if consulta_lower in clase["nombre"].lower():
                    resultados.append({
                        "tipo": "clase",
                        "nombre": clase["nombre"],
                        "modulo": m["nombre"],
                        "metodos": clase.get("metodos", []),
                        "docstring": clase.get("docstring", "")[:200],
                    })

                # Buscar en metodos
                for metodo in clase.get("metodos", []):
                    if consulta_lower in metodo.lower():
                        resultados.append({
                            "tipo": "metodo",
                            "nombre": metodo,
                            "clase": clase["nombre"],
                            "modulo": m["nombre"],
                        })

            # Buscar en funciones top-level
            for func in m.get("funciones", []):
                if consulta_lower in func.lower():
                    resultados.append({
                        "tipo": "funcion",
                        "nombre": func,
                        "modulo": m["nombre"],
                    })

        return resultados

    def complejidad(self) -> Dict[str, Any]:
        """Metricas de complejidad del codigo."""
        modulos = self.construir()

        total_lineas = sum(m.get("lineas", 0) for m in modulos)
        total_clases = sum(len(m.get("clases", [])) for m in modulos)
        total_metodos = sum(
            sum(len(c.get("metodos", [])) for c in m.get("clases", []))
            for m in modulos
        )
        total_funciones = sum(len(m.get("funciones", [])) for m in modulos)

        # Dependencias (imports entre modulos propios)
        dependencias: Dict[str, List[str]] = {}
        nombres_modulos = {m["nombre"] for m in modulos}
        for m in modulos:
            deps = []
            for imp in m.get("imports", []):
                # Extraer el nombre del modulo importado
                parts = imp.split(".")
                for part in parts:
                    if part in nombres_modulos and part != m["nombre"]:
                        deps.append(part)
                        break
            dependencias[m["nombre"]] = list(set(deps))

        return {
            "modulos": len(modulos),
            "clases": total_clases,
            "metodos": total_metodos,
            "funciones": total_funciones,
            "lineas": total_lineas,
            "dependencias": dependencias,
        }

    # ------------------------------------------------------------------
    # Inyeccion de autoconocimiento al grafo
    # ------------------------------------------------------------------

    def inyectar_autoconocimiento(self) -> int:
        """Crea conceptos en el grafo para cada modulo core. Retorna cantidad creados."""
        if self.sistema is None:
            return 0

        modulos = self._cache or self.construir()
        creados = 0

        # Solo modulos core (no tests, no __init__)
        core = [
            m for m in modulos
            if "core" in m.get("ruta", "").replace("\\", "/")
            and m["nombre"] != "__init__"
        ]

        for m in core:
            nombre_concepto = f"mod_{m['nombre']}"

            if nombre_concepto not in self.sistema.conceptos:
                try:
                    self.sistema.añadir_concepto(
                        nombre_concepto,
                        incertidumbre=0.1,
                        categoria="autoconocimiento",
                    )
                    creados += 1
                except Exception:
                    logger.debug("Error inyectando concepto '%s'", nombre_concepto)
                    continue

        # Crear relaciones basadas en imports
        for m in core:
            nombre_concepto = f"mod_{m['nombre']}"
            if nombre_concepto not in self.sistema.conceptos:
                continue

            for imp in m.get("imports", []):
                parts = imp.split(".")
                for part in parts:
                    target = f"mod_{part}"
                    if target != nombre_concepto and target in self.sistema.conceptos:
                        try:
                            self.sistema.relacionar(nombre_concepto, target, fuerza=0.8)
                        except Exception:
                            pass

        return creados
