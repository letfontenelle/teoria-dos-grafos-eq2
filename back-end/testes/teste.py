import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphs.graph import construir_grafo_conflitos, resolver_coloracao_horarios


# monta uma alocacao igual a que vem do supabase
def aula(id, professor, periodo):
    return {"ALO_ID": id, "PRO_ID": professor, "DI_DISCIPLINA": {"DI_PERIODO": periodo}}


# testes do grafo

def test_grafo_vazio():
    G = construir_grafo_conflitos([])
    assert G.number_of_nodes() == 0
    assert G.number_of_edges() == 0


def test_vertices():
    G = construir_grafo_conflitos([aula(1, 10, 1), aula(2, 20, 2), aula(3, 30, 3)])
    assert set(G.nodes) == {1, 2, 3}


def test_conflito_professor():
    G = construir_grafo_conflitos([aula(1, 10, 1), aula(2, 10, 2)])
    assert G.has_edge(1, 2)
    assert G.edges[1, 2]["motivo"] == "professor"


def test_conflito_periodo():
    G = construir_grafo_conflitos([aula(1, 10, 3), aula(2, 20, 3)])
    assert G.has_edge(1, 2)
    assert G.edges[1, 2]["motivo"] == "perfil_pleno"


def test_conflito_professor_e_periodo():
    G = construir_grafo_conflitos([aula(1, 10, 3), aula(2, 10, 3)])
    assert G.edges[1, 2]["motivo"] == "professor_e_perfil_pleno"


def test_sem_conflito():
    G = construir_grafo_conflitos([aula(1, 10, 1), aula(2, 20, 2)])
    assert not G.has_edge(1, 2)


def test_professor_none():
    # se nao tem professor cadastrado nao pode contar como o mesmo professor
    G = construir_grafo_conflitos([aula(1, None, 1), aula(2, None, 2)])
    assert not G.has_edge(1, 2)


def test_disciplina_none():
    alocacoes = [
        {"ALO_ID": 1, "PRO_ID": 10, "DI_DISCIPLINA": None},
        {"ALO_ID": 2, "PRO_ID": 20, "DI_DISCIPLINA": None},
    ]
    G = construir_grafo_conflitos(alocacoes)
    assert G.number_of_nodes() == 2
    assert not G.has_edge(1, 2)


# testes da coloracao (dsatur)

def test_todas_aulas_tem_horario():
    G = construir_grafo_conflitos([aula(1, 10, 1), aula(2, 10, 2), aula(3, 20, 1)])
    cores = resolver_coloracao_horarios(G)
    assert set(cores.keys()) == {1, 2, 3}


def test_vizinhos_cores_diferentes():
    G = construir_grafo_conflitos([aula(1, 10, 1), aula(2, 10, 2), aula(3, 20, 1), aula(4, 30, 4)])
    cores = resolver_coloracao_horarios(G)
    for a, b in G.edges:
        assert cores[a] != cores[b]


def test_sem_conflito_mesmo_horario():
    G = construir_grafo_conflitos([aula(1, 10, 1), aula(2, 20, 2)])
    cores = resolver_coloracao_horarios(G)
    assert cores[1] == cores[2]


def test_professor_com_3_aulas():
    # 3 aulas do mesmo prof -> precisa de 3 horarios diferentes
    G = construir_grafo_conflitos([aula(1, 10, 1), aula(2, 10, 2), aula(3, 10, 3)])
    cores = resolver_coloracao_horarios(G)
    assert len(set(cores.values())) == 3