"""Tests para VersionadoEstado y su integracion con ConceptosLucas."""
import pytest
import numpy as np
from src.core.versionado import VersionadoEstado
from src.core.nucleo import ConceptosLucas


@pytest.fixture
def versionado(tmp_path):
    return VersionadoEstado(db_path=str(tmp_path / "ver.db"))


@pytest.fixture
def sistema(tmp_path):
    s = ConceptosLucas(dim_vector=5, incertidumbre_base=0.0)
    s.persistencia.ruta_db = str(tmp_path / "per.db")
    s.persistencia._inicializar_tabla()
    s.versionado = VersionadoEstado(db_path=str(tmp_path / "ver.db"))
    s.añadir_concepto("X", atributos=np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    s.añadir_concepto("Y", atributos=np.array([0.0, 1.0, 0.0, 0.0, 0.0]))
    return s


# --- Tests unitarios VersionadoEstado ---

def test_guardar_y_listar(versionado):
    conceptos = {"A": {"actual": np.array([1.0, 2.0])}}
    vid = versionado.guardar_con_version("snap1", conceptos)
    assert vid >= 1
    versiones = versionado.listar_versiones()
    assert len(versiones) == 1
    assert versiones[0]["nombre"] == "snap1"
    assert versiones[0]["num_conceptos"] == 1


def test_multiples_versiones(versionado):
    c1 = {"A": {"actual": np.array([1.0])}}
    c2 = {"A": {"actual": np.array([2.0])}, "B": {"actual": np.array([3.0])}}
    v1 = versionado.guardar_con_version("v1", c1)
    v2 = versionado.guardar_con_version("v2", c2)
    assert v2 > v1
    assert versionado.contar_versiones() == 2


def test_cargar_version(versionado):
    conceptos = {"A": {"actual": np.array([1.0, 2.0, 3.0])}}
    vid = versionado.guardar_con_version("test", conceptos)
    datos = versionado.cargar_version(vid)
    assert datos is not None
    assert datos["nombre"] == "test"
    assert "A" in datos["conceptos"]
    assert datos["conceptos"]["A"]["vector"] == [1.0, 2.0, 3.0]


def test_cargar_version_inexistente(versionado):
    assert versionado.cargar_version(999) is None


# --- Tests integracion con nucleo ---

def test_guardar_estado_crea_version(sistema):
    sistema.guardar_estado("snap1", versionar=True)
    assert sistema.versionado.contar_versiones() == 1


def test_cargar_version_restaura_vectores(sistema):
    vec_original = sistema.conceptos["X"]["actual"].copy()
    sistema.guardar_estado("snap1", versionar=True)
    vid = sistema.versionado.listar_versiones()[0]["version_id"]

    # Perturbar
    sistema.conceptos["X"]["actual"] = np.array([9.0, 9.0, 9.0, 9.0, 9.0])

    # Restaurar
    assert sistema.cargar_version(vid)
    np.testing.assert_array_almost_equal(sistema.conceptos["X"]["actual"], vec_original)


def test_cargar_version_inexistente_nucleo(sistema):
    assert not sistema.cargar_version(999)
