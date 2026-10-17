"""Grafo <-> grade <-> banco (graphs/grade.py) com os dados reais. Rodar: python -m pytest testes -v"""
import os
import sys
from collections import Counter

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.data_ingestion.data_ingestion import montar_tabelas_das_fontes  # noqa: E402
from database.repositorio import RepositorioSQLite, montar_dados  # noqa: E402
from graphs.agendamento import validar_grade  # noqa: E402
from graphs.coloracao import dsatur, guloso, maior_clique, numero_de_cores  # noqa: E402
from graphs.grade import GradeEmMemoria  # noqa: E402
from graphs.graph import construir_grafo_conflitos  # noqa: E402

TABELAS, _ = montar_tabelas_das_fontes()
DADOS = montar_dados(TABELAS)


def test_grade_atual_da_coordenacao_nao_tem_conflitos_no_modelo():
    # Valida o modelo contra a realidade: eletivas do mesmo período podem coincidir.
    assert validar_grade(TABELAS["GRA_GRADE_HORARIA"], DADOS["alocacoes"]) == []
    grade = GradeEmMemoria.de_linhas(DADOS, TABELAS["GRA_GRADE_HORARIA"], "atual")
    assert grade.conflitos() == []


def test_duas_eletivas_do_mesmo_periodo_nao_tem_aresta_mas_obrigatoria_tem():
    G = construir_grafo_conflitos(DADOS["alocacoes"])
    alo = {a["DIS_DISCIPLINA"]["DIS_CODIGO"]: a["ALO_ID"] for a in DADOS["alocacoes"]}
    assert not G.has_edge(alo["CCMP0082"], alo["CCMP0023"])   # duas eletivas do 9º
    assert G.has_edge(alo["CCMP0082"], alo["CCMP0127"])       # eletiva x obrigatória do 9º


@pytest.mark.parametrize("ordem", ["dsatur", "alfabetica", "mais_conflitos"])
def test_grade_gerada_sem_choques_e_com_as_faixas_da_carga_horaria(ordem):
    grade = GradeEmMemoria.gerar(DADOS, ordem)
    linhas = grade.linhas("2027.1")
    assert validar_grade(linhas, DADOS["alocacoes"]) == []
    faixas = Counter(l["ALO_ID"] for l in linhas)
    for a in DADOS["alocacoes"]:
        assert faixas[a["ALO_ID"]] == a["DIS_DISCIPLINA"]["DIS_CARGA_HORARIA"] // 15


def test_dsatur_e_otimo_no_grafo_das_sessoes_e_guloso_nao():
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
    vizinho = next(s for s in estado["sessoes"]
                   if s["id"] != a["id"] and s["pro_id"] == a["pro_id"] and s["faixas"] == a["faixas"])
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


def test_grade_salva_no_banco_e_reinstanciada_como_grafo(tmp_path):
    repo = RepositorioSQLite(str(tmp_path / "grade.db"))
    repo.substituir_tudo(TABELAS)
    grade = GradeEmMemoria.gerar(repo.carregar_dados(), "dsatur")
    repo.salvar_grade("2027.1", grade.linhas("2027.1"))
    recarregada = GradeEmMemoria.de_linhas(repo.carregar_dados(), repo.carregar_grade("2027.1"), "banco")
    assert sorted((l["ALO_ID"], l["HOR_ID"]) for l in recarregada.linhas("x")) == \
        sorted((l["ALO_ID"], l["HOR_ID"]) for l in grade.linhas("x"))
    assert recarregada.conflitos() == []
