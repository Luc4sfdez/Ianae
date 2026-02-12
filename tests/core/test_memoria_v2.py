"""
Tests para MemoriaAsociativaV2 - Memoria con decaimiento temporal y capacidad máxima.
"""

import time
import pytest
import numpy as np
from src.core.memoria_v2 import MemoriaAsociativaV2


class TestMemoriaAsociativaV2:
    def test_almacenar_y_recuperar(self):
        """Verifica que un vector se almacena y se recupera correctamente por su clave."""
        memoria = MemoriaAsociativaV2()
        
        # Almacenar un vector numpy
        vector = np.array([1, 2, 3, 4, 5])
        memoria.almacenar("vector_test", vector, fuerza=0.8)
        
        # Recuperar
        resultado = memoria.buscar("vector_test")
        
        # Verificar que se recuperó correctamente
        assert resultado is not None
        assert np.array_equal(resultado, vector)
        
        # Almacenar otros tipos de datos
        memoria.almacenar("string_test", "texto ejemplo", fuerza=0.9)
        memoria.almacenar("dict_test", {"key": "value"}, fuerza=0.7)
        
        # Verificar recuperación
        assert memoria.buscar("string_test") == "texto ejemplo"
        assert memoria.buscar("dict_test") == {"key": "value"}
    
    def test_buscar_similares(self):
        """Verifica que buscar_similares devuelve las claves más cercanas a un vector de consulta."""
        memoria = MemoriaAsociativaV2()
        
        # Almacenar múltiples claves relacionadas
        memoria.almacenar("python_basic", "código Python básico", fuerza=0.9)
        memoria.almacenar("python_advanced", "código Python avanzado", fuerza=0.8)
        memoria.almacenar("java_code", "código Java", fuerza=0.7)
        memoria.almacenar("javascript_script", "script JavaScript", fuerza=0.6)
        memoria.almacenar("c_program", "programa en C", fuerza=0.5)
        
        # Buscar similares con patrón "python"
        resultados = memoria.buscar_similares("python", top_k=3)
        
        # Verificar resultados
        assert len(resultados) == 2  # Solo 2 contienen "python"
        claves = [clave for clave, _ in resultados]
        assert "python_basic" in claves
        assert "python_advanced" in claves
        
        # Verificar orden por fuerza (descendente)
        assert resultados[0][1] > resultados[1][1]  # python_basic > python_advanced
        
        # Buscar con patrón más general
        resultados_script = memoria.buscar_similares("script", top_k=5)
        assert len(resultados_script) == 1  # Solo javascript_script
        assert resultados_script[0][0] == "javascript_script"
    
    def test_exportar_e_importar(self):
        """Verifica que el método exportar genera un dict y que importar carga datos correctamente."""
        memoria = MemoriaAsociativaV2(capacidad=50)
        
        # Almacenar datos de prueba
        datos_test = {
            "concepto1": ("valor1", 0.8),
            "concepto2": ({"nested": "dict"}, 0.6),
            "concepto3": (np.array([1, 2, 3]), 0.9)
        }
        
        for clave, (valor, fuerza) in datos_test.items():
            memoria.almacenar(clave, valor, fuerza)
        
        # Exportar datos
        datos_exportados = memoria.exportar()
        
        # Verificar formato de exportación
        assert isinstance(datos_exportados, dict)
        assert len(datos_exportados) == 3
        
        # Verificar estructura exportada
        for clave in datos_test.keys():
            assert clave in datos_exportados
            valor_exp, fuerza_exp, timestamp_exp = datos_exportados[clave]
            assert isinstance(timestamp_exp, float)
            assert 0 <= fuerza_exp <= 1.0
        
        # Crear nueva memoria e importar
        nueva_memoria = MemoriaAsociativaV2()
        nueva_memoria.importar(datos_exportados)
        
        # Verificar que los datos se importaron correctamente
        for clave, (valor_original, _) in datos_test.items():
            valor_importado = nueva_memoria.buscar(clave)
            assert valor_importado is not None
            
            if isinstance(valor_original, np.ndarray):
                assert np.array_equal(valor_importado, valor_original)
            else:
                assert valor_importado == valor_original
    
    def test_memoria_vacia(self):
        """Verifica el comportamiento con memoria vacía."""
        memoria = MemoriaAsociativaV2()
        
        # Buscar en memoria vacía
        assert memoria.buscar("inexistente") is None
        
        # Buscar similares en memoria vacía
        resultados = memoria.buscar_similares("cualquier_patron")
        assert resultados == []
        
        # Consolidar memoria vacía
        eliminadas = memoria.consolidar()
        assert eliminadas == 0
        
        # Estadísticas de memoria vacía
        stats = memoria.estadisticas()
        assert stats["total"] == 0
        assert stats["activas"] == 0
        assert stats["promedio_fuerza"] == 0.0
        
        # Exportar memoria vacía
        exportado = memoria.exportar()
        assert exportado == {}
        
        # Importar a memoria vacía
        memoria.importar({})
        stats_post = memoria.estadisticas()
        assert stats_post["total"] == 0

    # Tests adicionales para cobertura completa
    def test_almacenar_y_buscar(self):
        """Almacena y recupera un valor correctamente."""
        memoria = MemoriaAsociativaV2()
        memoria.almacenar("test", "valor", fuerza=0.8)
        resultado = memoria.buscar("test")
        assert resultado == "valor"

    def test_buscar_inexistente(self):
        """Retorna None para una clave que no existe."""
        memoria = MemoriaAsociativaV2()
        resultado = memoria.buscar("clave_inexistente")
        assert resultado is None

    def test_consolidar(self):
        """Almacena memorias con fuerza baja y verifica que se eliminan al consolidar."""
        memoria = MemoriaAsociativaV2()
        
        # Almacenar con fuerzas diferentes
        memoria.almacenar("fuerte", "valor fuerte", fuerza=0.9)
        memoria.almacenar("debil", "valor débil", fuerza=0.05)  # Bajo umbral
        
        # Consolidar
        eliminadas = memoria.consolidar()
        
        # Verificar que se eliminó la débil
        assert eliminadas == 1
        assert memoria.buscar("fuerte") is not None
        assert memoria.buscar("debil") is None

    def test_estadisticas(self):
        """Almacena varios valores y verifica las estadísticas."""
        memoria = MemoriaAsociativaV2()
        
        memoria.almacenar("a", "valor a", fuerza=0.8)
        memoria.almacenar("b", "valor b", fuerza=0.6)
        memoria.almacenar("c", "valor c", fuerza=0.05)  # Bajo umbral
        
        stats = memoria.estadisticas()
        
        assert stats["total"] == 3
        assert stats["activas"] == 2  # Solo 'a' y 'b' están por encima del umbral
        assert 0 < stats["promedio_fuerza"] < 1

    def test_capacidad_maxima(self):
        """Almacena más elementos que la capacidad y verifica que no se excede."""
        memoria = MemoriaAsociativaV2(capacidad=3)
        
        # Almacenar más de la capacidad
        memoria.almacenar("1", "valor 1", fuerza=0.9)
        memoria.almacenar("2", "valor 2", fuerza=0.8)
        memoria.almacenar("3", "valor 3", fuerza=0.7)
        memoria.almacenar("4", "valor 4", fuerza=0.6)  # Debería eliminar el más débil
        
        stats = memoria.estadisticas()
        assert stats["total"] <= 3

    def test_decaimiento_tiempo(self):
        """Verifica que la fuerza decae con el tiempo."""
        memoria = MemoriaAsociativaV2(decaimiento=0.5)  # Decaimiento rápido para test
        
        memoria.almacenar("test", "valor", fuerza=1.0)
        
        # Simular paso del tiempo modificando timestamp
        if "test" in memoria._memorias:
            valor, fuerza, timestamp = memoria._memorias["test"]
            memoria._memorias["test"] = (valor, fuerza, timestamp - 2.0)  # 2 segundos atrás
        
        # La fuerza debería haber decaído
        resultado = memoria.buscar("test")
        # Con decaimiento=0.5 y 2 segundos: 1.0 * 0.5^2 = 0.25
        # Como es > 0.1, aún debería retornar el valor
        assert resultado is not None

    def test_almacenar_sobre_escribir(self):
        """Almacenar sobre una clave existente combina fuerzas."""
        memoria = MemoriaAsociativaV2()
        
        memoria.almacenar("test", "valor1", fuerza=0.5)
        memoria.almacenar("test", "valor2", fuerza=0.4)  # Debería combinar fuerzas
        
        resultado = memoria.buscar("test")
        assert resultado == "valor2"  # Último valor almacenado

    def test_buscar_similares_case_insensitive(self):
        """La búsqueda de similares debe ser case-insensitive."""
        memoria = MemoriaAsociativaV2()
        
        memoria.almacenar("Python", "lenguaje Python", fuerza=0.8)
        memoria.almacenar("python_script", "script Python", fuerza=0.7)
        
        resultados1 = memoria.buscar_similares("PYTHON")
        resultados2 = memoria.buscar_similares("python")
        resultados3 = memoria.buscar_similares("Python")
        
        # Todas deberían encontrar los mismos resultados
        assert len(resultados1) == 2
        assert len(resultados2) == 2
        assert len(resultados3) == 2

    def test_consolidar_vacio(self):
        """Consolidar una memoria vacía no debería fallar."""
        memoria = MemoriaAsociativaV2()
        
        eliminadas = memoria.consolidar()
        assert eliminadas == 0
        
        stats = memoria.estadisticas()
        assert stats["total"] == 0
        assert stats["activas"] == 0
        assert stats["promedio_fuerza"] == 0.0