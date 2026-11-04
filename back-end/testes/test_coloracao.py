"""Algoritmos de coloração da equipe (graphs/coloracao.py). Rodar: python -m pytest testes -v"""
import os
import sys

import networkx as nx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphs.coloracao import (  # noqa: E402
    conflitos_da_coloracao,
    dsatur,
    guloso,
    maior_clique,
    numero_de_cores,
    saturacao,
)


def test_guloso_da_a_menor_cor_disponivel():
    G = nx.path_graph(4)  # 0-1-2-3
    cores, passos = guloso(G)
    assert cores == {0: 0, 1: 1, 2: 0, 3: 1}
    assert [v for v, _ in passos] == [0, 1, 2, 3]


def test_guloso_depende_da_ordem():
    # Coroa: a ordem 1, 2, 3, 4, 5, 6 força o guloso a usar 3 cores num grafo bipartido.
    G = nx.Graph([(1, 4), (1, 6), (2, 3), (2, 5), (3, 6), (4, 5)])
    cores, _ = guloso(G, ordem=[1, 2, 3, 4, 5, 6])
    assert numero_de_cores(cores) == 3
    assert conflitos_da_coloracao(G, cores) == []


def test_dsatur_e_exato_em_bipartido():
    G = nx.Graph([(1, 4), (1, 6), (2, 3), (2, 5), (3, 6), (4, 5)])
    cores, _ = dsatur(G)
    assert numero_de_cores(cores) == 2
    assert conflitos_da_coloracao(G, cores) == []


def test_dsatur_completo_usa_n_cores():
    cores, _ = dsatur(nx.complete_graph(5))
    assert numero_de_cores(cores) == 5


def test_dsatur_ciclo_impar_usa_3_cores():
    cores, _ = dsatur(nx.cycle_graph(7))
    assert numero_de_cores(cores) == 3


def test_dsatur_comeca_pelo_vertice_de_maior_grau():
    G = nx.star_graph(4)  # centro 0 ligado a 1..4
    _, passos = dsatur(G)
    assert passos[0] == (0, 0)


def test_dsatur_desempata_pelo_menor_id():
    _, passos = dsatur(nx.empty_graph(3))
    assert [v for v, _ in passos] == [0, 1, 2]


def test_saturacao_conta_cores_distintas_dos_vizinhos():
    G = nx.star_graph(3)
    assert saturacao(G, 0, {1: 0, 2: 0, 3: 1}) == 2


def test_dsatur_nunca_pior_que_networkx_em_grafos_aleatorios():
    for semente in range(15):
        G = nx.gnp_random_graph(30, 0.3, seed=semente)
        cores, passos = dsatur(G)
        referencia = nx.coloring.greedy_color(G, strategy="DSATUR")
        assert conflitos_da_coloracao(G, cores) == []
        assert len(passos) == G.number_of_nodes()
        assert numero_de_cores(cores) <= len(set(referencia.values())) + 1


def test_maior_clique_e_limite_inferior():
    G = nx.complete_graph(4)
    G.add_edge(3, 10)
    assert maior_clique(G) == 4
    cores, _ = dsatur(G)
    assert numero_de_cores(cores) >= maior_clique(G)
