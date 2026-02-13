"""Tests para comunicacion entre instancias — Fase 16."""
import json
import os
import shutil

import numpy as np
import pytest

from src.core.comunicacion import CanalComunicacion
from src.core.nucleo import ConceptosLucas


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("Docker", categoria="tecnologias")
    s.relacionar("Python", "Docker", fuerza=0.8)
    return s


@pytest.fixture
def canal(tmp_path):
    return CanalComunicacion(
        instancia_id="test_a",
        outbox_dir=str(tmp_path / "outbox"),
        inbox_dir=str(tmp_path / "inbox"),
    )


@pytest.fixture
def canal_b(tmp_path):
    """Segundo canal cuyo inbox es el outbox del primero."""
    return CanalComunicacion(
        instancia_id="test_b",
        outbox_dir=str(tmp_path / "outbox_b"),
        inbox_dir=str(tmp_path / "outbox"),  # reads from canal A's outbox
    )


class TestEnviarRecibir:
    def test_enviar_crea_archivo(self, canal):
        msg_id = canal.enviar("saludo", {"hola": "mundo"})
        assert msg_id is not None
        archivos = os.listdir(canal.outbox_dir)
        assert len(archivos) == 1
        assert archivos[0].endswith(".json")

    def test_enviar_recibir_roundtrip(self, canal, canal_b):
        canal.enviar("saludo", {"hola": "mundo"})
        mensajes = canal_b.recibir()
        assert len(mensajes) == 1
        assert mensajes[0]["tipo"] == "saludo"
        assert mensajes[0]["payload"]["hola"] == "mundo"
        assert mensajes[0]["origen"] == "test_a"

    def test_no_recibir_duplicados(self, canal, canal_b):
        canal.enviar("saludo", {"hola": "1"})
        canal.enviar("saludo", {"hola": "2"})
        m1 = canal_b.recibir()
        assert len(m1) == 2
        m2 = canal_b.recibir()
        assert len(m2) == 0  # ya procesados

    def test_inbox_vacio(self, canal):
        assert canal.recibir() == []


class TestCompartirConcepto:
    def test_compartir_concepto(self, canal, sistema):
        msg_id = canal.compartir_concepto(sistema, "Python")
        assert msg_id is not None
        # Verify outbox file content
        archivos = os.listdir(canal.outbox_dir)
        assert len(archivos) == 1
        with open(os.path.join(canal.outbox_dir, archivos[0]), "r") as f:
            data = json.load(f)
        assert data["tipo"] == "concepto"
        assert data["payload"]["nombre"] == "Python"
        assert "vector" in data["payload"]

    def test_compartir_concepto_inexistente(self, canal, sistema):
        result = canal.compartir_concepto(sistema, "NoExiste")
        assert result is None


class TestAbsorber:
    def test_absorber_concepto(self, canal, canal_b, sistema):
        # Canal A comparte concepto
        canal.compartir_concepto(sistema, "Python")
        # Canal B absorbe (reads from canal A's outbox)
        sistema_b = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        absorbidos = canal_b.absorber_mensajes(sistema_b)
        assert len(absorbidos) == 1
        assert absorbidos[0]["tipo"] == "concepto_absorbido"
        assert "Python" in sistema_b.conceptos

    def test_absorber_no_duplica(self, canal, canal_b, sistema):
        canal.compartir_concepto(sistema, "Python")
        sistema_b = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        sistema_b.añadir_concepto("Python", categoria="tecnologias")
        absorbidos = canal_b.absorber_mensajes(sistema_b)
        # Python already exists, should not absorb
        assert len(absorbidos) == 0


class TestEstado:
    def test_estado_vacio(self, canal):
        e = canal.estado()
        assert e["instancia_id"] == "test_a"
        assert e["outbox"] == 0
        assert e["inbox"] == 0
        assert e["procesados"] == 0

    def test_estado_con_mensajes(self, canal):
        canal.enviar("saludo", {})
        canal.enviar("saludo", {})
        e = canal.estado()
        assert e["outbox"] == 2


class TestAnunciar:
    def test_anunciar(self, canal):
        msg_id = canal.anunciar(num_conceptos=42)
        assert msg_id is not None
        archivos = os.listdir(canal.outbox_dir)
        assert len(archivos) == 1
