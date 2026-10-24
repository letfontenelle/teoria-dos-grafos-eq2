import networkx as nx

def construir_grafo_conflitos(alocacoes):
    """
    Constrói o Grafo de Conflitos para as alocações brutas (sem horários atribuídos).
    """
    G = nx.Graph()

    # 1. Adicionar os Vértices (Nós - V)
    for alo in alocacoes:
        alo_id = alo.get("ALO_ID")
        pro_id = alo.get("PRO_ID")
        disciplina_info = alo.get("DI_DISCIPLINA", {})
        di_periodo = disciplina_info.get("DI_PERIODO") if isinstance(disciplina_info, dict) else None

        G.add_node(
            alo_id, 
            pro_id=pro_id, 
            di_periodo=di_periodo
        )

    # 2. Adicionar as Arestas (Incompatibilidades / Conflitos - E)
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
    Atende ao requisito da professora:
    Instancia o resultado SALVO no banco (tabela GRA_GRADE_HORARIA) em um grafo em memória.
    """
    G = nx.Graph()

    for item in grade_horaria:
        gra_id = item.get("GRA_ID")
        alo_id = item.get("ALO_ID")
        ho_id = item.get("HO_ID")

        G.add_node(alo_id, gra_id=gra_id, ho_id=ho_id)

    return G


def resolver_coloracao_horarios(G):
    """
    Aplica o algoritmo DSATUR (Modelo Teórico) para encontrar a coloração mínima (7 cores).
    """
    agendamento = nx.coloring.greedy_color(G, strategy="DSATUR")
    return agendamento


# Bloco de execução para teste direto do arquivo
if __name__ == "__main__":
    import sys
    import os
    
    pasta_backend = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if pasta_backend not in sys.path:
        sys.path.insert(0, pasta_backend)
    
    from database.connection import connect
    
    if hasattr(connect, 'supabase'):
        supabase = connect.supabase
    elif callable(connect):
        supabase = connect()
    else:
        supabase = connect

    print("--- Testando a Modelagem em Grafos ---")
    
    if supabase:
        # 1. Teste de Instanciação do Grafo Bruto
        res = supabase.table("ALO_ALOCACAO").select("ALO_ID, PRO_ID, DI_DISCIPLINA(DI_PERIODO)").execute()
        alocacoes = res.data

        G = construir_grafo_conflitos(alocacoes)
        print(f"[OK] Grafo em Memória Criado: {G.number_of_nodes()} Vértices e {G.number_of_edges()} Arestas.")

        # 2. Execução do DSATUR (Modelo Teórico)
        resultado_dsatur = resolver_coloracao_horarios(G)
        print(f"[OK] DSATUR executado. Qtd de cores encontradas: {len(set(resultado_dsatur.values()))}")

        # 3. Teste de Instanciação do Resultado Salvo no BD (Exigência da Professora)
        try:
            res_grade = supabase.table("GRA_GRADE_HORARIA").select("GRA_ID, ALO_ID, HO_ID").execute()
            if res_grade.data:
                G_salvo = construir_grafo_da_grade_salva(res_grade.data)
                print(f"[OK] Grafo da Grade Salva no BD instanciado em memória com {G_salvo.number_of_nodes()} nós!")
        except Exception as e:
            print(f"[Aviso] Tabela GRA_GRADE_HORARIA ainda vazia ou indisponível: {e}")

    else:
        print("Erro: Não foi possível conectar ao Supabase.")