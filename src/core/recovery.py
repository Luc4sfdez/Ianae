"""
Modulo de recovery para IANAE.

Funcionalidades:
- Graceful shutdown con guardado automatico de estado
- Auto-recovery desde ultimo snapshot al iniciar
- Health diagnostics del sistema
- Watchdog de integridad
"""
import logging
import signal
import time
import os
import json
from typing import Optional, Dict, List, Callable

logger = logging.getLogger(__name__)


class RecoveryManager:
    """
    Gestiona shutdown seguro y recovery automatico del sistema IANAE.
    """

    def __init__(self, sistema, snapshot_dir: str = "data/snapshots",
                 auto_save_interval: int = 300):
        """
        Args:
            sistema: instancia de ConceptosLucas
            snapshot_dir: directorio para snapshots de recovery
            auto_save_interval: segundos entre auto-saves (0 = desactivado)
        """
        self.sistema = sistema
        self.snapshot_dir = snapshot_dir
        self.auto_save_interval = auto_save_interval
        self._shutdown_requested = False
        self._last_save_time = 0.0
        self._save_count = 0
        self._recovery_log: List[Dict] = []
        self._signal_handlers_installed = False

    def instalar_signal_handlers(self):
        """Instala handlers para SIGINT/SIGTERM que hacen graceful shutdown."""
        if self._signal_handlers_installed:
            return

        def _handler(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Senal %s recibida, iniciando shutdown seguro...", sig_name)
            self._shutdown_requested = True
            self.guardar_snapshot("shutdown")

        try:
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)
            self._signal_handlers_installed = True
            logger.info("Signal handlers instalados para graceful shutdown")
        except (OSError, ValueError) as e:
            logger.warning("No se pudieron instalar signal handlers: %s", e)

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def guardar_snapshot(self, motivo: str = "manual") -> Optional[str]:
        """
        Guarda snapshot del estado actual del sistema.

        Args:
            motivo: razon del snapshot (manual, auto, shutdown, pre_consolidacion)

        Returns:
            Ruta del archivo guardado o None si fallo
        """
        try:
            os.makedirs(self.snapshot_dir, exist_ok=True)

            timestamp = int(time.time())
            nombre = f"snapshot_{motivo}_{timestamp}.json"
            ruta = os.path.join(self.snapshot_dir, nombre)

            estado = self._serializar_estado()
            estado["_meta"] = {
                "motivo": motivo,
                "timestamp": timestamp,
                "num_conceptos": len(self.sistema.conceptos),
                "metricas": dict(self.sistema.metricas),
            }

            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)

            self._last_save_time = time.time()
            self._save_count += 1
            self._recovery_log.append({
                "accion": "snapshot_guardado",
                "ruta": ruta,
                "motivo": motivo,
                "timestamp": timestamp,
            })

            logger.info("Snapshot guardado: %s (%d conceptos)", ruta,
                        len(self.sistema.conceptos))
            return ruta

        except Exception as e:
            logger.error("Error guardando snapshot: %s", e)
            return None

    @staticmethod
    def _to_serializable(obj):
        """Convierte recursivamente objetos numpy a tipos nativos Python."""
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): RecoveryManager._to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [RecoveryManager._to_serializable(i) for i in obj]
        return obj

    def _serializar_estado(self) -> Dict:
        """Serializa el estado del sistema a dict JSON-compatible."""
        conceptos_serial = {}
        for nombre, data in self.sistema.conceptos.items():
            conceptos_serial[nombre] = self._to_serializable(dict(data))

        relaciones_serial = {}
        for k, v in self.sistema.relaciones.items():
            relaciones_serial[str(k)] = self._to_serializable(v)

        categorias = {}
        for k, v in getattr(self.sistema, "categorias", {}).items():
            categorias[str(k)] = self._to_serializable(v)

        return {
            "conceptos": conceptos_serial,
            "relaciones": relaciones_serial,
            "categorias": categorias,
        }

    def restaurar_snapshot(self, ruta: Optional[str] = None) -> bool:
        """
        Restaura el sistema desde un snapshot.

        Args:
            ruta: ruta al snapshot. Si None, usa el mas reciente.

        Returns:
            True si se restauro correctamente
        """
        import numpy as np

        if ruta is None:
            ruta = self._encontrar_ultimo_snapshot()
            if ruta is None:
                logger.info("No hay snapshots disponibles para restaurar")
                return False

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                estado = json.load(f)

            conceptos_cargados = 0
            for nombre, data in estado.get("conceptos", {}).items():
                if nombre in self.sistema.conceptos:
                    # Restaurar vectores
                    for campo in ("actual", "base"):
                        if campo in data and isinstance(data[campo], list):
                            self.sistema.conceptos[nombre][campo] = np.array(data[campo])
                    # Restaurar escalares
                    for campo in ("fuerza", "activaciones", "categoria"):
                        if campo in data:
                            self.sistema.conceptos[nombre][campo] = data[campo]
                    conceptos_cargados += 1

            meta = estado.get("_meta", {})
            self._recovery_log.append({
                "accion": "snapshot_restaurado",
                "ruta": ruta,
                "conceptos_restaurados": conceptos_cargados,
                "timestamp": int(time.time()),
                "motivo_original": meta.get("motivo", "desconocido"),
            })

            logger.info("Snapshot restaurado: %s (%d conceptos)", ruta, conceptos_cargados)
            return conceptos_cargados > 0

        except Exception as e:
            logger.error("Error restaurando snapshot %s: %s", ruta, e)
            return False

    def _encontrar_ultimo_snapshot(self) -> Optional[str]:
        """Encuentra el snapshot mas reciente en el directorio."""
        if not os.path.isdir(self.snapshot_dir):
            return None

        snapshots = []
        for f in os.listdir(self.snapshot_dir):
            if f.startswith("snapshot_") and f.endswith(".json"):
                ruta = os.path.join(self.snapshot_dir, f)
                snapshots.append((os.path.getmtime(ruta), ruta))

        if not snapshots:
            return None

        snapshots.sort(reverse=True)
        return snapshots[0][1]

    def listar_snapshots(self) -> List[Dict]:
        """Lista todos los snapshots disponibles."""
        if not os.path.isdir(self.snapshot_dir):
            return []

        resultado = []
        for f in os.listdir(self.snapshot_dir):
            if f.startswith("snapshot_") and f.endswith(".json"):
                ruta = os.path.join(self.snapshot_dir, f)
                try:
                    with open(ruta, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    meta = data.get("_meta", {})
                    resultado.append({
                        "archivo": f,
                        "ruta": ruta,
                        "motivo": meta.get("motivo", "desconocido"),
                        "timestamp": meta.get("timestamp", 0),
                        "num_conceptos": meta.get("num_conceptos", 0),
                    })
                except Exception:
                    resultado.append({"archivo": f, "ruta": ruta, "error": True})

        resultado.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return resultado

    def check_auto_save(self) -> Optional[str]:
        """
        Verifica si es momento de auto-guardar. Llamar periodicamente.

        Returns:
            Ruta del snapshot si se guardo, None si no era necesario
        """
        if self.auto_save_interval <= 0:
            return None

        ahora = time.time()
        if ahora - self._last_save_time >= self.auto_save_interval:
            return self.guardar_snapshot("auto")
        return None

    def limpiar_snapshots(self, mantener: int = 10) -> int:
        """
        Elimina snapshots antiguos, manteniendo los N mas recientes.

        Returns:
            Numero de snapshots eliminados
        """
        snapshots = self.listar_snapshots()
        if len(snapshots) <= mantener:
            return 0

        eliminados = 0
        for snap in snapshots[mantener:]:
            ruta = snap.get("ruta")
            if ruta and os.path.exists(ruta):
                try:
                    os.remove(ruta)
                    eliminados += 1
                except OSError as e:
                    logger.warning("Error eliminando snapshot %s: %s", ruta, e)

        if eliminados:
            logger.info("Snapshots limpiados: %d eliminados, %d mantenidos",
                        eliminados, mantener)
        return eliminados

    def diagnostico(self) -> Dict:
        """
        Ejecuta diagnostico completo del sistema.

        Returns:
            Dict con estado de salud del sistema
        """
        diag = {
            "estado": "ok",
            "problemas": [],
            "conceptos_total": len(self.sistema.conceptos),
            "snapshots_disponibles": len(self.listar_snapshots()),
            "ultimo_save": self._last_save_time,
            "saves_totales": self._save_count,
            "shutdown_pendiente": self._shutdown_requested,
        }

        # Check: sistema tiene conceptos
        if len(self.sistema.conceptos) == 0:
            diag["problemas"].append("Sin conceptos cargados")
            diag["estado"] = "warning"

        # Check: conceptos con fuerza muy baja
        debiles = 0
        for nombre, data in self.sistema.conceptos.items():
            if data.get("fuerza", 1.0) < 0.1:
                debiles += 1
        if debiles > 0:
            diag["conceptos_debiles"] = debiles
            if debiles > len(self.sistema.conceptos) * 0.5:
                diag["problemas"].append(
                    f"{debiles} conceptos con fuerza < 0.1 (>50%)")
                diag["estado"] = "warning"

        # Check: vectores con NaN
        nan_count = 0
        for nombre, data in self.sistema.conceptos.items():
            vec = data.get("actual")
            if vec is not None and hasattr(vec, "__len__"):
                import numpy as np
                if np.any(np.isnan(vec)):
                    nan_count += 1
        if nan_count > 0:
            diag["vectores_nan"] = nan_count
            diag["problemas"].append(f"{nan_count} vectores contienen NaN")
            diag["estado"] = "error"

        # Check: metricas del sistema
        metricas = getattr(self.sistema, "metricas", {})
        diag["edad_sistema"] = metricas.get("edad", 0)
        diag["ciclos_pensamiento"] = metricas.get("ciclos_pensamiento", 0)

        return diag

    @property
    def recovery_log(self) -> List[Dict]:
        """Historial de operaciones de recovery."""
        return list(self._recovery_log)
