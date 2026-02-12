"""
Tests para la memoria asociativa de IANAE.
"""

import pytest
from src.core.memoria import MemoriaAsociativa


class TestMemoriaAsociativa:
    """Tests para la clase MemoriaAsociativa."""

    def test_init_crea_almacen_vacio(self):
        """La memoria debe inicializarse con un almacén vacío."""
        memoria = MemoriaAsociativa()
        assert memoria._almacen == {}

    def test_almacenar_guarda_nuevo_concepto(self):
        """Almacenar un concepto nuevo debe agregarlo al almacén."""
        memoria = MemoriaAsociativa()
        memoria.almacenar("Python", "Lenguaje de programación", 0.9)
        
        assert "Python" in memoria._almacen
        contexto, peso = memoria._almacen["Python"]
        assert contexto == "Lenguaje de programación"
        assert peso == 0.9

    def test_almacenar_sobrescribe_existente(self):
        """Almacenar un concepto existente debe sobrescribirlo."""
        memoria = MemoriaAsociativa()
        memoria.almacenar("Python", "Lenguaje antiguo", 0.5)
        memoria.almacenar("Python", "Lenguaje moderno", 0.8)
        
        assert len(memoria._almacen) == 1
        contexto, peso = memoria._almacen["Python"]
        assert contexto == "Lenguaje moderno"
        assert peso == 0.8

    def test_buscar_sin_resultados(self):
        """Buscar una query que no coincide debe retornar lista vacía."""
        memoria = MemoriaAsociativa()
        memoria.almacenar("Python", "Lenguaje", 0.9)
        
        resultados = memoria.buscar("Java")
        assert resultados == []

    def test_buscar_case_insensitive(self):
        """La búsqueda debe ser case-insensitive."""
        memoria = MemoriaAsociativa()
        memoria.almacenar("Python", "Lenguaje", 0.9)
        memoria.almacenar("pytorch", "Framework", 0.7)
        
        resultados = memoria.buscar("PY")
        assert len(resultados) == 2
        conceptos = [c for c, _ in resultados]
        assert "Python" in conceptos
        assert "pytorch" in conceptos

    def test_buscar_orden_por_peso_descendente(self):
        """Los resultados deben ordenarse por peso descendente."""
        memoria = MemoriaAsociativa()
        memoria.almacenar("A", "Contexto A", 0.3)
        memoria.almacenar("B", "Contexto B", 0.9)
        memoria.almacenar("C", "Contexto C", 0.5)
        
        resultados = memoria.buscar("")
        pesos = [p for _, p in resultados]
        assert pesos == [0.9, 0.5, 0.3]

    def test_buscar_top_k(self):
        """El parámetro top_k debe limitar el número de resultados."""
        memoria = MemoriaAsociativa()
        for i in range(10):
            memoria.almacenar(f"Concepto{i}", f"Contexto{i}", i/10.0)
        
        resultados = memoria.buscar("Concepto", top_k=3)
        assert len(resultados) == 3
        # Deben ser los 3 con mayor peso
        pesos_esperados = [0.9, 0.8, 0.7]
        pesos_obtenidos = [p for _, p in resultados]
        assert pesos_obtenidos == pesos_esperados

    def test_buscar_substring(self):
        """Debe coincidir con substrings dentro del concepto."""
        memoria = MemoriaAsociativa()
        memoria.almacenar("Machine Learning", "AI", 0.8)
        memoria.almacenar("Deep Learning", "AI", 0.7)
        memoria.almacenar("Reinforcement Learning", "AI", 0.6)
        
        resultados = memoria.buscar("Learning")
        assert len(resultados) == 3
        conceptos = [c for c, _ in resultados]
        assert "Machine Learning" in conceptos
        assert "Deep Learning" in conceptos
        assert "Reinforcement Learning" in conceptos

    def test_exportar_copia(self):
        """Exportar debe retornar una copia del almacén interno."""
        memoria = MemoriaAsociativa()
        memoria.almacenar("A", "Contexto A", 0.5)
        memoria.almacenar("B", "Contexto B", 0.8)
        
        exportado = memoria.exportar()
        # Debe ser igual
        assert exportado == memoria._almacen
        # Pero no el mismo objeto
        assert exportado is not memoria._almacen
        
        # Modificar la copia no debe afectar al original
        exportado["C"] = ("Contexto C", 1.0)
        assert "C" not in memoria._almacen

    def test_exportar_vacio(self):
        """Exportar una memoria vacía debe retornar dict vacío."""
        memoria = MemoriaAsociativa()
        exportado = memoria.exportar()
        assert exportado == {}
        assert isinstance(exportado, dict)

    def test_integracion_completa(self):
        """Test de integración: almacenar, buscar, exportar."""
        memoria = MemoriaAsociativa()
        
        # Almacenar varios conceptos
        datos = [
            ("Python", "Lenguaje interpretado", 0.9),
            ("Java", "Lenguaje compilado", 0.7),
            ("JavaScript", "Lenguaje web", 0.8),
            ("TypeScript", "JavaScript con tipos", 0.85),
        ]
        
        for concepto, contexto, peso in datos:
            memoria.almacenar(concepto, contexto, peso)
        
        # Buscar
        resultados = memoria.buscar("Script")
        assert len(resultados) == 2
        conceptos = [c for c, _ in resultados]
        assert "JavaScript" in conceptos
        assert "TypeScript" in conceptos
        
        # Verificar orden por peso
        pesos = [p for _, p in resultados]
        assert pesos == [0.85, 0.8]  # TypeScript primero
        
        # Exportar
        exportado = memoria.exportar()
        assert len(exportado) == 4
        for concepto, contexto, peso in datos:
            assert concepto in exportado
            ctx_exp, peso_exp = exportado[concepto]
            assert ctx_exp == contexto
            assert peso_exp == peso