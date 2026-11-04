import json
import os
<<<<<<< HEAD
import networkx as nx


def dsatur(G):
    """
    Algoritmo DSATUR para coloração de grafos.
    """
    if len(G) == 0:
        return {}

    saturacao = {v: 0 for v in G.nodes()}
    graus = {v: G.degree(v) for v in G.nodes()}
    cores = {}

    primeiro_no = max(graus, key=graus.get)
    cores[primeiro_no] = 0

    for vizinho in G.neighbors(primeiro_no):
        saturacao[vizinho] += 1

    while len(cores) < len(G):
        nos_nao_coloridos = [v for v in G.nodes() if v not in cores]

        proximo_no = max(
            nos_nao_coloridos,
            key=lambda v: (saturacao[v], graus[v])
        )

        cores_vizinhos = {cores[v] for v in G.neighbors(proximo_no) if v in cores}
        cor = 0
        while cor in cores_vizinhos:
            cor += 1

        cores[proximo_no] = cor

        for vizinho in G.neighbors(proximo_no):
            if vizinho not in cores:
                cores_vizinhos_do_vizinho = {cores[v] for v in G.neighbors(vizinho) if v in cores}
                saturacao[vizinho] = len(cores_vizinhos_do_vizinho)

    return cores
=======

import networkx as nx

try:
    from graphs.coloracao import dsatur
except ImportError:  # quando executado de dentro da pasta graphs/
    from coloracao import dsatur
>>>>>>> 0c87cf57d56642c73ab74416f2bc2a81df31a1a5


def construir_grafo_conflitos(alocacoes):
    """
<<<<<<< HEAD
    Constrói o grafo de conflitos para a Grade Horária.
=======
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
>>>>>>> 0c87cf57d56642c73ab74416f2bc2a81df31a1a5
    """
    G = nx.Graph()

    # 1. Adicionar os Vértices (Nós)
    for alo in alocacoes:
        alo_id = alo.get("ALO_ID")
        pro_id = alo.get("PRO_ID")
<<<<<<< HEAD
        disciplina_info = alo.get("DI_DISCIPLINA", {}) or alo.get("DIS_DISCIPLINA", {}) or {}
        
        di_periodo = disciplina_info.get("DI_PERIODO") if isinstance(disciplina_info, dict) else None
=======
        disciplina_info = alo.get("DIS_DISCIPLINA", {})
        disciplina_info = disciplina_info if isinstance(disciplina_info, dict) else {}
>>>>>>> 0c87cf57d56642c73ab74416f2bc2a81df31a1a5

        G.add_node(
            alo_id,
            pro_id=pro_id,
            dis_periodo=disciplina_info.get("DIS_PERIODO"),
            eletiva=bool(disciplina_info.get("DIS_ELETIVA")),
        )

    # 2. Adicionar as Arestas (Incompatibilidades / Conflitos)
    nos = list(G.nodes(data=True))
    qtd_nos = len(nos)

    for i in range(qtd_nos):
        for j in range(i + 1, qtd_nos):
            id_a, attr_a = nos[i]
            id_b, attr_b = nos[j]

            mesmo_professor = (
                attr_a["pro_id"] is not None and
                attr_a["pro_id"] == attr_b["pro_id"]
            )

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


def construir_grafo_da_grade_salva(grade_horaria):
    """
<<<<<<< HEAD
    Instancia o resultado salvo no banco (tabela GRA_GRADE_HORARIA) em um grafo em memória.
=======
    Atende ao requisito da professora:
    Instancia a grade salva em um grafo, mantendo todas as faixas de cada alocação.
>>>>>>> 0c87cf57d56642c73ab74416f2bc2a81df31a1a5
    """
    G = nx.Graph()

    for item in grade_horaria:
        gra_id = item.get("GRA_ID")
        alo_id = item.get("ALO_ID")
        ho_id = item.get("HO_ID")

        if not G.has_node(alo_id):
            G.add_node(alo_id, gra_ids=[], ho_ids=[])
        G.nodes[alo_id]["gra_ids"].append(gra_id)
        G.nodes[alo_id]["ho_ids"].append(ho_id)

    return G


def resolver_coloracao_com_preferencias(G, preferencias_professores=None, param_N=2, total_cores_disponiveis=7):
    """
    Atende à demanda da Iteração 09:
    Algoritmo Guloso de Coloração que considera as preferências de horário dos professores
    e valida o parâmetro N de horários excedentes.
    """
    if preferencias_professores is None:
        preferencias_professores = {}

    agendamento = {}
    nos_ordenados = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)

    for no in nos_ordenados:
        pro_id = G.nodes[no].get("pro_id")
        cores_vizinhos = {agendamento[vizinho] for vizinho in G.neighbors(no) if vizinho in agendamento}

        # Preferências do professor para este nó
        prefs_prof = preferencias_professores.get(pro_id, [])

        # 1. Tentar alocar primeiro em uma cor/slot de PREFERÊNCIA do professor
        cor_escolhida = None
        for cor_pref in prefs_prof:
            if cor_pref not in cores_vizinhos and cor_pref < total_cores_disponiveis:
                cor_escolhida = cor_pref
                break

        # 2. Se nenhuma preferência for viável, aplica Busca Gulosa padrão
        if cor_escolhida is None:
            for cor_cand in range(total_cores_disponiveis):
                if cor_cand not in cores_vizinhos:
                    cor_escolhida = cor_cand
                    break

        agendamento[no] = cor_escolhida

    return agendamento


if __name__ == "__main__":
    import sys
    pasta_backend = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if pasta_backend not in sys.path:
        sys.path.insert(0, pasta_backend)

<<<<<<< HEAD
    from database.connection import connect
    
    supabase = getattr(connect, 'supabase', connect() if callable(connect) else connect)

    print("--- [Iteração 09] Testando Algoritmo Guloso com Preferências de Horário ---")
    
    if supabase:
        # Consulta ajustada aos campos existentes na tabela
        res = supabase.table("ALO_ALOCACAO").select("ALO_ID, PRO_ID, DI_DISCIPLINA(DI_PERIODO)").execute()
        alocacoes = res.data

        G = construir_grafo_conflitos(alocacoes)
        print(f"[OK] Grafo criado: {G.number_of_nodes()} Vértices e {G.number_of_edges()} Arestas.")

        # Teste do DSATUR
        res_dsatur = dsatur(G)
        print(f"[OK] DSATUR executado. Qtd de cores encontradas: {len(set(res_dsatur.values()))}")

        # Teste da Busca Gulosa com Preferências (Iteração 09)
        param_N = 2
        preferencias_mock = {
            1: [0, 1, 2],
            2: [2, 3, 4]
        }

        res_guloso = resolver_coloracao_com_preferencias(G, preferencias_professores=preferencias_mock, param_N=param_N)
        print(f"[OK] Busca Gulosa com Preferências executada. Qtd de cores utilizadas: {len(set(res_guloso.values()))}")
    else:
        print("Erro ao conectar ao Supabase.")
=======
    from graphs.coloracao import maior_clique
    from graphs.dados import BancoSupabase

    print("--- Testando a Modelagem em Grafos ---")
    alocacoes = BancoSupabase().carregar_dados()["alocacoes"]

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
>>>>>>> 0c87cf57d56642c73ab74416f2bc2a81df31a1a5
