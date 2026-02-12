"""
Ingesta continua: monitorea directorio para auto-procesar archivos nuevos.

Cada .txt o .md nuevo pasa por el pipeline NLP y se inyecta en la red IANAE.
Deduplicacion automatica — no repite conceptos ya existentes.
"""
import os
import time
import logging
from typing import Dict, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class IngestaContinua:
    """
    Monitorea un directorio y procesa automaticamente archivos nuevos
    via pipeline NLP -> red IANAE.
    """

    EXTENSIONES = {".txt", ".md"}

    def __init__(self, directorio: str, sistema, pipeline=None,
                 categoria: str = "ingesta_auto",
                 max_conceptos: int = 10,
                 on_ingesta: Optional[Callable] = None):
        """
        Args:
            directorio: ruta al directorio a monitorear
            sistema: instancia de ConceptosLucas
            pipeline: instancia de PipelineNLP (o None para crear)
            categoria: categoria para conceptos nuevos
            max_conceptos: max conceptos por archivo
            on_ingesta: callback tras cada ingesta (recibe dict con metricas)
        """
        self.directorio = Path(directorio)
        self.sistema = sistema
        self.categoria = categoria
        self.max_conceptos = max_conceptos
        self.on_ingesta = on_ingesta

        # Pipeline NLP (lazy)
        self._pipeline = pipeline

        # Tracking
        self._archivos_procesados = set()
        self._log_ingesta: List[Dict] = []
        self._running = False

    @property
    def pipeline(self):
        if self._pipeline is None:
            try:
                from src.nlp.pipeline import PipelineNLP
                self._pipeline = PipelineNLP(
                    sistema_ianae=self.sistema,
                    modo_nlp="auto"
                )
            except ImportError:
                raise RuntimeError("PipelineNLP no disponible — instalar dependencias NLP")
        return self._pipeline

    def escanear_nuevos(self) -> List[Path]:
        """Retorna archivos nuevos no procesados en el directorio."""
        if not self.directorio.exists():
            return []

        nuevos = []
        for archivo in self.directorio.iterdir():
            if (archivo.is_file()
                    and archivo.suffix.lower() in self.EXTENSIONES
                    and str(archivo) not in self._archivos_procesados):
                nuevos.append(archivo)

        nuevos.sort(key=lambda p: p.stat().st_mtime)
        return nuevos

    def procesar_archivo(self, ruta: Path) -> Dict:
        """
        Procesa un archivo individual: lee texto, extrae conceptos, inyecta.

        Returns:
            Dict con metricas de la ingesta
        """
        ruta = Path(ruta)
        t_inicio = time.time()

        try:
            texto = ruta.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.error("Error leyendo %s: %s", ruta, e)
            return {"archivo": str(ruta), "error": str(e), "conceptos_nuevos": 0}

        if not texto.strip():
            return {"archivo": str(ruta), "error": "vacio", "conceptos_nuevos": 0}

        # Conceptos antes de inyectar
        conceptos_antes = set(self.sistema.conceptos.keys())

        # Procesar con pipeline
        if len(texto.split()) > 200:
            resultado = self.pipeline.procesar_largo(
                texto, max_conceptos=self.max_conceptos,
                categoria=self.categoria
            )
        else:
            resultado = self.pipeline.procesar(
                texto, max_conceptos=self.max_conceptos,
                categoria=self.categoria
            )

        # Deduplicacion: contar solo conceptos realmente nuevos
        conceptos_despues = set(self.sistema.conceptos.keys())
        conceptos_nuevos = conceptos_despues - conceptos_antes

        t_total = time.time() - t_inicio

        metricas = {
            "archivo": str(ruta),
            "tamano_bytes": ruta.stat().st_size,
            "palabras": len(texto.split()),
            "conceptos_extraidos": len(resultado.get("conceptos", [])),
            "conceptos_nuevos": len(conceptos_nuevos),
            "conceptos_nombres": list(conceptos_nuevos),
            "relaciones": len(resultado.get("relaciones", [])),
            "modo_nlp": resultado.get("modo", "basico"),
            "chunks": resultado.get("chunks", 1),
            "tiempo_s": round(t_total, 3),
            "timestamp": time.time(),
        }

        self._archivos_procesados.add(str(ruta))
        self._log_ingesta.append(metricas)

        logger.info("Ingesta: %s -> %d conceptos nuevos en %.2fs",
                     ruta.name, len(conceptos_nuevos), t_total)

        if self.on_ingesta:
            self.on_ingesta(metricas)

        return metricas

    def procesar_pendientes(self) -> List[Dict]:
        """Procesa todos los archivos nuevos pendientes."""
        nuevos = self.escanear_nuevos()
        resultados = []
        for archivo in nuevos:
            resultado = self.procesar_archivo(archivo)
            resultados.append(resultado)
        return resultados

    def iniciar_watcher(self, intervalo: float = 5.0):
        """
        Inicia el watcher con watchdog (polling).

        Args:
            intervalo: segundos entre escaneos
        """
        try:
            from watchdog.observers.polling import PollingObserver
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            raise RuntimeError("watchdog no instalado: pip install watchdog")

        ingesta = self

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if event.is_directory:
                    return
                ruta = Path(event.src_path)
                if ruta.suffix.lower() in IngestaContinua.EXTENSIONES:
                    # Esperar a que el archivo termine de escribirse
                    time.sleep(0.5)
                    ingesta.procesar_archivo(ruta)

        self.directorio.mkdir(parents=True, exist_ok=True)
        observer = PollingObserver(timeout=intervalo)
        observer.schedule(Handler(), str(self.directorio), recursive=False)

        self._running = True
        observer.start()
        logger.info("Watcher iniciado en %s (intervalo=%.1fs)", self.directorio, intervalo)

        return observer

    def detener_watcher(self, observer):
        """Detiene el watcher."""
        self._running = False
        observer.stop()
        observer.join(timeout=5)
        logger.info("Watcher detenido")

    # --- Metricas ---

    def estadisticas(self) -> Dict:
        """Retorna estadisticas de ingesta."""
        if not self._log_ingesta:
            return {
                "archivos_procesados": 0,
                "conceptos_totales_nuevos": 0,
                "palabras_totales": 0,
                "tiempo_total_s": 0,
            }

        return {
            "archivos_procesados": len(self._log_ingesta),
            "conceptos_totales_nuevos": sum(l["conceptos_nuevos"] for l in self._log_ingesta),
            "palabras_totales": sum(l["palabras"] for l in self._log_ingesta),
            "tiempo_total_s": round(sum(l["tiempo_s"] for l in self._log_ingesta), 3),
            "archivos_con_error": sum(1 for l in self._log_ingesta if "error" in l),
            "ultimo_procesado": self._log_ingesta[-1]["archivo"],
        }

    @property
    def log(self) -> List[Dict]:
        """Log completo de ingestas."""
        return list(self._log_ingesta)

    def marcar_procesado(self, ruta: str):
        """Marca un archivo como ya procesado (para skip)."""
        self._archivos_procesados.add(ruta)
