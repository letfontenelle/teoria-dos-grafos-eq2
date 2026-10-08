import json
import os

import networkx as nx

try:
    from graphs.coloracao import dsatur
except ImportError:  # quando executado de dentro da pasta graphs/
    from coloracao import dsatur


def construir_grafo_conflitos(alocacoes):
    """
    Constrói o Grafo de Conflitos para a Grade Horária.

    Parâmetros:
      alocacoes (list[dict]): alocações (tabela ALO_ALOCACAO) com a disciplina
                              aninhada em DIS_DISCIPLINA, como vem do banco.

    Retorna:
      nx.Graph: Grafo onde os nós são as alocações e as arestas representam conflitos de horário.

    Regras de aresta:
      1. Mesmo professor: um professor não ministra duas aulas no mesmo horário.
      2. Mesmo período (perfil pleno): o aluno blocado precisa conseguir cursar
         todas as disciplinas do seu período. A exceção são duas ELETIVAS do
         mesmo período: o aluno escolhe algumas, então elas podem coincidir
         entre si (é o que a grade atual da coordenação faz).
    """
    G = nx.Graph()

    # 1. Adicionar os Vértices (Nós - V)
    for alo in alocacoes:
        alo_id = alo.get("ALO_ID")
        pro_id = alo.get("PRO_ID")
        disciplina_info = alo.get("DIS_DISCIPLINA", {})
        disciplina_info = disciplina_info if isinstance(disciplina_info, dict) else {}

        G.add_node(
            alo_id,
            pro_id=pro_id,
            dis_periodo=disciplina_info.get("DIS_PERIODO"),
            eletiva=bool(disciplina_info.get("DIS_ELETIVA")),
        )

    # 2. Adicionar as Arestas (Incompatibilidades / Conflitos - E)
    nos = list(G.nodes(data=True))
    qtd_nos = len(nos)

    for i in range(qtd_nos):
        for j in range(i + 1, qtd_nos):
            id_a, attr_a = nos[i]
            id_b, attr_b = nos[j]

            # Regra 1: Conflito de Professor
            mesmo_professor = (
                attr_a["pro_id"] is not None and
                attr_a["pro_id"] == attr_b["pro_id"]
            )

            # Regra 2: Conflito de Perfil Pleno / Curricular
            mesmo_periodo = (
                attr_a["dis_periodo"] is not None and
                attr_a["dis_periodo"] == attr_b["dis_periodo"] and
                not (attr_a["eletiva"] and attr_b["eletiva"])
            )

            if mesmo_professor or mesmo_periodo:
                motivo = "professor" if mesmo_professor else "perfil_pleno"
                if mesmo_professor and mesmo_periodo:
                    motivo = "professor_e_perfil_pleno"

                G.add_edge(id_a, id_b, motivo=motivo)

    return G


def resolver_coloracao_horarios(G):
    """
    Aplica o DSATUR (implementado pela equipe em coloracao.py) e devolve
    {nó: cor}, em que cada cor é um slot de horário.
    """
    cores, _ = dsatur(G)
    return cores


def grafo_em_json(G, cores=None):
    """Exporta o grafo (US-02: grafo exibido em tela ou exportado em JSON)."""
    return {
        "vertices": [{"id": n, **{k: v for k, v in d.items()}, "cor": (cores or {}).get(n)}
                     for n, d in G.nodes(data=True)],
        "arestas": [{"origem": a, "destino": b, "motivo": d.get("motivo")} for a, b, d in G.edges(data=True)],
    }


# Bloco de execução para teste direto do arquivo:
#   python graphs/graph.py   (de dentro de back-end)
# Lê o grafo do banco configurado (SQLite local por padrão), colore com DSATUR,
# exporta graphs/graph.json e desenha docs/img/grafo_conflitos.png.
if __name__ == "__main__":
    import sys

    pasta_backend = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if pasta_backend not in sys.path:
        sys.path.insert(0, pasta_backend)

    from database.repositorio import obter_repositorio
    from graphs.coloracao import maior_clique

    print("--- Testando a Modelagem em Grafos ---")
    repo = obter_repositorio()
    if repo.esta_vazio():
        from database.data_ingestion.data_ingestion import montar_tabelas_das_fontes
        repo.substituir_tudo(montar_tabelas_das_fontes()[0])
    alocacoes = repo.carregar_dados()["alocacoes"]

    G = construir_grafo_conflitos(alocacoes)
    print(f"Vértices (Aulas) criados: {G.number_of_nodes()}")
    print(f"Arestas (Conflitos de Prof/Período) criadas: {G.number_of_edges()}")

    resultado = resolver_coloracao_horarios(G)
    print(f"\nDSATUR usou {len(set(resultado.values()))} cores; maior clique = {maior_clique(G)}.")

    arquivo_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph.json")
    with open(arquivo_json, "w", encoding="utf-8") as f:
        json.dump(grafo_em_json(G, resultado), f, ensure_ascii=False, indent=1)
    print(f"Grafo exportado em {os.path.relpath(arquivo_json)}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        cores_nos = [resultado[node] for node in G.nodes()]
        rotulos = {a["ALO_ID"]: a["DIS_DISCIPLINA"]["DIS_CODIGO"] for a in alocacoes}

        plt.figure(figsize=(15, 10))
        pos = nx.spring_layout(G, k=0.35, seed=42)
        nx.draw_networkx_nodes(G, pos, node_color=cores_nos, cmap=plt.cm.tab10, node_size=700, edgecolors='black')
        nx.draw_networkx_edges(G, pos, alpha=0.25)
        nx.draw_networkx_labels(G, pos, labels=rotulos, font_size=6, font_weight='bold')

        plt.title("Grafo de conflitos (alocações). Cor = slot de horário pelo DSATUR da equipe")
        plt.axis("off")
        arquivo_png = os.path.join(pasta_backend, "..", "docs", "img", "grafo_conflitos.png")
        os.makedirs(os.path.dirname(arquivo_png), exist_ok=True)
        plt.savefig(arquivo_png, format="PNG", dpi=130, bbox_inches="tight")
        print(f"Imagem salva em {os.path.relpath(arquivo_png)}")
    except ImportError:
        print("\nAviso: Matplotlib não instalado. A imagem não foi gerada, mas o resultado textual está pronto.")
