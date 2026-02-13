"""Tests para MotorEvolucion — auto-evolucion, persistencia, percepcion."""
import json
import os

import pytest

from src.core.nucleo import ConceptosLucas
from src.core.organismo import IANAE
from src.core.evolucion import MotorEvolucion, LIMITES


# ==================== Fixtures ====================


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("OpenCV", categoria="tecnologias")
    s.añadir_concepto("Docker", categoria="tecnologias")
    s.añadir_concepto("Tacografos", categoria="proyectos")
    s.añadir_concepto("RAG_System", categoria="proyectos")
    s.añadir_concepto("Lucas", categoria="lucas_personal")
    s.añadir_concepto("IANAE", categoria="conceptos_ianae")
    s.añadir_concepto("Automatizacion", categoria="herramientas")

    s.relacionar("Python", "OpenCV", fuerza=0.9)
    s.relacionar("Python", "Tacografos", fuerza=0.85)
    s.relacionar("OpenCV", "Tacografos", fuerza=0.95)
    s.relacionar("Python", "RAG_System", fuerza=0.8)
    s.relacionar("RAG_System", "IANAE", fuerza=0.9)
    s.relacionar("Lucas", "Python", fuerza=0.95)
    s.relacionar("Lucas", "IANAE", fuerza=0.9)
    s.relacionar("Docker", "RAG_System", fuerza=0.7)
    s.relacionar("Automatizacion", "Python", fuerza=0.85)

    for _ in range(5):
        s.activar("Python", pasos=2, temperatura=0.1)
        s.activar("Tacografos", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def ianae(sistema, tmp_path):
    return IANAE.desde_componentes(
        sistema,
        diario_path=str(tmp_path / "diario.jsonl"),
        objetivos_path=str(tmp_path / "obj.json"),
        conversaciones_path=str(tmp_path / "conv.jsonl"),
        snapshot_dir=str(tmp_path / "snap"),
        intervalo_base=0.01,
    )


@pytest.fixture
def motor(ianae, tmp_path):
    return MotorEvolucion(
        ianae,
        estado_path=str(tmp_path / "estado.json"),
        historial_path=str(tmp_path / "historial.jsonl"),
        percepcion_dir=str(tmp_path / "percepcion"),
    )


@pytest.fixture
def motor_con_ciclos(motor):
    """Motor con datos de diario para que consciencia tenga informacion."""
    for _ in range(8):
        motor.organismo.vida.ejecutar_ciclo()
    return motor


# ==================== TestAutoEvolucion ====================


class TestAutoEvolucion:
    def test_evolucionar_retorna_entrada(self, motor_con_ciclos):
        r = motor_con_ciclos.evolucionar()
        assert "generacion" in r
        assert "timestamp" in r
        assert "pulso" in r
        assert "tendencia" in r
        assert "cambios" in r
        assert r["generacion"] == 1

    def test_generacion_incrementa(self, motor_con_ciclos):
        motor_con_ciclos.evolucionar()
        motor_con_ciclos.evolucionar()
        assert motor_con_ciclos._generacion == 2

    def test_historial_registra(self, motor_con_ciclos):
        motor_con_ciclos.evolucionar()
        h = motor_con_ciclos.historial_evolucion()
        assert len(h) == 1
        assert h[0]["generacion"] == 1

    def test_historial_persiste_a_archivo(self, motor_con_ciclos):
        motor_con_ciclos.evolucionar()
        assert os.path.exists(motor_con_ciclos.historial_path)
        with open(motor_con_ciclos.historial_path, "r") as f:
            linea = json.loads(f.readline())
        assert linea["generacion"] == 1

    def test_intervalo_respeta_limites(self, motor_con_ciclos):
        # Forzar muchas evoluciones
        for _ in range(20):
            motor_con_ciclos.evolucionar()
        lo, hi = LIMITES["intervalo_base"]
        assert lo <= motor_con_ciclos.organismo.vida.intervalo_base <= hi


# ==================== TestPersistencia ====================


class TestPersistencia:
    def test_guardar_crea_archivo(self, motor):
        motor.guardar_estado()
        assert os.path.exists(motor.estado_path)

    def test_guardar_contiene_campos(self, motor):
        motor.guardar_estado()
        with open(motor.estado_path, "r") as f:
            estado = json.load(f)
        assert "version" in estado
        assert "timestamp" in estado
        assert "ciclo_actual" in estado
        assert "conceptos_total" in estado

    def test_cargar_restaura_generacion(self, motor):
        motor._generacion = 42
        motor.guardar_estado()
        motor._generacion = 0
        estado = motor.cargar_estado()
        assert estado is not None
        assert motor._generacion == 42

    def test_cargar_restaura_ciclo(self, motor):
        motor.organismo.vida._ciclo_actual = 100
        motor.guardar_estado()
        motor.organismo.vida._ciclo_actual = 0
        motor.cargar_estado()
        assert motor.organismo.vida._ciclo_actual == 100

    def test_cargar_restaura_ajustes(self, motor):
        motor.organismo.vida._ajustes_curiosidad = {"gap": 1.5, "serendipia": 0.8}
        motor.guardar_estado()
        motor.organismo.vida._ajustes_curiosidad = {}
        motor.cargar_estado()
        assert motor.organismo.vida._ajustes_curiosidad["gap"] == 1.5

    def test_cargar_sin_archivo_retorna_none(self, motor):
        assert motor.cargar_estado() is None

    def test_cargar_archivo_corrupto_retorna_none(self, motor):
        os.makedirs(os.path.dirname(motor.estado_path), exist_ok=True)
        with open(motor.estado_path, "w") as f:
            f.write("no es json{{{")
        assert motor.cargar_estado() is None

    def test_guardar_cargar_roundtrip(self, motor_con_ciclos):
        motor_con_ciclos.evolucionar()
        motor_con_ciclos.guardar_estado()

        gen_antes = motor_con_ciclos._generacion
        ciclo_antes = motor_con_ciclos.organismo.vida._ciclo_actual

        motor_con_ciclos._generacion = 0
        motor_con_ciclos.organismo.vida._ciclo_actual = 0
        motor_con_ciclos.cargar_estado()

        assert motor_con_ciclos._generacion == gen_antes
        assert motor_con_ciclos.organismo.vida._ciclo_actual == ciclo_antes


# ==================== TestPercepcion ====================


class TestPercepcion:
    def test_sin_directorio_retorna_vacio(self, ianae, tmp_path):
        motor = MotorEvolucion(ianae, percepcion_dir=None,
                               estado_path=str(tmp_path / "e.json"),
                               historial_path=str(tmp_path / "h.jsonl"))
        assert motor.percibir() == []

    def test_directorio_vacio_retorna_vacio(self, motor, tmp_path):
        os.makedirs(tmp_path / "percepcion", exist_ok=True)
        assert motor.percibir() == []

    def test_detecta_archivo_txt(self, motor, tmp_path):
        pdir = tmp_path / "percepcion"
        os.makedirs(pdir, exist_ok=True)
        (pdir / "nuevo.txt").write_text("Docker Kubernetes Terraform\nOpenCV Python", encoding="utf-8")
        resultados = motor.percibir()
        assert len(resultados) == 1
        assert resultados[0]["archivo"] == "nuevo.txt"
        assert resultados[0]["conceptos"] >= 0

    def test_detecta_archivo_md(self, motor, tmp_path):
        pdir = tmp_path / "percepcion"
        os.makedirs(pdir, exist_ok=True)
        (pdir / "nota.md").write_text("# Proyecto\nReact Angular Vue\n", encoding="utf-8")
        resultados = motor.percibir()
        assert len(resultados) == 1

    def test_no_reprocesa_archivos(self, motor, tmp_path):
        pdir = tmp_path / "percepcion"
        os.makedirs(pdir, exist_ok=True)
        (pdir / "doc.txt").write_text("Contenido", encoding="utf-8")
        motor.percibir()
        # Segunda vez: no debe reprocesar
        resultados = motor.percibir()
        assert len(resultados) == 0

    def test_ignora_extensiones_no_validas(self, motor, tmp_path):
        pdir = tmp_path / "percepcion"
        os.makedirs(pdir, exist_ok=True)
        (pdir / "imagen.png").write_bytes(b"\x89PNG")
        (pdir / "data.json").write_text("{}", encoding="utf-8")
        resultados = motor.percibir()
        assert len(resultados) == 0

    def test_archivos_percibidos_lista(self, motor, tmp_path):
        pdir = tmp_path / "percepcion"
        os.makedirs(pdir, exist_ok=True)
        (pdir / "a.txt").write_text("Alpha", encoding="utf-8")
        (pdir / "b.txt").write_text("Bravo", encoding="utf-8")
        motor.percibir()
        assert len(motor.archivos_percibidos()) == 2


# ==================== TestCicloEvolutivo ====================


class TestCicloEvolutivo:
    def test_ciclo_retorna_estructura(self, motor_con_ciclos, tmp_path):
        pdir = tmp_path / "percepcion"
        os.makedirs(pdir, exist_ok=True)
        r = motor_con_ciclos.ciclo_evolutivo()
        assert "timestamp" in r
        assert "percepciones" in r
        assert "evolucion" in r
        assert "generacion" in r

    def test_ciclo_guarda_estado(self, motor_con_ciclos, tmp_path):
        os.makedirs(tmp_path / "percepcion", exist_ok=True)
        motor_con_ciclos.ciclo_evolutivo()
        assert os.path.exists(motor_con_ciclos.estado_path)

    def test_multiples_ciclos_evolutivos(self, motor_con_ciclos, tmp_path):
        os.makedirs(tmp_path / "percepcion", exist_ok=True)
        for _ in range(3):
            r = motor_con_ciclos.ciclo_evolutivo()
            assert isinstance(r, dict)
        assert motor_con_ciclos._generacion == 3
