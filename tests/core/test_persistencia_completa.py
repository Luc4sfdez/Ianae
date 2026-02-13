"""Tests para persistencia completa — Fase 16."""
import json
import os

import pytest

from src.core.nucleo import ConceptosLucas
from src.core.organismo import IANAE
from src.core.memoria_viva import MemoriaViva


# ==================== Fixtures ====================


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("Docker", categoria="tecnologias")
    s.añadir_concepto("IANAE", categoria="conceptos_ianae")
    s.relacionar("Python", "Docker", fuerza=0.8)
    s.relacionar("Python", "IANAE", fuerza=0.9)
    return s


@pytest.fixture
def organismo(sistema, tmp_path):
    return IANAE.desde_componentes(
        sistema,
        diario_path=str(tmp_path / "diario.jsonl"),
        objetivos_path=str(tmp_path / "objetivos.json"),
        conversaciones_path=str(tmp_path / "conv.jsonl"),
        snapshot_dir=str(tmp_path / "snapshots"),
        estado_path=str(tmp_path / "estado.json"),
    )


# ==================== MemoriaViva exportar/importar ====================


class TestMemoriaVivaPersistencia:
    def test_exportar_importar_roundtrip(self):
        mv = MemoriaViva()
        mv.recordar_ciclo("Python", "gap", 0.7, "interesante", 1)
        mv.recordar_relacion("Python", "Docker", 0.8, "test")

        datos = mv.exportar()
        assert "episodica" in datos
        assert "semantica" in datos
        assert len(datos["episodica"]) > 0
        assert len(datos["semantica"]) > 0

        # Importar en nueva instancia
        mv2 = MemoriaViva()
        mv2.importar(datos)

        stats1 = mv.estadisticas()
        stats2 = mv2.estadisticas()
        assert stats1["total_memorias"] == stats2["total_memorias"]

    def test_exportar_vacia(self):
        mv = MemoriaViva()
        datos = mv.exportar()
        assert datos["episodica"] == {}
        assert datos["semantica"] == {}

    def test_importar_vacia(self):
        mv = MemoriaViva()
        mv.recordar_ciclo("X", "gap", 0.5, "rutinario", 1)
        mv.importar({"episodica": {}, "semantica": {}})
        assert mv.estadisticas()["total_memorias"] == 0

    def test_exportar_json_serializable(self):
        mv = MemoriaViva()
        mv.recordar_ciclo("Python", "gap", 0.7, "interesante", 1)
        datos = mv.exportar()
        # Must be JSON-serializable (no tuples)
        serialized = json.dumps(datos)
        restored = json.loads(serialized)
        assert isinstance(restored["episodica"], dict)


# ==================== Organismo guardar/restaurar ====================


class TestGuardarCompleto:
    def test_guardar_crea_archivos(self, organismo, tmp_path):
        save_dir = str(tmp_path / "save")
        archivos = organismo.guardar_completo(save_dir)
        assert "grafo" in archivos
        assert "evolucion" in archivos
        assert "memoria" in archivos
        assert os.path.exists(archivos["grafo"])
        assert os.path.exists(archivos["memoria"])

    def test_restaurar_roundtrip(self, organismo, tmp_path):
        save_dir = str(tmp_path / "save")
        organismo.memoria_viva.recordar_ciclo("Python", "gap", 0.7, "interesante", 1)
        organismo.guardar_completo(save_dir)

        restored = IANAE.restaurar(
            save_dir,
            diario_path=str(tmp_path / "diario2.jsonl"),
            objetivos_path=str(tmp_path / "objetivos2.json"),
            conversaciones_path=str(tmp_path / "conv2.jsonl"),
            snapshot_dir=str(tmp_path / "snap2"),
            estado_path=str(tmp_path / "estado.json"),
        )
        assert restored is not None
        assert len(restored.sistema.conceptos) == len(organismo.sistema.conceptos)
        assert restored.memoria_viva.estadisticas()["total_memorias"] > 0

    def test_restaurar_sin_archivos(self, tmp_path):
        empty_dir = str(tmp_path / "empty")
        os.makedirs(empty_dir, exist_ok=True)
        assert IANAE.restaurar(empty_dir) is None

    def test_conceptos_sobreviven(self, organismo, tmp_path):
        save_dir = str(tmp_path / "save")
        nombres_antes = set(organismo.sistema.conceptos.keys())
        organismo.guardar_completo(save_dir)

        restored = IANAE.restaurar(
            save_dir,
            diario_path=str(tmp_path / "d.jsonl"),
            objetivos_path=str(tmp_path / "o.json"),
            conversaciones_path=str(tmp_path / "c.jsonl"),
            snapshot_dir=str(tmp_path / "s"),
            estado_path=str(tmp_path / "estado.json"),
        )
        nombres_despues = set(restored.sistema.conceptos.keys())
        assert nombres_antes == nombres_despues
