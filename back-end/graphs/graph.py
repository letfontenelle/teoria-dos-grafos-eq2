import networkx as nx

def construir_grafo_conflitos(alocacoes):
    """
    Constrói o Grafo de Conflitos para a Grade Horária.
    
    Parâmetros:
      alocacoes (list[dict]): Lista de dicionários vinda do Supabase (tabela ALO_ALOCACAO).
                              
    Retorna:
      nx.Graph: Grafo onde os nós são as alocações e as arestas representam conflitos de horário.
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

            # Regra 1: Conflito de Professor
            mesmo_professor = (
                attr_a["pro_id"] is not None and 
                attr_a["pro_id"] == attr_b["pro_id"]
            )

            # Regra 2: Conflito de Perfil Pleno / Curricular
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


def resolver_coloracao_horarios(G):
    """
    Aplica o algoritmo DSATUR (Busca Gulosa) para atribuir slots de horário (cores).
    """
    agendamento = nx.coloring.greedy_color(G, strategy="DSATUR")
    return agendamento


# Bloco de execução para teste direto do arquivo
if __name__ == "__main__":
    import sys
    import os
    
    # Adiciona a pasta 'back-end' ao sys.path
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
        # 1. Puxa as alocações
        res = supabase.table("ALO_ALOCACAO").select("ALO_ID, PRO_ID, DI_DISCIPLINA(DI_PERIODO)").execute()
        alocacoes = res.data

        # 2. Constrói o Grafo
        G = construir_grafo_conflitos(alocacoes)
        print(f"Vértices (Aulas) criados: {G.number_of_nodes()}")
        print(f"Arestas (Conflitos de Prof/Período) criadas: {G.number_of_edges()}")

        # 3. Executa a Busca Gulosa (DSATUR)
        resultado = resolver_coloracao_horarios(G)
        print("\nResultado da Atribuição de Horários (Cores):")
        print(resultado)

        # 4. Desenha e salva a imagem do Grafo
        try:
            import matplotlib.pyplot as plt
            cores_nos = [resultado[node] for node in G.nodes()]
            
            plt.figure(figsize=(14, 10))
            pos = nx.spring_layout(G, k=0.15, seed=42)
            nx.draw_networkx_nodes(G, pos, node_color=cores_nos, cmap=plt.cm.tab20, node_size=600, edgecolors='black')
            nx.draw_networkx_edges(G, pos, alpha=0.3)
            nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
            
            plt.title("Grafo de Conflitos de Horários (Cores = Slots de Tempo)")
            plt.axis("off")
            
            plt.savefig("grafo_conflitos.png", format="PNG", dpi=150)
            print("\nImagem 'grafo_conflitos.png' salva com sucesso!")
        except ImportError:
            print("\nAviso: Matplotlib não instalado. A imagem não foi gerada, mas o resultado textual está pronto.")
    else:
        print("Erro: Não foi possível conectar ao Supabase.")