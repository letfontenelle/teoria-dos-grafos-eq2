"""Rodar de dentro de back-end:  python -m pytest testes -v"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphs.agendamento import (  # noqa: E402
    dividir_duracao,
    duracao_pela_carga_horaria,
    expandir_sessoes,
    gerar_grade,
    montar_blocos,
    validar_grade,
)

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]


def horarios_semana():
    """60 horários: 5 dias x 12 faixas, HO_ID de 1 a 60."""
    return [{"HO_ID": d * 12 + f + 1, "HO_DIA": dia} for d, dia in enumerate(DIAS) for f in range(12)]


def alo(alo_id, pro_id, periodo, nome=None):
    a = {"ALO_ID": alo_id, "PRO_ID": pro_id, "DI_DISCIPLINA": {"DI_PERIODO": periodo}}
    if nome:
        a["PRO_NOME"] = nome
    return a


def slots(r, alo_id):
    return {l["HO_ID"] for l in r["linhas"] if l["ALO_ID"] == alo_id}


def dias_da_aula(r, alo_id):
    por_id = {b["id"]: b for b in r["blocos"]}
    return [por_id[r["colocacao"][s["ALO_ID"]][0]]["dia"] for s in r["sessoes"] if s["ALO_ID"][0] == alo_id]


def test_dividir_duracao():
    assert dividir_duracao(4) == [2, 2]
    assert dividir_duracao(2) == [2]
    assert dividir_duracao(3) == [3]
    assert dividir_duracao(5) == [3, 2]
    assert dividir_duracao(6) == [2, 2, 2]


def test_montar_blocos_gera_30_blocos_de_2_com_letras_a_f():
    blocos = montar_blocos(horarios_semana())
    assert len(blocos) == 30
    assert all(len(b["ho_ids"]) == 2 for b in blocos)
    assert "".join(b["letra"] for b in blocos[:6]) == "ABCDEF"
    assert blocos[0]["ho_ids"] == [1, 2]  # bloco A = 07:10-08:50


def test_expandir_sessoes_divide_aula_de_4_horarios_em_duas_sessoes():
    sessoes = expandir_sessoes([alo(1, 1, 1)])
    assert [s["SLOTS"] for s in sessoes] == [2, 2]
    assert [s["ALO_ID"] for s in sessoes] == [(1, 0), (1, 1)]


def test_mesmo_professor_nao_fica_no_mesmo_horario():
    r = gerar_grade([alo(1, 10, 1), alo(2, 10, 2)], horarios_semana(), "2026.2")
    assert r["violacoes"] == []
    assert slots(r, 1).isdisjoint(slots(r, 2))


def test_mesmo_periodo_nao_fica_no_mesmo_horario():
    r = gerar_grade([alo(1, 1, 5), alo(2, 2, 5)], horarios_semana(), "2026.2")
    assert r["violacoes"] == []
    assert slots(r, 1).isdisjoint(slots(r, 2))


def test_aula_de_4_horarios_ocupa_4_horarios_em_dois_dias_diferentes():
    r = gerar_grade([alo(1, 1, 1)], horarios_semana(), "2026.2")
    assert len(slots(r, 1)) == 4
    assert len(set(dias_da_aula(r, 1))) == 2


def test_espalhar_coloca_aulas_sem_conflito_em_blocos_diferentes():
    r = gerar_grade([alo(1, 1, 1), alo(2, 2, 2), alo(3, 3, 3)], horarios_semana(), "2026.2")
    assert len(set(r["colocacao"].values())) == 6  # 3 aulas x 2 sessões, sem repetir bloco


def test_sem_espalhar_comeca_na_segunda_bloco_a():
    r = gerar_grade([alo(1, 1, 1), alo(2, 2, 2)], horarios_semana(), "2026.2", espalhar=False)
    assert 1 in slots(r, 1) and 2 in slots(r, 1)  # Segunda A = HO_ID 1 e 2


def test_ordem_alfabetica_por_professor():
    r = gerar_grade([alo(1, 1, 1, "ZULEIDE"), alo(2, 2, 2, "ADAO")], horarios_semana(),
                    "2026.2", espalhar=False)
    assert {1, 2} <= slots(r, 2)  # ADAO é o primeiro: fica em Segunda A


def test_letras_permitidas_so_de_manha():
    alocacoes = [alo(i, i, i) for i in range(1, 25)]
    r = gerar_grade(alocacoes, horarios_semana(), "2026.2", letras_permitidas="ABC")
    assert {b["letra"] for b in r["blocos"]} == {"A", "B", "C"}
    assert all(l["HO_ID"] % 12 in (1, 2, 3, 4, 5, 6) for l in r["linhas"])  # primeiras 6 faixas do dia


def test_erro_claro_quando_faltam_blocos():
    # 16 aulas do mesmo professor = 32 sessões, mas só existem 30 blocos.
    with pytest.raises(ValueError, match="não cabe"):
        gerar_grade([alo(i, 1, i) for i in range(1, 17)], horarios_semana(), "2026.2")


def test_validador_detecta_choque_de_professor():
    alocacoes = [alo(1, 10, 1), alo(2, 10, 2)]
    linhas = [{"GRA_SEMESTRE": "2026.2", "ALO_ID": 1, "HO_ID": 1},
              {"GRA_SEMESTRE": "2026.2", "ALO_ID": 2, "HO_ID": 1}]
    assert any("mesmo professor" in v for v in validar_grade(linhas, alocacoes))


def test_carga_horaria_define_aulas_por_semana():
    assert [duracao_pela_carga_horaria(ch) for ch in (30, 45, 60, 90)] == [2, 3, 4, 6]


def test_disciplina_de_60h_tem_4_horarios_e_de_30h_tem_2():
    a60 = {"ALO_ID": 1, "PRO_ID": 1, "DI_DISCIPLINA": {"DI_PERIODO": 1, "DI_CARGA_HORARIA": 60}}
    a30 = {"ALO_ID": 2, "PRO_ID": 2, "DI_DISCIPLINA": {"DI_PERIODO": 2, "DI_CARGA_HORARIA": 30}}
    r = gerar_grade([a60, a30], horarios_semana(), "2026.2")
    assert len(slots(r, 1)) == 4 and len(slots(r, 2)) == 2


def test_manha_primeiro_quando_cabe():
    r = gerar_grade([alo(i, i, i) for i in range(1, 11)], horarios_semana(), "2026.2")
    usados = {i for ids in r["colocacao"].values() for i in ids}
    assert {b["letra"] for b in r["blocos"] if b["id"] in usados} <= {"A", "B", "C"}


def test_tarde_so_quando_nao_cabe_na_manha():
    # 8 aulas do mesmo professor = 16 sessões que se bloqueiam; a manhã tem 15 blocos.
    r = gerar_grade([alo(i, 1, i) for i in range(1, 9)], horarios_semana(), "2026.2")
    por_id = {b["id"]: b for b in r["blocos"]}
    letras = [por_id[ids[0]]["letra"] for ids in r["colocacao"].values()]
    assert sum(l in "DEF" for l in letras) == 1
    assert r["violacoes"] == []


def test_aula_de_3_horarios_fica_seguida_no_mesmo_dia():
    r = gerar_grade([alo(1, 1, 1)], horarios_semana(), "2026.2", duracoes={1: 3})
    ids = sorted(slots(r, 1))
    assert len(ids) == 3
    assert ids == list(range(ids[0], ids[0] + 3))  # três horários consecutivos
    assert len(r["sessoes"]) == 1 and r["sessoes"][0]["SPAN"] == 2


def test_aula_de_3_horarios_nao_divide_bloco_com_conflito():
    # a de 3 horários ocupa dois blocos; a outra aula do mesmo professor não pode tocar em nenhum
    r = gerar_grade([alo(1, 1, 1), alo(2, 1, 2)], horarios_semana(), "2026.2", duracoes={1: 3, 2: 2})
    assert slots(r, 1).isdisjoint(slots(r, 2))
    assert r["violacoes"] == []