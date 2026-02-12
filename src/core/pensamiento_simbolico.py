"""
pensamiento_simbolico.py - ThoughtNode y ThoughtTree para pensamiento simbólico recursivo

Implementa el lenguaje interno de IANAE como árboles de ThoughtNodes,
representando estados mentales en lugar de palabras en español.
"""

from dataclasses import dataclass, field
import numpy as np
import time
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

@dataclass
class ThoughtNode:
    """
    Unidad atómica del pensamiento simbólico de IANAE.
    Representa un estado mental, no una palabra.
    """
    concept_id: str           # Nombre del concepto origen
    activation: float         # Nivel de activación (0-1)
    vector: np.ndarray        # Vector de 15 dimensiones
    coherence: float          # Auto-evaluación de coherencia (0-1)
    origin: str               # 'propagation' | 'emergence' | 'refinement'
    children: List['ThoughtNode'] = field(default_factory=list)  # ThoughtNodes derivados
    depth: int = 0            # Profundidad en el árbol
    timestamp: float = field(default_factory=time.time)  # time.time() de creación
    
    def __post_init__(self):
        """Validación de tipos después de inicialización."""
        if not isinstance(self.vector, np.ndarray):
            self.vector = np.array(self.vector)
        if self.vector.shape != (15,):
            raise ValueError(f"Vector debe tener 15 dimensiones, tiene {self.vector.shape}")
        if not 0 <= self.activation <= 1:
            raise ValueError(f"Activación debe estar entre 0 y 1, es {self.activation}")
        if not 0 <= self.coherence <= 1:
            raise ValueError(f"Coherencia debe estar entre 0 y 1, es {self.coherence}")
        if self.origin not in ['propagation', 'emergence', 'refinement']:
            raise ValueError(f"Origen inválido: {self.origin}")


