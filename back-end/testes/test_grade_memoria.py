"""Grafo <-> grade <-> banco (graphs/grade.py) com os dados da equipe de dados. Rodar: python -m pytest testes -v"""
import os
import sys
from collections import Counter

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphs.agendamento import validar_grade  # noqa: E402
from graphs.coloracao import dsatur, guloso, maior_clique, numero_de_cores  # noqa: E402
from graphs.dados import BancoSupabase, linhas_da_grade, montar_dados, tabelas_da_planilha  # noqa: E402
from graphs.grade import GradeEmMemoria  # noqa: E402
from supabase_falso import ClienteSupabaseFalso  # noqa: E402

TABELAS = tabelas_da_planilha()
DADOS = montar_dados(TABELAS)
ATUAL = linhas_da_grade(TABELAS, "2026.2")


def test_tabelas_da_equipe_de_dados_viram_o_formato_do_grafo():
    horarios = {h["HOR_ID"]: h for h in DADOS["horarios"]}
    assert (horarios[1]["HOR_DIA"], horarios[1]["HOR_FAIXA"], horarios[1]["HOR_INICIO"]) == (2, "A", "07:10")
    assert (horarios[60]["HOR_DIA"], horarios[60]["HOR_FAIXA"], horarios[60]["HOR_FIM"]) == (6, "L", "17:10")
    # Carga horária = faixas da disciplina na grade atual x 15h (somando os professores que a dividem).
    faixas = Counter(l["ALO_ID"] for l in ATUAL)
    for d in DADOS["disciplinas"]:
        alocacoes = [a["ALO_ID"] for a in DADOS["alocacoes"] if a["DIS_ID"] == d["DIS_ID"]]
        assert d["DIS_CARGA_HORARIA"] == 15 * sum(faixas[a] for a in alocacoes)


def test_grade_atual_so_tem_choques_entre_disciplinas_do_mesmo_periodo():
    # O banco não diz quais disciplinas são eletivas; as que a coordenação põe juntas aparecem como choque.
    violacoes = validar_grade(ATUAL, DADOS["alocacoes"])
    assert violacoes and all("mesmo período" in v for v in violacoes)


@pytest.mark.parametrize("ordem", ["dsatur", "alfabetica", "mais_conflitos"])
def test_grade_gerada_sem_choques_e_com_as_faixas_da_carga_horaria(ordem):
    grade = GradeEmMemoria.gerar(DADOS, ordem)
    linhas = grade.linhas("2027.1")
    assert validar_grade(linhas, DADOS["alocacoes"]) == []
    faixas = Counter(l["ALO_ID"] for l in linhas)
    for a in DADOS["alocacoes"]:
        assert faixas[a["ALO_ID"]] == a["DIS_DISCIPLINA"]["DIS_CARGA_HORARIA"] // 15


def test_dsatur_atinge_a_maior_clique_no_grafo_das_sessoes():
    G = GradeEmMemoria.gerar(DADOS, "dsatur").G
    clique = maior_clique(G)
    assert numero_de_cores(dsatur(G)[0]) == clique
    assert numero_de_cores(guloso(G)[0]) >= clique


def test_grafo_sem_cor_parcial_e_completo_viram_grade_vazia_parcial_e_completa():
    grade = GradeEmMemoria.gerar(DADOS, "dsatur")
    vazia, parcial, completa = grade.estado(0), grade.estado(10), grade.estado()
    assert vazia["situacao"] == "vazia" and not any(s["horarios"] for s in vazia["sessoes"])
    assert parcial["situacao"] == "parcial" and sum(s["colorida"] for s in parcial["sessoes"]) == 10
    assert completa["situacao"] == "completa" and all(s["colorida"] for s in completa["sessoes"])


def test_mover_sessao_troca_a_cor_do_vertice_e_aponta_conflito():
    grade = GradeEmMemoria.gerar(DADOS, "dsatur")
    estado = grade.estado()
    a = estado["sessoes"][0]
    vizinho = next(s for s in estado["sessoes"]  # mesmo professor, outra disciplina
                   if s["alo_id"] != a["alo_id"] and s["pro_id"] == a["pro_id"] and s["faixas"] == a["faixas"])
    dia, faixa = int(vizinho["rotulos"][0][0]), vizinho["rotulos"][0][1]
    conflitos = grade.mover(a["id"], dia, faixa)
    assert any({c["a"], c["b"]} == {a["id"], vizinho["id"]} and c["motivo"].startswith("professor")
               for c in conflitos)
    assert grade.estado()["resumo"]["conflitos"] >= 1


def test_mover_para_fora_do_dia_e_recusado():
    grade = GradeEmMemoria.gerar(DADOS, "dsatur")
    sessao = next(s for s in grade.estado()["sessoes"] if s["faixas"] == 2)
    with pytest.raises(ValueError):
        grade.mover(sessao["id"], 2, "L")


def test_grade_salva_no_banco_e_reinstanciada_como_grafo():
    cliente = ClienteSupabaseFalso(tabelas_da_planilha())
    repo = BancoSupabase(cliente)
    grade = GradeEmMemoria.gerar(repo.carregar_dados(), "dsatur")
    repo.salvar_grade("2027.1", grade.linhas("2027.1"))
    repo.salvar_grade("2027.1", grade.linhas("2027.1"))  # salvar de novo substitui, não duplica
    recarregada = GradeEmMemoria.de_linhas(repo.carregar_dados(), repo.carregar_grade("2027.1"), "banco")
    assert sorted((l["ALO_ID"], l["HOR_ID"]) for l in recarregada.linhas("x")) == \
        sorted((l["ALO_ID"], l["HOR_ID"]) for l in grade.linhas("x"))
    assert recarregada.conflitos() == []
    gravadas = [g for g in cliente.tabelas["GRA_GRADE_HORARIA"] if g["GRA_SEMESTRE"] == "2027.1"]
    assert len(gravadas) == len(grade.linhas("x")) and min(g["GRA_ID"] for g in gravadas) > 179
    assert repo.semestres()[0] == {"semestre": "2026.2", "linhas": 179}


def test_grade_da_carga_nao_e_sobrescrita():
    repo = BancoSupabase(ClienteSupabaseFalso(tabelas_da_planilha()))
    with pytest.raises(ValueError):
        repo.salvar_grade("2026.2", [])
