"""Tests para ThoughtNode y ThoughtTree (pensamiento_simbolico.py)."""
import pytest
import numpy as np
import time

from src.core.nucleo import ConceptosLucas
from src.core.pensamiento_simbolico import ThoughtNode, ThoughtTree


@pytest.fixture
def nucleo():
    """Sistema con conceptos interconectados para construir arboles."""
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto('Python', atributos=np.random.RandomState(1).rand(15), categoria='tecnologias')
    s.añadir_concepto('OpenCV', atributos=np.random.RandomState(2).rand(15), categoria='tecnologias')
    s.añadir_concepto('Tacografos', atributos=np.random.RandomState(3).rand(15), categoria='proyectos')
    s.añadir_concepto('IANAE', atributos=np.random.RandomState(4).rand(15), categoria='conceptos_ianae')
    s.añadir_concepto('Lucas', atributos=np.random.RandomState(5).rand(15), categoria='lucas_personal')
    s.relacionar('Python', 'OpenCV', fuerza=0.8)
    s.relacionar('Python', 'Tacografos', fuerza=0.7)
    s.relacionar('Python', 'IANAE', fuerza=0.9)
    s.relacionar('OpenCV', 'Tacografos', fuerza=0.6)
    s.relacionar('Lucas', 'Python', fuerza=0.8)
    s.relacionar('Lucas', 'IANAE', fuerza=0.7)
    return s


# ==================== ThoughtNode ====================

class TestThoughtNode:
    def test_crear_nodo_valido(self):
        node = ThoughtNode(
            concept_id='Python',
            activation=0.8,
            vector=np.ones(15),
            coherence=0.9,
            origin='propagation'
        )
        assert node.concept_id == 'Python'
        assert node.activation == 0.8
        assert node.depth == 0
        assert node.children == []

    def test_vector_se_convierte_a_numpy(self):
        node = ThoughtNode(
            concept_id='test',
            activation=0.5,
            vector=[1.0] * 15,
            coherence=0.5,
            origin='emergence'
        )
        assert isinstance(node.vector, np.ndarray)

    def test_vector_dimension_incorrecta(self):
        with pytest.raises(ValueError, match='15 dimensiones'):
            ThoughtNode(
                concept_id='test',
                activation=0.5,
                vector=np.ones(10),
                coherence=0.5,
                origin='propagation'
            )

    def test_activacion_fuera_rango(self):
        with pytest.raises(ValueError, match='entre 0 y 1'):
            ThoughtNode(
                concept_id='test',
                activation=1.5,
                vector=np.ones(15),
                coherence=0.5,
                origin='propagation'
            )

    def test_coherencia_fuera_rango(self):
        with pytest.raises(ValueError, match='entre 0 y 1'):
            ThoughtNode(
                concept_id='test',
                activation=0.5,
                vector=np.ones(15),
                coherence=-0.1,
                origin='propagation'
            )

    def test_origen_invalido(self):
        with pytest.raises(ValueError, match='inválido'):
            ThoughtNode(
                concept_id='test',
                activation=0.5,
                vector=np.ones(15),
                coherence=0.5,
                origin='invalid_origin'
            )

    def test_origenes_validos(self):
        for origin in ['propagation', 'emergence', 'refinement']:
            node = ThoughtNode(
                concept_id='test',
                activation=0.5,
                vector=np.ones(15),
                coherence=0.5,
                origin=origin
            )
            assert node.origin == origin

    def test_timestamp_automatico(self):
        before = time.time()
        node = ThoughtNode(
            concept_id='test',
            activation=0.5,
            vector=np.ones(15),
            coherence=0.5,
            origin='propagation'
        )
        after = time.time()
        assert before <= node.timestamp <= after

    def test_children_mutable(self):
        parent = ThoughtNode('A', 0.8, np.ones(15), 0.9, 'propagation')
        child = ThoughtNode('B', 0.6, np.ones(15) * 0.5, 0.7, 'propagation', depth=1)
        parent.children.append(child)
        assert len(parent.children) == 1
        assert parent.children[0].concept_id == 'B'


# ==================== ThoughtTree ====================

