"""Tests para Consciencia — auto-consciencia de IANAE."""
import json
import os

import pytest

from src.core.nucleo import ConceptosLucas
from src.core.emergente import PensamientoLucas
from src.core.insights import InsightsEngine
from src.core.vida_autonoma import VidaAutonoma
from src.core.consciencia import Consciencia


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
    # Relacion debil para capilaridad
    s.relacionar("Docker", "IANAE", fuerza=0.2)

    for _ in range(5):
        s.activar("Python", pasos=2, temperatura=0.1)
        s.activar("Tacografos", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def vida(sistema, tmp_path):
    pensamiento = PensamientoLucas(sistema)
    insights = InsightsEngine(sistema, pensamiento)
    diario = str(tmp_path / "diario_test.jsonl")
    return VidaAutonoma(
        sistema, pensamiento, insights,
        intervalo_base=0.01,
        diario_path=diario,
        snapshot_dir=str(tmp_path / "snapshots"),
    )


@pytest.fixture
def consciencia(vida, tmp_path):
    objetivos = str(tmp_path / "objetivos_test.json")
    return Consciencia(vida, objetivos_path=objetivos)


@pytest.fixture
def consciencia_con_diario(consciencia):
    """Consciencia con varios ciclos ejecutados para tener datos en diario."""
    for _ in range(8):
        consciencia.vida.ejecutar_ciclo()
    return consciencia


# ==================== TestMetaAnalisis ====================


class TestMetaAnalisis:
    def test_sin_diario_retorna_vacio(self, consciencia):
        r = consciencia.analizar_patrones_propios()
        assert r["ciclos_analizados"] == 0
        assert r["tipos_frecuencia"] == {}

    def test_con_datos_retorna_frecuencias(self, consciencia_con_diario):
        r = consciencia_con_diario.analizar_patrones_propios()
        assert r["ciclos_analizados"] > 0
        assert len(r["tipos_frecuencia"]) > 0
        assert len(r["conceptos_frecuencia"]) > 0

    def test_frecuencias_suman_aprox_1(self, consciencia_con_diario):
        r = consciencia_con_diario.analizar_patrones_propios()
        total_tipos = sum(r["tipos_frecuencia"].values())
        assert 0.95 <= total_tipos <= 1.05  # tolerancia por redondeo

    def test_veredictos_presentes(self, consciencia_con_diario):
        r = consciencia_con_diario.analizar_patrones_propios()
        assert len(r["veredictos_distribucion"]) > 0
        for v in r["veredictos_distribucion"]:
            assert v in {"revelador", "interesante", "rutinario", "desconocido"}


class TestSesgos:
    def test_sin_datos_sin_sesgos(self, consciencia):
        assert consciencia.detectar_sesgos() == []

    def test_retorna_lista_dicts(self, consciencia_con_diario):
        sesgos = consciencia_con_diario.detectar_sesgos()
        assert isinstance(sesgos, list)
        for s in sesgos:
            assert "tipo" in s
            assert "descripcion" in s
            assert "severidad" in s

    def test_severidad_entre_0_y_1(self, consciencia_con_diario):
        sesgos = consciencia_con_diario.detectar_sesgos()
        for s in sesgos:
            assert 0.0 <= s["severidad"] <= 1.0


class TestCrecimiento:
    def test_insuficiente_sin_datos(self, consciencia):
        r = consciencia.medir_crecimiento()
        assert r["tendencia"] == "insuficiente"

    def test_con_datos_retorna_tendencia(self, consciencia_con_diario):
        r = consciencia_con_diario.medir_crecimiento()
        assert r["tendencia"] in {"creciendo", "estable", "decayendo"}
        assert isinstance(r["score_promedio_reciente"], float)
        assert isinstance(r["novedad_promedio"], float)


# ==================== TestNarrativa ====================


class TestNarrativa:
    def test_narrar_ciclo_contiene_concepto(self, consciencia_con_diario):
        entradas = consciencia_con_diario.vida.leer_diario(ultimos=1)
        assert len(entradas) > 0
        narrativa = consciencia_con_diario.narrar_ciclo(entradas[0])
        concepto = entradas[0].get("curiosidad", {}).get("concepto", "")
        assert concepto in narrativa

    def test_narrar_ciclo_contiene_veredicto(self, consciencia_con_diario):
        entradas = consciencia_con_diario.vida.leer_diario(ultimos=1)
        narrativa = consciencia_con_diario.narrar_ciclo(entradas[0])
        veredicto = entradas[0].get("reflexion", {}).get("veredicto", "")
        assert veredicto in narrativa

    def test_narrar_estado_sin_datos(self, consciencia):
        n = consciencia.narrar_estado()
        assert "no ha iniciado" in n.lower() or "sin datos" in n.lower()

    def test_narrar_estado_con_datos(self, consciencia_con_diario):
        n = consciencia_con_diario.narrar_estado()
        assert len(n) > 20
        assert "ciclos" in n.lower()

    def test_explicar_insight_cada_tipo(self, consciencia):
        tipos = ["gap", "revitalizar", "puente", "prediccion", "serendipia"]
        for t in tipos:
            exp = consciencia.explicar_insight(t, "Python")
            assert "Python" in exp
            assert len(exp) > 10


# ==================== TestObjetivos ====================


class TestObjetivos:
    def test_definir_objetivo(self, consciencia):
        obj = consciencia.definir_objetivo(
            "Dominar Docker", ["Docker", "RAG_System"], prioridad=0.8
        )
        assert "id" in obj
        assert obj["descripcion"] == "Dominar Docker"
        assert obj["progreso"] == 0.0
        assert obj["prioridad"] == 0.8

    def test_evaluar_progreso_sin_exploracion(self, consciencia):
        obj = consciencia.definir_objetivo("Test", ["Docker", "IANAE"])
        prog = consciencia.evaluar_progreso(obj["id"])
        assert prog["progreso"] == 0.0
        assert len(prog["pendientes"]) == 2

    def test_evaluar_progreso_con_exploracion(self, consciencia_con_diario):
        # Usar conceptos que probablemente se exploraron
        entradas = consciencia_con_diario.vida.leer_diario(ultimos=8)
        explorados = [e.get("curiosidad", {}).get("concepto", "") for e in entradas]
        if explorados:
            obj = consciencia_con_diario.definir_objetivo(
                "Test", explorados[:2]
            )
            prog = consciencia_con_diario.evaluar_progreso(obj["id"])
            assert prog["progreso"] > 0.0

    def test_objetivo_no_encontrado(self, consciencia):
        r = consciencia.evaluar_progreso("inexistente")
        assert "error" in r

    def test_leer_objetivos(self, consciencia):
        consciencia.definir_objetivo("A", ["Python"])
        consciencia.definir_objetivo("B", ["Docker"])
        objs = consciencia.leer_objetivos()
        assert len(objs) == 2

    def test_persistencia_objetivos(self, consciencia):
        consciencia.definir_objetivo("Persistir", ["Python"])
        assert os.path.exists(consciencia.objetivos_path)
        with open(consciencia.objetivos_path, "r", encoding="utf-8") as f:
            datos = json.load(f)
        assert len(datos) == 1
        assert datos[0]["descripcion"] == "Persistir"


# ==================== TestFuerzas ====================


class TestPulso:
    def test_sin_datos_curiosa(self, consciencia):
        p = consciencia.pulso()
        assert p["estado"] == "curiosa"
        assert p["energia"] == 0.5

    def test_con_datos_estado_valido(self, consciencia_con_diario):
        p = consciencia_con_diario.pulso()
        assert p["estado"] in {"inspirada", "curiosa", "aburrida", "enfocada"}
        assert 0.0 <= p["energia"] <= 1.0
        assert p["racha"] >= 1


class TestCapilaridad:
    def test_retorna_lista(self, consciencia):
        cap = consciencia.capilaridad()
        assert isinstance(cap, list)

    def test_items_tienen_campos(self, consciencia):
        cap = consciencia.capilaridad()
        for item in cap:
            assert "concepto" in item
            assert "atraido_por" in item
            assert "fuerza_conexion" in item


class TestCorrientes:
    def test_sin_datos(self, consciencia):
        c = consciencia.corrientes()
        assert c["flujos"] == {}
        assert c["dominante"] is None

    def test_con_datos_flujos(self, consciencia_con_diario):
        c = consciencia_con_diario.corrientes()
        assert len(c["flujos"]) > 0
        assert c["dominante"] is not None


class TestSuperficie:
    def test_sin_datos_neutro(self, consciencia):
        s = consciencia.superficie()
        assert s == 0.5

    def test_con_datos_entre_0_y_1(self, consciencia_con_diario):
        s = consciencia_con_diario.superficie()
        assert 0.0 <= s <= 1.0


# ==================== TestAjustes ====================


class TestAjustarCuriosidad:
    def test_retorna_5_tipos(self, consciencia):
        aj = consciencia.ajustar_curiosidad()
        assert "gap" in aj
        assert "revitalizar" in aj
        assert "puente" in aj
        assert "prediccion" in aj
        assert "serendipia" in aj

    def test_factores_positivos(self, consciencia_con_diario):
        aj = consciencia_con_diario.ajustar_curiosidad()
        for k, v in aj.items():
            assert v > 0.0


# ==================== TestCicloConsciente ====================


class TestCicloConsciente:
    def test_retorna_todas_capas(self, consciencia):
        r = consciencia.ciclo_consciente()
        assert "timestamp" in r
        assert "vida" in r
        assert "narrativa" in r
        assert "fuerzas" in r
        assert "ajustes_curiosidad" in r

    def test_fuerzas_presentes(self, consciencia):
        r = consciencia.ciclo_consciente()
        f = r["fuerzas"]
        assert "pulso" in f
        assert "capilaridad" in f
        assert "corrientes" in f
        assert "superficie" in f

    def test_narrativa_no_vacia(self, consciencia):
        r = consciencia.ciclo_consciente()
        assert isinstance(r["narrativa"], str)
        assert len(r["narrativa"]) > 10

    def test_multiples_ciclos_conscientes(self, consciencia):
        for _ in range(5):
            r = consciencia.ciclo_consciente()
            assert isinstance(r, dict)
            assert r["vida"]["ciclo"] > 0


# ==================== TestCircuitoCerrado ====================


class TestCircuitoCerrado:
    def test_cerrar_circuito_retorna_ajustes(self, consciencia):
        aj = consciencia.cerrar_circuito()
        assert "gap" in aj
        assert "serendipia" in aj

    def test_cerrar_circuito_aplica_a_vida(self, consciencia):
        consciencia.cerrar_circuito()
        assert len(consciencia.vida._ajustes_curiosidad) == 6

    def test_ciclo_consciente_aplica_ajustes(self, consciencia):
        consciencia.ciclo_consciente()
        # Despues del ciclo, los ajustes deben estar aplicados
        assert len(consciencia.vida._ajustes_curiosidad) == 6
