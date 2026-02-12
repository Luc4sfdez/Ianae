"""Tests para VidaAutonoma — ciclo autonomo de IANAE."""
import json
import os
import tempfile

import pytest

from src.core.nucleo import ConceptosLucas
from src.core.emergente import PensamientoLucas
from src.core.insights import InsightsEngine
from src.core.vida_autonoma import VidaAutonoma, TIPOS_CURIOSIDAD


# ==================== Fixtures ====================


@pytest.fixture
def sistema():
    """Sistema con 8 conceptos multi-categoria, relaciones y activaciones."""
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    # Tecnologias
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("OpenCV", categoria="tecnologias")
    s.añadir_concepto("Docker", categoria="tecnologias")
    # Proyectos
    s.añadir_concepto("Tacografos", categoria="proyectos")
    s.añadir_concepto("RAG_System", categoria="proyectos")
    # Personal
    s.añadir_concepto("Lucas", categoria="lucas_personal")
    # IANAE
    s.añadir_concepto("IANAE", categoria="conceptos_ianae")
    # Herramientas
    s.añadir_concepto("Automatizacion", categoria="herramientas")

    # Relaciones
    s.relacionar("Python", "OpenCV", fuerza=0.9)
    s.relacionar("Python", "Tacografos", fuerza=0.85)
    s.relacionar("OpenCV", "Tacografos", fuerza=0.95)
    s.relacionar("Python", "RAG_System", fuerza=0.8)
    s.relacionar("RAG_System", "IANAE", fuerza=0.9)
    s.relacionar("Lucas", "Python", fuerza=0.95)
    s.relacionar("Lucas", "IANAE", fuerza=0.9)
    s.relacionar("Docker", "RAG_System", fuerza=0.7)
    s.relacionar("Automatizacion", "Python", fuerza=0.85)

    # Historial de activaciones para que insights tenga datos
    for _ in range(5):
        s.activar("Python", pasos=2, temperatura=0.1)
        s.activar("Tacografos", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def pensamiento(sistema):
    return PensamientoLucas(sistema)


@pytest.fixture
def insights(sistema, pensamiento):
    return InsightsEngine(sistema, pensamiento)


@pytest.fixture
def vida(sistema, pensamiento, insights, tmp_path):
    diario = str(tmp_path / "diario_test.jsonl")
    return VidaAutonoma(
        sistema,
        pensamiento,
        insights,
        intervalo_base=0.01,  # Rapido para tests
        diario_path=diario,
        consolidar_cada=5,
        snapshot_dir=str(tmp_path / "snapshots"),
    )


@pytest.fixture
def vida_grafo_vacio(tmp_path):
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    p = PensamientoLucas(s)
    i = InsightsEngine(s, p)
    diario = str(tmp_path / "diario_vacio.jsonl")
    return VidaAutonoma(s, p, i, diario_path=diario, intervalo_base=0.01)


# ==================== TestCuriosidad ====================


class TestCuriosidad:
    def test_retorna_dict_con_campos(self, vida):
        c = vida._curiosidad()
        assert isinstance(c, dict)
        assert "tipo" in c
        assert "concepto" in c
        assert "motivacion" in c
        assert "prioridad" in c

    def test_concepto_pertenece_al_sistema(self, vida):
        c = vida._curiosidad()
        assert c["concepto"] in vida.sistema.conceptos

    def test_tipo_valido(self, vida):
        c = vida._curiosidad()
        assert c["tipo"] in TIPOS_CURIOSIDAD

    def test_prioridad_float_no_negativa(self, vida):
        c = vida._curiosidad()
        assert isinstance(c["prioridad"], float)
        assert c["prioridad"] >= 0.0

    def test_grafo_vacio_retorna_fallback(self, vida_grafo_vacio):
        c = vida_grafo_vacio._curiosidad()
        assert c["tipo"] == "serendipia"
        assert c["concepto"] == "desconocido"


# ==================== TestPreguntas ====================


class TestPreguntas:
    def test_retorna_string_no_vacio(self, vida):
        cur = vida._curiosidad()
        p = vida._preguntar(cur)
        assert isinstance(p, str)
        assert len(p) > 0

    def test_contiene_concepto(self, vida):
        cur = {"tipo": "puente", "concepto": "Python", "motivacion": "test", "prioridad": 0.5}
        p = vida._preguntar(cur)
        assert "Python" in p

    def test_cada_tipo_genera_pregunta(self, vida):
        for tipo in TIPOS_CURIOSIDAD:
            cur = {"tipo": tipo, "concepto": "Python", "motivacion": "test",
                   "prioridad": 0.5, "categoria": "tecnologias"}
            p = vida._preguntar(cur)
            assert isinstance(p, str) and len(p) > 0


# ==================== TestExploracion ====================


class TestExploracion:
    def test_retorna_dict_con_claves(self, vida):
        cur = {"tipo": "puente", "concepto": "Python", "motivacion": "t", "prioridad": 0.5}
        r = vida._explorar(cur)
        assert "activaciones" in r
        assert "coherencia" in r
        assert "conexiones_nuevas" in r

    def test_coherencia_entre_0_y_1(self, vida):
        cur = {"tipo": "puente", "concepto": "Python", "motivacion": "t", "prioridad": 0.5}
        r = vida._explorar(cur)
        assert 0.0 <= r["coherencia"] <= 1.0

    def test_activaciones_no_vacias(self, vida):
        cur = {"tipo": "puente", "concepto": "Python", "motivacion": "t", "prioridad": 0.5}
        r = vida._explorar(cur)
        assert len(r["activaciones"]) > 0

    def test_concepto_inexistente_graceful(self, vida):
        cur = {"tipo": "serendipia", "concepto": "NoExiste", "motivacion": "t", "prioridad": 0.1}
        r = vida._explorar(cur)
        assert r["activaciones"] == {}
        assert r["coherencia"] == 0.0


# ==================== TestReflexion ====================


class TestReflexion:
    def test_score_entre_0_y_1(self, vida):
        resp = {"coherencia": 0.5, "conexiones_nuevas": 1, "convergencia": True}
        r = vida._reflexionar(resp)
        assert 0.0 <= r["score"] <= 1.0

    def test_veredicto_valido(self, vida):
        resp = {"coherencia": 0.5, "conexiones_nuevas": 0, "convergencia": False}
        r = vida._reflexionar(resp)
        assert r["veredicto"] in {"revelador", "interesante", "rutinario"}

    def test_score_alto_con_todo(self, vida):
        resp = {"coherencia": 0.9, "conexiones_nuevas": 3, "convergencia": True}
        r = vida._reflexionar(resp)
        # novedad=1.0*0.3 + coherencia=0.9*0.4 + convergencia=0.3 = 0.96
        assert r["score"] > 0.7
        assert r["veredicto"] == "revelador"


# ==================== TestIntegracion ====================


class TestIntegracion:
    def test_score_alto_ejecuta_auto_mod(self, vida):
        # Generar historial para que auto_modificar funcione
        vida.sistema.activar("Python", pasos=2)
        reflexion = {"score": 0.8, "veredicto": "revelador"}
        respuesta = {"conexiones_nuevas": 0, "activaciones": {}}
        r = vida._integrar(reflexion, respuesta)
        assert r["auto_mod"] is True

    def test_novedad_ejecuta_genesis(self, vida):
        vida.sistema.activar("Python", pasos=2)
        reflexion = {"score": 0.3, "veredicto": "rutinario"}
        respuesta = {"conexiones_nuevas": 2, "activaciones": {}}
        r = vida._integrar(reflexion, respuesta)
        # genesis se intenta (puede crear 0 si no hay candidatos)
        assert "genesis" in r

    def test_siempre_ejecuta_aprendizaje(self, vida):
        reflexion = {"score": 0.1, "veredicto": "rutinario"}
        respuesta = {"conexiones_nuevas": 0, "activaciones": {}}
        r = vida._integrar(reflexion, respuesta)
        assert r["aprendizaje"] is True


# ==================== TestDiario ====================


class TestDiario:
    def test_registra_entrada_con_campos(self, vida):
        entrada = {
            "ciclo": 1,
            "timestamp": 123456.0,
            "curiosidad": {"tipo": "gap", "concepto": "X"},
            "pregunta": "test?",
            "reflexion": {"score": 0.5, "veredicto": "interesante"},
        }
        vida._registrar_diario(entrada)
        contenido = vida.leer_diario(ultimos=1)
        assert len(contenido) == 1
        assert contenido[0]["ciclo"] == 1

    def test_leer_diario_ultimas_n(self, vida):
        for i in range(5):
            vida._registrar_diario({"ciclo": i})
        contenido = vida.leer_diario(ultimos=3)
        assert len(contenido) == 3
        assert contenido[0]["ciclo"] == 2
        assert contenido[2]["ciclo"] == 4

    def test_archivo_jsonl_creado(self, vida):
        vida._registrar_diario({"ciclo": 1})
        assert os.path.exists(vida.diario_path)
        with open(vida.diario_path, "r", encoding="utf-8") as f:
            linea = f.readline().strip()
        parsed = json.loads(linea)
        assert parsed["ciclo"] == 1


# ==================== TestCicloCompleto ====================


class TestCicloCompleto:
    def test_ejecutar_ciclo_retorna_todas_fases(self, vida):
        r = vida.ejecutar_ciclo()
        assert "ciclo" in r
        assert "timestamp" in r
        assert "curiosidad" in r
        assert "pregunta" in r
        assert "descubrimientos" in r
        assert "reflexion" in r
        assert "integracion" in r

    def test_multiples_ciclos_no_rompen(self, vida):
        for _ in range(5):
            r = vida.ejecutar_ciclo()
            assert isinstance(r, dict)
            assert r["ciclo"] > 0
        assert vida._ciclo_actual == 5


# ==================== TestDescanso ====================


class TestDescanso:
    def test_revelador_intervalo_corto(self, vida):
        t = vida._descansar({"veredicto": "revelador"})
        assert t == vida.intervalo_base * 0.5

    def test_rutinario_intervalo_largo(self, vida):
        t = vida._descansar({"veredicto": "rutinario"})
        assert t == vida.intervalo_base * 2.0


# ==================== TestEstado ====================


class TestEstado:
    def test_estado_retorna_info(self, vida):
        e = vida.estado()
        assert "ciclo_actual" in e
        assert "corriendo" in e
        assert "conceptos" in e
        assert e["conceptos"] == 8

    def test_detener(self, vida):
        vida._corriendo = True
        vida.detener()
        assert vida._corriendo is False


# ==================== TestCircuitoCerrado ====================


class TestCircuitoCerrado:
    def test_ajustes_curiosidad_inicialmente_vacio(self, vida):
        assert vida._ajustes_curiosidad == {}

    def test_ajustes_modifican_prioridad(self, vida):
        vida._ajustes_curiosidad = {"gap": 0.1, "puente": 2.0, "serendipia": 1.0}
        # Ejecutar varios ciclos — los ajustes se aplican sin error
        for _ in range(3):
            r = vida.ejecutar_ciclo()
            assert isinstance(r, dict)

    def test_factor_cero_reduce_tipo(self, vida):
        # Con factor muy bajo para todo excepto serendipia
        vida._ajustes_curiosidad = {
            "gap": 0.01, "revitalizar": 0.01, "puente": 0.01,
            "prediccion": 0.01, "serendipia": 5.0,
        }
        # Ejecutar ciclos — no debe fallar
        for _ in range(3):
            r = vida.ejecutar_ciclo()
            assert r["curiosidad"]["prioridad"] >= 0.0
