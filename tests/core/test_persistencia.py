"""Tests para PersistenciaVectores (SQLite)."""
import pytest
import numpy as np
import os
import tempfile
from src.core.persistencia import PersistenciaVectores


@pytest.fixture
def db(tmp_path):
    """Persistencia con DB temporal."""
    db_path = str(tmp_path / "test_ianae.db")
    return PersistenciaVectores(ruta_db=db_path)


def test_guardar_y_cargar_vector(db):
    """Guardar y recuperar un vector numpy."""
    vec = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    meta = {"categoria": "test", "fuerza": 0.9}

    assert db.guardar_vector("v1", vec, meta)

    vec_out, meta_out = db.cargar_vector("v1")
    np.testing.assert_array_almost_equal(vec_out, vec)
    assert meta_out["categoria"] == "test"
    assert meta_out["fuerza"] == 0.9


def test_cargar_inexistente(db):
    """Cargar vector que no existe retorna (None, None)."""
    vec, meta = db.cargar_vector("no_existe")
    assert vec is None
    assert meta is None


def test_contar_vectores(db):
    """Contar vectores en la DB."""
    assert db.contar_vectores() == 0
    db.guardar_vector("a", np.array([1.0, 2.0]))
    db.guardar_vector("b", np.array([3.0, 4.0]))
    assert db.contar_vectores() == 2


def test_eliminar_vector(db):
    """Eliminar un vector."""
    db.guardar_vector("a", np.array([1.0]))
    assert db.contar_vectores() == 1

    assert db.eliminar_vector("a")
    assert db.contar_vectores() == 0


def test_listar_vectores(db):
    """Listar vectores almacenados."""
    db.guardar_vector("x", np.array([1.0]), {"tipo": "alpha"})
    db.guardar_vector("y", np.array([2.0]), {"tipo": "beta"})

    lista = db.listar_vectores(limite=10)
    assert len(lista) == 2
    ids = [item[0] for item in lista]
    assert "x" in ids
    assert "y" in ids


def test_sobreescribir_vector(db):
    """Guardar con mismo ID sobreescribe."""
    db.guardar_vector("v1", np.array([1.0, 0.0]))
    db.guardar_vector("v1", np.array([0.0, 1.0]))

    vec, _ = db.cargar_vector("v1")
    np.testing.assert_array_almost_equal(vec, np.array([0.0, 1.0]))
    assert db.contar_vectores() == 1


def test_limpiar_tabla(db):
    """Limpiar elimina todo."""
    db.guardar_vector("a", np.array([1.0]))
    db.guardar_vector("b", np.array([2.0]))
    assert db.contar_vectores() == 2

    assert db.limpiar_tabla()
    assert db.contar_vectores() == 0


def test_metadata_default(db):
    """Guardar sin metadata usa dict vacio."""
    db.guardar_vector("v1", np.array([1.0, 2.0]))
    _, meta = db.cargar_vector("v1")
    assert meta == {}
