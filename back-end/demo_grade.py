"""
Demonstração local: gera a grade com os dados do Excel (sem usar o Supabase)
e mostra o resultado de forma legível. NÃO grava nada em lugar nenhum.

Como rodar, de dentro de back-end:
    python demo_grade.py             -> grade do 5º período, em texto
    python demo_grade.py 7           -> grade do 7º período
    python demo_grade.py --grafo     -> também desenha o grafo (abre uma janela
                                        e salva grafo_agendamento.png)
    python demo_grade.py --tudo4     -> assume 4 horários para todas as aulas
                                        (o padrão usa as durações da grade de
                                        exemplo do Excel: 2, 3, 4 ou 6)
    python demo_grade.py --manha     -> só usa os blocos A, B e C (nunca a tarde)
    python demo_grade.py --espalhado -> sem preferência de turno: usa manhã e tarde por igual
    python demo_grade.py --seguido   -> não espalha: Segunda A, B, C... (dia por dia)

Padrão: manhã primeiro; a tarde só entra quando uma aula não cabe na manhã.
"""
import os
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graphs.agendamento import gerar_grade  # noqa: E402

CAMINHO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "database", "data", "modelo_grade_professor.xlsx")
numeros = [a for a in sys.argv[1:] if a.isdigit()]
periodo_escolhido = int(numeros[0]) if numeros else 5
desenhar_grafo = "--grafo" in sys.argv

abas = pd.read_excel(CAMINHO, sheet_name=None)
prof, disc = abas["PRO_PROFESSOR"], abas["DI_DISCIPLINA"]
aloc, hor = abas["ALO_ALOCACAO"], abas["HO_HORARIO"]

# No Excel os números de identificação (ID) são a posição da linha: 1, 2, 3...
alocacoes = []
for i, r in enumerate(aloc.itertuples()):
    d = disc.loc[int(r.DI_ID) - 1]
    alocacoes.append({
        "ALO_ID": i + 1,
        "PRO_ID": int(r.PRO_ID),
        "PRO_NOME": prof.loc[int(r.PRO_ID) - 1, "PRO_NOME"],
        "DI_DISCIPLINA": {"DI_PERIODO": int(d.DI_PERIODO), "DI_DESCRICAO": d.DI_DESCRICAO},
    })
horarios = [{"HO_ID": i + 1, "HO_DIA": r.HO_DIA} for i, r in enumerate(hor.itertuples())]

# Durações (quantos horários cada aula tem por semana): vêm da grade de exemplo
# do Excel. No sistema final virão da carga horária da disciplina (CH / 15).
duracoes = None
if "--tudo4" not in sys.argv:
    duracoes = abas["GRA_GRADE_HORARIA"].groupby("ALO_ID").size().to_dict()

resultado = gerar_grade(
    alocacoes, horarios, "2026.2", duracoes=duracoes,
    espalhar="--seguido" not in sys.argv,
    letras_permitidas="ABC" if "--manha" in sys.argv else "ABCDEF",
    turnos=("ABCDEF",) if "--espalhado" in sys.argv else ("ABC", "DEF"),
)
blocos = {b["id"]: b for b in resultado["blocos"]}
colocacao = resultado["colocacao"]


def horario_bloco(b):
    ini = hor.loc[b["ho_ids"][0] - 1, "HO_FAIXA"][:5]
    fim = hor.loc[b["ho_ids"][-1] - 1, "HO_FAIXA"][-5:]
    return f"{ini}-{fim}"


por_bloco = Counter(i for ids in colocacao.values() for i in ids)
por_dia = Counter(blocos[ids[0]]["dia"] for ids in colocacao.values())
print(f"Aulas: {len(alocacoes)} | Sessões de 2 horários: {len(colocacao)} | "
      f"Blocos usados: {len(por_bloco)} de {len(blocos)} | "
      f"Máx. aulas ao mesmo tempo: {max(por_bloco.values())} | "
      f"Choques: {len(resultado['violacoes'])}")
print("Sessões por dia:", {d: por_dia[d] for d in ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]})

print(f"\n--- Grade do {periodo_escolhido}º período ---")
linhas = []
for s in resultado["sessoes"]:
    alo_id, n = s["ALO_ID"]
    a = alocacoes[alo_id - 1]
    if a["DI_DISCIPLINA"]["DI_PERIODO"] != periodo_escolhido:
        continue
    ids = colocacao[s["ALO_ID"]]
    primeiro = blocos[ids[0]]
    horarios_usados = [h for i in ids for h in blocos[i]["ho_ids"]][: s["SLOTS"]]
    ini = hor.loc[horarios_usados[0] - 1, "HO_FAIXA"][:5]
    fim = hor.loc[horarios_usados[-1] - 1, "HO_FAIXA"][-5:]
    letras = "+".join(blocos[i]["letra"] for i in ids)
    linhas.append((primeiro["ordem_dia"], primeiro["pos"], primeiro["dia"], letras, f"{ini}-{fim}",
                   a["DI_DISCIPLINA"]["DI_DESCRICAO"], a["PRO_NOME"]))
for _, _, dia, letra, hora, d, p in sorted(linhas):
    print(f"{dia:8} {letra:4} {hora}  {d}  ({p})")

# ---------------------------------------------------------------- desenho ----
if desenhar_grafo:
    import matplotlib.pyplot as plt
    import networkx as nx
    from matplotlib.lines import Line2D

    G = resultado["grafo"]
    dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    paleta = {d: plt.cm.tab10.colors[i] for i, d in enumerate(dias)}

    fig, ax = plt.subplots(figsize=(15, 9.5))
    pos = nx.spring_layout(G, k=0.15, seed=42)
    nx.draw_networkx_edges(G, pos, alpha=0.2, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=[paleta[blocos[colocacao[n][0]]["dia"]] for n in G.nodes()],
                           node_size=520, edgecolors="black", ax=ax)
    nx.draw_networkx_labels(G, pos, labels={n: f"{n[0]}\n" + "+".join(blocos[i]["letra"] for i in colocacao[n]) for n in G.nodes()},
                            font_size=7, font_weight="bold", ax=ax)
    legenda = [Line2D([0], [0], marker="o", color="w", markerfacecolor=paleta[d],
                      markeredgecolor="black", markersize=13, label=d) for d in dias]
    ax.legend(handles=legenda, title="Cor = dia da semana", loc="center left",
              bbox_to_anchor=(1.0, 0.5), fontsize=11, title_fontsize=12, frameon=False)
    ax.set_title("Cada bolinha é uma sessão de 2 horários: número da aula e letra do bloco (A a F). "
                 "Linha = não podem ser juntas.")
    ax.axis("off")
    plt.tight_layout()
    arquivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grafo_agendamento.png")
    plt.savefig(arquivo, dpi=110, bbox_inches="tight")
    print(f"\nImagem salva em: {arquivo}")
    plt.show()