import numpy as np
import matplotlib as mpl  # Importar matplotlib directamente para obtener la versión
import matplotlib.pyplot as plt
import networkx as nx

print("NumPy versión:", np.__version__)
print("Matplotlib versión:", mpl.__version__)  # Usar mpl en lugar de plt
print("NetworkX versión:", nx.__version__)

# Crear un grafo simple para probar
G = nx.Graph()
G.add_edge('A', 'B', weight=1)
G.add_edge('B', 'C', weight=2)
G.add_edge('C', 'A', weight=3)

# Dibujar el grafo
plt.figure(figsize=(5,4))
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color='skyblue')
plt.title("Gráfico de prueba - Si ves esto, todo funciona!")
plt.show()