class TestThoughtTreeBuild:
    def test_construye_arbol(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        assert tree.root_node is not None
        assert tree.root_node.concept_id == 'Python'
        assert tree.root_node.activation == 1.0
        assert tree.root_node.depth == 0

    def test_concepto_inexistente(self, nucleo):
        with pytest.raises(ValueError, match='no existe'):
            ThoughtTree('NoExiste', nucleo)

    def test_arbol_tiene_profundidad(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        assert 0 in tree.nodes_by_depth
        # Debe tener al menos depth 0 y 1
        assert len(tree.nodes_by_depth) >= 1

    def test_root_es_depth_0(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        assert tree.root_node in tree.nodes_by_depth[0]

    def test_hijos_tienen_depth_mayor(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        for child in tree.root_node.children:
            assert child.depth > tree.root_node.depth


class TestThoughtTreeCoherence:
    def test_evaluate_coherence_rango(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        c = tree.evaluate_coherence()
        assert 0.0 <= c <= 1.0

    def test_evaluate_coherence_arbol_vacio(self, nucleo):
        tree = ThoughtTree.__new__(ThoughtTree)
        tree.root_node = None
        tree.nodes_by_depth = {}
        assert tree.evaluate_coherence() == 0.0


class TestThoughtTreePrune:
    def test_prune_mantiene_raiz(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        tree.prune(min_coherence=0.99)  # Umbral muy alto
        assert tree.root_node is not None
        assert tree.root_node.concept_id == 'Python'

    def test_prune_reduce_nodos(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        all_before = tree.get_all_nodes()
        tree.prune(min_coherence=0.5)
        all_after = tree.get_all_nodes()
        assert len(all_after) <= len(all_before)

    def test_prune_cero_mantiene_todos(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        all_before = tree.get_all_nodes()
        tree.prune(min_coherence=0.0)
        all_after = tree.get_all_nodes()
        assert len(all_after) == len(all_before)

    def test_prune_arbol_vacio(self, nucleo):
        tree = ThoughtTree.__new__(ThoughtTree)
        tree.root_node = None
        tree.nodes_by_depth = {}
        tree.nucleo = nucleo
        tree.root_concept = 'Python'
        tree.prune()  # No debe crashear


class TestThoughtTreeMerge:
    def test_merge_misma_raiz(self, nucleo):
        tree1 = ThoughtTree('Python', nucleo)
        tree2 = ThoughtTree('Python', nucleo)
        merged = tree1.merge(tree2)
        assert merged.root_node is not None
        assert merged.root_concept == 'Python'

    def test_merge_raiz_diferente_error(self, nucleo):
        tree1 = ThoughtTree('Python', nucleo)
        tree2 = ThoughtTree('OpenCV', nucleo)
        with pytest.raises(ValueError, match='misma raíz'):
            tree1.merge(tree2)

    def test_merge_promedia_activaciones(self, nucleo):
        tree1 = ThoughtTree('Python', nucleo)
        tree2 = ThoughtTree('Python', nucleo)
        merged = tree1.merge(tree2)
        # Root activation should be average of 1.0 and 1.0
        assert merged.root_node.activation == pytest.approx(1.0)


class TestThoughtTreeSymbolic:
    def test_to_symbolic_retorna_string(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        s = tree.to_symbolic()
        assert isinstance(s, str)
        assert 'Python' in s

    def test_to_symbolic_contiene_coherencia(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        s = tree.to_symbolic()
        assert 'Coherence' in s

    def test_to_symbolic_arbol_vacio(self, nucleo):
        tree = ThoughtTree.__new__(ThoughtTree)
        tree.root_node = None
        tree.nodes_by_depth = {}
        assert tree.to_symbolic() == 'EmptyTree'

    def test_to_symbolic_nodo_sin_hijos(self, nucleo):
        tree = ThoughtTree.__new__(ThoughtTree)
        tree.nucleo = nucleo
        tree.root_concept = 'Python'
        tree.nodes_by_depth = {0: []}
        tree.root_node = ThoughtNode(
            concept_id='Python',
            activation=1.0,
            vector=nucleo.conceptos['Python']['actual'],
            coherence=1.0,
            origin='propagation',
            depth=0
        )
        tree.nodes_by_depth[0].append(tree.root_node)
        s = tree.to_symbolic()
        assert 'Python(1.0)' in s


class TestThoughtTreeStats:
    def test_depth_stats_estructura(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        stats = tree.depth_stats()
        assert isinstance(stats, dict)
        assert 0 in stats
        assert stats[0]['node_count'] >= 1

    def test_depth_stats_campos(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        stats = tree.depth_stats()
        for depth, s in stats.items():
            assert 'node_count' in s
            assert 'avg_activation' in s
            assert 'avg_coherence' in s
            assert 'concepts' in s
            assert s['min_activation'] <= s['max_activation']


class TestThoughtTreeGetAllNodes:
    def test_get_all_nodes(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        nodes = tree.get_all_nodes()
        assert len(nodes) >= 1
        assert nodes[0].concept_id == 'Python'

    def test_get_all_nodes_arbol_vacio(self, nucleo):
        tree = ThoughtTree.__new__(ThoughtTree)
        tree.root_node = None
        nodes = tree.get_all_nodes()
        assert nodes == []


class TestCalculateCoherence:
    def test_coherence_vectores_similares(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        v1 = np.ones(15) / np.linalg.norm(np.ones(15))
        v2 = np.ones(15) / np.linalg.norm(np.ones(15))
        c = tree._calculate_coherence(v1, v2, 0.8)
        assert 0.0 <= c <= 1.0

    def test_coherence_penaliza_ruido(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        v1 = np.ones(15) / np.linalg.norm(np.ones(15))
        v2 = np.ones(15) / np.linalg.norm(np.ones(15))
        c_high = tree._calculate_coherence(v1, v2, 0.8)
        c_low = tree._calculate_coherence(v1, v2, 0.1)  # Below 0.15 threshold
        assert c_low <= c_high


class TestFindBestParent:
    def test_find_parent_depth_0(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        parent = tree._find_best_parent('OpenCV', 0)
        if parent:
            assert parent.depth == 0

    def test_find_parent_invalid_depth(self, nucleo):
        tree = ThoughtTree('Python', nucleo)
        parent = tree._find_best_parent('OpenCV', 99)
        assert parent is None
