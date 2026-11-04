"""
Algoritmos de coloração de vértices implementados pela equipe.

O NetworkX é usado só como estrutura de grafo (vértices, arestas, vizinhos):
a escolha das cores é feita aqui, como definido na Iteração 02 (os algoritmos
de coloração são o objeto da disciplina).

Referência: Vieira, M. R. A. "Heurística Matemática Aplicada ao Problema da
Coloração de Grafos", relatório de IC, UFOP, 2018 (material da Iteração 06),
seção 4.3.1, e Brélaz, D. "New methods to color the vertices of a graph", 1979.

  guloso(G, ordem)  cada vértice, na ordem dada, recebe a menor cor que
                    nenhum vizinho já colorido usa.
  dsatur(G)         a cada passo escolhe o vértice ainda sem cor com maior grau
                    de saturação (quantidade de cores diferentes entre seus
                    vizinhos); empate: maior grau; depois menor id. Ele recebe
                    a menor cor disponível.

Os dois devolvem (cores, passos): cores = {vértice: cor 0, 1, 2...} e
passos = lista de (vértice, cor) na ordem em que foram coloridos, que permite
mostrar a coloração parcial (grafo sem cor -> parcialmente colorido -> completo).
"""
import networkx as nx


def _chave_id(v):
    """Ordena ids de tipos diferentes (int, tupla, str) de forma estável."""
    return (str(type(v).__name__), v if isinstance(v, (int, float, str, tuple)) else str(v))


def menor_cor_disponivel(G, v, cores):
    usadas = {cores[u] for u in G[v] if u in cores}
    cor = 0
    while cor in usadas:
        cor += 1
    return cor


def guloso(G, ordem=None):
    """Coloração gulosa sequencial. ordem: sequência de vértices (padrão: ordem de inserção)."""
    cores, passos = {}, []
    for v in (ordem if ordem is not None else list(G.nodes)):
        cores[v] = menor_cor_disponivel(G, v, cores)
        passos.append((v, cores[v]))
    return cores, passos


def saturacao(G, v, cores):
    """Grau de saturação: número de cores distintas entre os vizinhos já coloridos."""
    return len({cores[u] for u in G[v] if u in cores})


def dsatur(G):
    """DSATUR de Brélaz (1979), com o desempate da referência: saturação, grau, id."""
    cores, passos = {}, []
    sem_cor = set(G.nodes)
    while sem_cor:
        v = min(sem_cor, key=lambda x: (-saturacao(G, x, cores), -G.degree(x), _chave_id(x)))
        cores[v] = menor_cor_disponivel(G, v, cores)
        passos.append((v, cores[v]))
        sem_cor.remove(v)
    return cores, passos


def conflitos_da_coloracao(G, cores):
    """Arestas cujos dois extremos têm a mesma cor. Lista vazia = coloração própria."""
    return [(a, b) for a, b in G.edges if a in cores and b in cores and cores[a] == cores[b]]


def numero_de_cores(cores):
    return len(set(cores.values()))


def maior_clique(G):
    """
    Tamanho da maior clique: limite inferior do número cromático (todas as
    aulas de uma clique precisam de cores diferentes). Se uma coloração usa
    exatamente esse número de cores, ela é ótima.
    """
    if G.number_of_nodes() == 0:
        return 0
    return max(len(c) for c in nx.find_cliques(G))


def resumo_coloracao(G, algoritmo="dsatur"):
    """Colore o grafo e devolve números para comparar com o limite inferior."""
    cores, passos = dsatur(G) if algoritmo == "dsatur" else guloso(G)
    k, w = numero_de_cores(cores), maior_clique(G)
    return {"algoritmo": algoritmo, "cores": cores, "passos": passos, "numero_de_cores": k,
            "maior_clique": w, "otima": k == w, "conflitos": conflitos_da_coloracao(G, cores)}
