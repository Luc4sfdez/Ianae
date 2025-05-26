"""Ejemplo de procesamiento de texto con IANAE"""

from ianae_optimizador import IANAEOptimizado

# 1. Inicializar sistema
sistema = IANAEOptimizado(dim_vector=50)

# 2. Procesar texto
texto = '''
La inteligencia artificial avanza rápidamente.
Los sistemas como IANAE muestran capacidades emergentes
de pensamiento no algorítmico.
'''

# 3. Entrenar con el texto
resultados = sistema.procesar_texto(texto)

# 4. Mostrar conceptos aprendidos
print("\nConceptos identificados:")
for concepto, datos in resultados['conceptos'].items():
    print(f"- {concepto}: {datos['activaciones']} activaciones")

# 5. Mostrar relaciones clave
print("\nRelaciones relevantes:")
for origen, destinos in resultados['relaciones'].items():
    for destino, peso in destinos:
        if peso > 0.3:
            print(f"{origen} -> {destino} (fuerza: {peso:.2f})")
