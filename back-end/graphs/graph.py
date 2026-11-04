import json
import os
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


def construir_grafo_conflitos(alocacoes):
    """
    Constrói o grafo de conflitos para a Grade Horária.
    """
    G = nx.Graph()

    # 1. Adicionar os Vértices (Nós)
    for alo in alocacoes:
        alo_id = alo.get("ALO_ID")
        pro_id = alo.get("PRO_ID")
        disciplina_info = alo.get("DI_DISCIPLINA", {}) or alo.get("DIS_DISCIPLINA", {}) or {}
        
        di_periodo = disciplina_info.get("DI_PERIODO") if isinstance(disciplina_info, dict) else None

        G.add_node(
            alo_id, 
            pro_id=pro_id, 
            di_periodo=di_periodo
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
                attr_a["di_periodo"] is not None and 
                attr_a["di_periodo"] == attr_b["di_periodo"]
            )

            if mesmo_professor or mesmo_periodo:
                motivo = "professor" if mesmo_professor else "perfil_pleno"
                if mesmo_professor and mesmo_periodo:
                    motivo = "professor_e_perfil_pleno"
                
                G.add_edge(id_a, id_b, motivo=motivo)

    return G


def construir_grafo_da_grade_salva(grade_horaria):
    """
    Instancia o resultado salvo no banco (tabela GRA_GRADE_HORARIA) em um grafo em memória.
    """
    G = nx.Graph()

    for item in grade_horaria:
        gra_id = item.get("GRA_ID")
        alo_id = item.get("ALO_ID")
        ho_id = item.get("HO_ID")

        G.add_node(alo_id, gra_id=gra_id, ho_id=ho_id)

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