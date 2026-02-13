"""
Motor de Evolucion de IANAE — Fase 8: IANAE Evoluciona.

Auto-ajuste de parametros basado en consciencia, persistencia del estado
completo entre reinicios, y percepcion del entorno (vigilancia de
directorio para auto-ingesta).

IANAE deja de ser estatica: se adapta, recuerda y percibe.
"""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Rangos seguros para auto-tuning
LIMITES = {
    "intervalo_base": (0.5, 30.0),
    "temperatura_exploracion": (0.01, 0.5),
    "umbral_convergencia": (0.01, 0.2),
    "max_ciclos_pensamiento": (2, 10),
}


class MotorEvolucion:
    """Auto-evolucion, persistencia perpetua y percepcion del entorno."""

    def __init__(
        self,
        organismo,
        estado_path: str = "data/estado_ianae.json",
        historial_path: str = "data/evolucion_historial.jsonl",
        percepcion_dir: Optional[str] = None,
    ):
        self.organismo = organismo
        self.estado_path = estado_path
        self.historial_path = historial_path
        self.percepcion_dir = percepcion_dir
        self._archivos_vistos: set = set()
        self._historial_parametros: List[Dict] = []
        self._generacion: int = 0

    # ==================================================================
    # AUTO-EVOLUCION — ajusta parametros segun consciencia
    # ==================================================================

    def evolucionar(self) -> Dict[str, Any]:
        """Evalua consciencia y ajusta parametros del organismo."""
        consciencia = self.organismo.consciencia
        cambios: Dict[str, Any] = {}

        # Leer diagnosticos
        pulso = consciencia.pulso()
        crecimiento = consciencia.medir_crecimiento()
        sesgos = consciencia.detectar_sesgos()
        superficie = consciencia.superficie()

        # 1. Intervalo base: si aburrida, acelerar; si inspirada, mantener
        intervalo_actual = self.organismo.vida.intervalo_base
        if pulso["estado"] == "aburrida":
            nuevo_intervalo = max(LIMITES["intervalo_base"][0],
                                  intervalo_actual * 0.8)
            if nuevo_intervalo != intervalo_actual:
                self.organismo.vida.intervalo_base = nuevo_intervalo
                cambios["intervalo_base"] = {
                    "antes": intervalo_actual, "despues": nuevo_intervalo,
                    "razon": "aburrida → acelerar",
                }
        elif pulso["estado"] == "inspirada" and crecimiento["tendencia"] == "creciendo":
            # Mantener ritmo — no cambiar
            pass
        elif crecimiento["tendencia"] == "decayendo":
            nuevo_intervalo = max(LIMITES["intervalo_base"][0],
                                  intervalo_actual * 0.9)
            if nuevo_intervalo != intervalo_actual:
                self.organismo.vida.intervalo_base = nuevo_intervalo
                cambios["intervalo_base"] = {
                    "antes": intervalo_actual, "despues": nuevo_intervalo,
                    "razon": "decayendo → acelerar ligeramente",
                }

        # 2. Estancamiento: si muchos rutinarios, forzar serendipia
        estancada = any(s["tipo"] == "estancamiento" for s in sesgos)
        if estancada:
            ajustes = self.organismo.vida._ajustes_curiosidad
            ajustes["serendipia"] = ajustes.get("serendipia", 1.0) * 1.5
            ajustes["prediccion"] = ajustes.get("prediccion", 1.0) * 1.3
            cambios["curiosidad_boost"] = {
                "serendipia": ajustes["serendipia"],
                "prediccion": ajustes["prediccion"],
                "razon": "estancamiento detectado",
            }

        # 3. Superficie baja: reducir genesis agresividad (consolidar lo que hay)
        if superficie < 0.2:
            cambios["superficie_baja"] = {
                "accion": "consolidar",
                "superficie": superficie,
                "razon": "porosa baja, consolidando conocimiento",
            }

        # 4. Registrar generacion
        self._generacion += 1
        entrada = {
            "generacion": self._generacion,
            "timestamp": time.time(),
            "pulso": pulso["estado"],
            "energia": pulso["energia"],
            "tendencia": crecimiento["tendencia"],
            "superficie": superficie,
            "sesgos": len(sesgos),
            "cambios": cambios,
        }
        self._historial_parametros.append(entrada)
        self._registrar_historial(entrada)

        return entrada

    def historial_evolucion(self, ultimos: int = 10) -> List[Dict]:
        """Ultimas N generaciones de evolucion."""
        return self._historial_parametros[-ultimos:]

    def _registrar_historial(self, entrada: Dict) -> None:
        directorio = os.path.dirname(self.historial_path)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)
        with open(self.historial_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False, default=str) + "\n")

    # ==================================================================
    # PERSISTENCIA PERPETUA — recuerda entre reinicios
    # ==================================================================

    def guardar_estado(self) -> str:
        """Persiste el estado completo del organismo."""
        estado = {
            "version": 1,
            "timestamp": time.time(),
            "generacion": self._generacion,
            "ciclo_actual": self.organismo.vida._ciclo_actual,
            "intervalo_base": self.organismo.vida.intervalo_base,
            "ajustes_curiosidad": self.organismo.vida._ajustes_curiosidad,
            "objetivos": self.organismo.consciencia.leer_objetivos(),
            "suenos_prometedores": len(
                self.organismo.suenos.suenos_prometedores()
            ),
            "conceptos_total": len(self.organismo.sistema.conceptos),
            "relaciones_total": self.organismo.sistema.grafo.number_of_edges(),
            "archivos_vistos": list(self._archivos_vistos),
        }

        directorio = os.path.dirname(self.estado_path)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)
        with open(self.estado_path, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2, default=str)

        logger.info("Estado guardado: gen=%d ciclo=%d",
                     self._generacion, estado["ciclo_actual"])
        return self.estado_path

    def cargar_estado(self) -> Optional[Dict]:
        """Carga estado previo si existe."""
        if not os.path.exists(self.estado_path):
            return None

        try:
            with open(self.estado_path, "r", encoding="utf-8") as f:
                estado = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

        # Restaurar parametros
        self._generacion = estado.get("generacion", 0)
        self.organismo.vida._ciclo_actual = estado.get("ciclo_actual", 0)

        intervalo = estado.get("intervalo_base")
        if intervalo is not None:
            lo, hi = LIMITES["intervalo_base"]
            self.organismo.vida.intervalo_base = max(lo, min(hi, intervalo))

        ajustes = estado.get("ajustes_curiosidad", {})
        if ajustes:
            self.organismo.vida._ajustes_curiosidad = ajustes

        self._archivos_vistos = set(estado.get("archivos_vistos", []))

        logger.info("Estado cargado: gen=%d ciclo=%d",
                     self._generacion, estado.get("ciclo_actual", 0))
        return estado

    # ==================================================================
    # PERCEPCION — vigila directorio, auto-ingesta
    # ==================================================================

    def percibir(self) -> List[Dict[str, Any]]:
        """Escanea directorio de percepcion y procesa archivos nuevos."""
        if not self.percepcion_dir or not os.path.isdir(self.percepcion_dir):
            return []

        extensiones = {".txt", ".md"}
        nuevos: List[Dict[str, Any]] = []

        for nombre in os.listdir(self.percepcion_dir):
            ruta = os.path.join(self.percepcion_dir, nombre)
            if not os.path.isfile(ruta):
                continue
            _, ext = os.path.splitext(nombre)
            if ext.lower() not in extensiones:
                continue
            if ruta in self._archivos_vistos:
                continue

            # Nuevo archivo detectado
            self._archivos_vistos.add(ruta)
            resultado = self._ingestar_archivo(ruta)
            nuevos.append(resultado)

        return nuevos

    def _ingestar_archivo(self, ruta: str) -> Dict[str, Any]:
        """Lee archivo y extrae conceptos al sistema."""
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read(10000)  # Max 10KB
        except IOError:
            return {"archivo": ruta, "error": "No se pudo leer", "conceptos": 0}

        # Extraer palabras clave como conceptos simples
        conceptos_nuevos = 0
        palabras = set()
        for linea in contenido.split("\n"):
            for palabra in linea.split():
                limpia = palabra.strip(".,;:!?()[]{}\"'").strip()
                if len(limpia) > 3 and limpia.isalpha() and limpia[0].isupper():
                    palabras.add(limpia)

        # Agregar al sistema si no existen
        for palabra in list(palabras)[:10]:  # Max 10 conceptos por archivo
            if palabra not in self.organismo.sistema.conceptos:
                try:
                    self.organismo.sistema.añadir_concepto(
                        palabra, categoria="percibidos"
                    )
                    conceptos_nuevos += 1
                except Exception:
                    pass

        # Activar conceptos nuevos para que entren en curiosidad
        for palabra in list(palabras)[:3]:
            if palabra in self.organismo.sistema.conceptos:
                try:
                    self.organismo.sistema.activar(palabra, pasos=1)
                except Exception:
                    pass

        return {
            "archivo": os.path.basename(ruta),
            "conceptos": conceptos_nuevos,
            "palabras_detectadas": len(palabras),
        }

    def archivos_percibidos(self) -> List[str]:
        """Lista de archivos ya procesados."""
        return sorted(self._archivos_vistos)

    # ==================================================================
    # CICLO EVOLUTIVO — todo junto
    # ==================================================================

    def ciclo_evolutivo(self) -> Dict[str, Any]:
        """Un ciclo completo de evolucion: percibir → evolucionar → guardar."""
        ts = time.time()

        # 1. Percibir entorno
        percepciones = self.percibir()

        # 2. Evolucionar parametros
        evolucion = self.evolucionar()

        # 3. Guardar estado
        self.guardar_estado()

        return {
            "timestamp": ts,
            "percepciones": percepciones,
            "evolucion": evolucion,
            "generacion": self._generacion,
        }