class ThoughtTree:
    """
    Árbol de pensamiento simbólico construido desde activaciones del núcleo.
    """
    
    def __init__(self, root_concept: str, nucleo):
        """
        Construye árbol desde una activación del núcleo.
        
        Args:
            root_concept: Concepto raíz para iniciar el árbol
            nucleo: Instancia de ConceptosLucas o ConceptosDifusos
        """
        self.root_concept = root_concept
        self.nucleo = nucleo
        self.root_node = None
        self.nodes_by_depth = defaultdict(list)
        self._build_tree()
    
    def _build_tree(self):
        """Construye el árbol llamando a nucleo.activar."""
        if self.root_concept not in self.nucleo.conceptos:
            raise ValueError(f"Concepto '{self.root_concept}' no existe en el núcleo")
        
        # Activar el concepto raíz
        resultados = self.nucleo.activar(
            self.root_concept, 
            pasos=3, 
            temperatura=0.5
        )
        
        if not resultados:
            raise ValueError(f"No se pudo activar '{self.root_concept}'")
        
        # Crear nodo raíz
        root_vector = self.nucleo.conceptos[self.root_concept]['actual']
        self.root_node = ThoughtNode(
            concept_id=self.root_concept,
            activation=1.0,
            vector=root_vector,
            coherence=1.0,  # La raíz es perfectamente coherente consigo misma
            origin='propagation',
            depth=0,
            timestamp=time.time()
        )
        self.nodes_by_depth[0].append(self.root_node)
        
        # Construir árbol por niveles de profundidad
        for paso_idx, activaciones_paso in enumerate(resultados[1:], start=1):  # Saltar paso 0 (solo raíz)
            depth = paso_idx
            
            # Para cada concepto activado en este paso
            for concepto, activacion in activaciones_paso.items():
                if activacion > 0.1:  # Umbral para considerar
                    # Buscar padre más cercano en nivel anterior
                    parent = self._find_best_parent(concepto, depth-1)
                    
                    if parent:
                        # Crear nodo hijo
                        concepto_vector = self.nucleo.conceptos[concepto]['actual']
                        coherence = self._calculate_coherence(concepto_vector, parent.vector, activacion)
                        
                        child_node = ThoughtNode(
                            concept_id=concepto,
                            activation=activacion,
                            vector=concepto_vector,
                            coherence=coherence,
                            origin='propagation',
                            depth=depth,
                            timestamp=time.time()
                        )
                        
                        parent.children.append(child_node)
                        self.nodes_by_depth[depth].append(child_node)
    
    def _find_best_parent(self, concepto: str, parent_depth: int) -> Optional[ThoughtNode]:
        """
        Encuentra el mejor nodo padre para un concepto dado.
        
        Args:
            concepto: Concepto para el que buscar padre
            parent_depth: Profundidad de los padres candidatos
            
        Returns:
            El nodo padre más apropiado o None
        """
        if parent_depth not in self.nodes_by_depth:
            return None
        
        concepto_vector = self.nucleo.conceptos[concepto]['actual']
        best_parent = None
        best_similarity = -1
        
        for parent in self.nodes_by_depth[parent_depth]:
            # Calcular similitud coseno
            parent_vector = parent.vector
            similarity = np.dot(concepto_vector, parent_vector) / (
                np.linalg.norm(concepto_vector) * np.linalg.norm(parent_vector) + 1e-10
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_parent = parent
        
        return best_parent if best_similarity > 0.1 else None  # Umbral mínimo
    
    def _calculate_coherence(self, child_vector: np.ndarray, parent_vector: np.ndarray, 
                           child_activation: float) -> float:
        """
        Calcula coherencia de un nodo hijo respecto a su padre.
        
        Fórmula:
        - cosine_similarity(vector_nodo, vector_padre) si tiene padre
        - Bonus +0.2 si el nodo es de categoría diferente al padre (emergencia cross-category)
        - Penalización -0.3 si activación < 0.15 (ruido)
        """
        # Similitud coseno base
        similarity = np.dot(child_vector, parent_vector) / (
            np.linalg.norm(child_vector) * np.linalg.norm(parent_vector) + 1e-10
        )
        
        # Bonus por cross-categoría (si los conceptos tienen categorías diferentes)
        child_concept = None
        parent_concept = None
        
        # Buscar categorías en el núcleo
        for name, data in self.nucleo.conceptos.items():
            if np.array_equal(data['actual'], child_vector):
                child_concept = name
            if np.array_equal(data['actual'], parent_vector):
                parent_concept = name
        
        cross_category_bonus = 0.0
        if child_concept and parent_concept:
            child_cat = self.nucleo.conceptos[child_concept].get('categoria', 'emergentes')
            parent_cat = self.nucleo.conceptos[parent_concept].get('categoria', 'emergentes')
            if child_cat != parent_cat:
                cross_category_bonus = 0.2
        
        # Penalización por ruido
        noise_penalty = 0.0
        if child_activation < 0.15:
            noise_penalty = -0.3
        
        # Coherencia final (clip entre 0 y 1)
        coherence = similarity + cross_category_bonus + noise_penalty
        return max(0.0, min(1.0, coherence))
    
    def evaluate_coherence(self) -> float:
        """
        Calcula coherencia del árbol completo.
        
        Returns:
            Coherencia promedio ponderada por activación
        """
        if not self.root_node:
            return 0.0
        
        total_weighted_coherence = 0.0
        total_activation = 0.0
        
        # Recorrer todos los nodos en el árbol
        def traverse(node):
            nonlocal total_weighted_coherence, total_activation
            total_weighted_coherence += node.coherence * node.activation
            total_activation += node.activation
            
            for child in node.children:
                traverse(child)
        
        traverse(self.root_node)
        
        return total_weighted_coherence / max(total_activation, 1e-10)
    
    def prune(self, min_coherence: float = 0.3):
        """
        Elimina ramas incoherentes del árbol.
        
        Args:
            min_coherence: Coherencia mínima para mantener un nodo
        """
        if not self.root_node:
            return
        
        def prune_node(node: ThoughtNode) -> bool:
            """Poda recursiva, retorna True si el nodo debe mantenerse."""
            # Filtrar hijos primero
            node.children = [child for child in node.children if prune_node(child)]
            
            # Mantener nodo si:
            # 1. Es la raíz, o
            # 2. Tiene coherencia suficiente, o
            # 3. Tiene hijos (aunque sea incoherente, puede ser puente)
            if node.depth == 0:
                return True
            elif node.coherence >= min_coherence:
                return True
            elif node.children:  # Mantener si tiene hijos coherentes
                return True
            else:
                return False
        
        # Reconstruir nodes_by_depth después de podar
        self.nodes_by_depth.clear()
        
        def rebuild_depth_index(node):
            self.nodes_by_depth[node.depth].append(node)
            for child in node.children:
                rebuild_depth_index(child)
        
        if prune_node(self.root_node):
            rebuild_depth_index(self.root_node)
        else:
            self.root_node = None
            self.nodes_by_depth.clear()
    
    def merge(self, other: 'ThoughtTree') -> 'ThoughtTree':
        """
        Fusiona dos árboles de pensamiento.
        
        Args:
            other: Otro ThoughtTree para fusionar
            
        Returns:
            Nuevo ThoughtTree fusionado
        """
        if self.root_concept != other.root_concept:
            raise ValueError("Solo se pueden fusionar árboles con la misma raíz")
        
        # Crear nuevo árbol con la misma raíz
        merged_tree = ThoughtTree.__new__(ThoughtTree)
        merged_tree.root_concept = self.root_concept
        merged_tree.nucleo = self.nucleo
        merged_tree.nodes_by_depth = defaultdict(list)
        
        # Fusionar nodos por profundidad
        all_depths = set(self.nodes_by_depth.keys()) | set(other.nodes_by_depth.keys())
        
        for depth in sorted(all_depths):
            # Recolectar nodos de ambos árboles en esta profundidad
            nodes_self = self.nodes_by_depth.get(depth, [])
            nodes_other = other.nodes_by_depth.get(depth, [])
            
            # Agrupar por concepto_id
            nodes_by_concept = {}
            
            # Agregar nodos de self
            for node in nodes_self:
                nodes_by_concept[node.concept_id] = {
                    'node': node,
                    'count': 1,
                    'total_activation': node.activation,
                    'total_coherence': node.coherence
                }
            
            # Fusionar con nodos de other
            for node in nodes_other:
                if node.concept_id in nodes_by_concept:
                    # Nodo existente: promediar
                    data = nodes_by_concept[node.concept_id]
                    data['count'] += 1
                    data['total_activation'] += node.activation
                    data['total_coherence'] += node.coherence
                else:
                    # Nuevo nodo
                    nodes_by_concept[node.concept_id] = {
                        'node': node,
                        'count': 1,
                        'total_activation': node.activation,
                        'total_coherence': node.coherence
                    }
            
            # Crear nodos fusionados para esta profundidad
            merged_nodes = []
            for concept_id, data in nodes_by_concept.items():
                original_node = data['node']
                count = data['count']
                
                # Crear nodo fusionado
                merged_node = ThoughtNode(
                    concept_id=concept_id,
                    activation=data['total_activation'] / count,
                    vector=original_node.vector,  # Vector no cambia
                    coherence=data['total_coherence'] / count,
                    origin=original_node.origin,
                    depth=depth,
                    timestamp=time.time()
                )
                
                merged_nodes.append(merged_node)
            
            merged_tree.nodes_by_depth[depth] = merged_nodes
        
        # Reconstruir relaciones padre-hijo (simplificado)
        # Para este MVP, solo establecemos la raíz
        if 0 in merged_tree.nodes_by_depth:
            merged_tree.root_node = merged_tree.nodes_by_depth[0][0]
        
        return merged_tree
    
    def to_symbolic(self) -> str:
        """
        Representación simbólica: notación lógica, no prosa.
        
        Formato: "Python(0.9) -> [OpenCV(0.7), Pandas(0.6)] ~> Emergent(vision+data, 0.4)"
        """
        if not self.root_node:
            return "EmptyTree"
        
        parts = []
        
        def build_symbolic(node, indent=0):
            # Representación del nodo actual
            node_repr = f"{node.concept_id}({node.activation:.1f})"
            
            if node.children:
                # Si tiene hijos, mostrar como lista
                children_repr = []
                for child in node.children:
                    child_repr = f"{child.concept_id}({child.activation:.1f})"
                    if child.coherence < 0.3:
                        child_repr += "!"  # Marcar baja coherencia
                    children_repr.append(child_repr)
                
                children_str = "[" + ", ".join(children_repr) + "]"
                
                # Determinar tipo de transición
                if node.origin == 'emergence':
                    connector = "~>"
                else:
                    connector = "->"
                
                return f"{node_repr} {connector} {children_str}"
            else:
                return node_repr
        
        # Construir desde la raíz
        root_symbolic = build_symbolic(self.root_node)
        parts.append(root_symbolic)
        
        # Agregar coherencia global
        global_coherence = self.evaluate_coherence()
        parts.append(f"~> Coherence({global_coherence:.2f})")
        
        return " ".join(parts)
    
    def depth_stats(self) -> dict:
        """
        Estadísticas por profundidad del árbol.
        
        Returns:
            Dict con estadísticas por nivel de profundidad
        """
        stats = {}
        
        for depth, nodes in self.nodes_by_depth.items():
            if nodes:
                activations = [n.activation for n in nodes]
                coherences = [n.coherence for n in nodes]
                
                stats[depth] = {
                    'node_count': len(nodes),
                    'avg_activation': np.mean(activations),
                    'min_activation': np.min(activations),
                    'max_activation': np.max(activations),
                    'avg_coherence': np.mean(coherences),
                    'min_coherence': np.min(coherences),
                    'max_coherence': np.max(coherences),
                    'concepts': [n.concept_id for n in nodes]
                }
        
        return stats
    
    def get_all_nodes(self) -> List[ThoughtNode]:
        """Retorna todos los nodos del árbol."""
        nodes = []
        
        def collect(node):
            nodes.append(node)
            for child in node.children:
                collect(child)
        
        if self.root_node:
            collect(self.root_node)
        
        return nodes