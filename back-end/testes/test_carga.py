"""Carga de dados (database/data_ingestion). Rodar: python -m pytest testes -v"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.data_ingestion.data_ingestion import (  # noqa: E402
    codigo_horario,
    id_horario,
    ler_horario,
    montar_horarios,
    montar_tabelas,
    montar_tabelas_das_fontes,
    relatorio_em_markdown,
)
from database.repositorio import RepositorioSQLite, montar_dados  # noqa: E402

CABECALHO = ["professor", "codigo", "disciplina", "periodo", "eletiva", "horarios_atuais", "horarios_originais"]


def linha(n, *valores):
    return n, dict(zip(CABECALHO, valores))


def cp21(n, codigo, periodo, carga, tipo="Obrigatória"):
    return n, {"codigo": codigo, "descricao": "X", "periodo": str(periodo), "carga_horaria": str(carga), "tipo": tipo}


def test_ler_horario_no_padrao_dia_mais_faixa():
    assert ler_horario("2C") == (2, "C")
    assert ler_horario("6l") == (6, "L")
    for invalido in ("1A", "7B", "2M", "C2", ""):
        with pytest.raises(ValueError):
            ler_horario(invalido)


def test_ids_de_horario_vao_de_segunda_a_ate_sexta_l():
    assert id_horario(2, "A") == 1 and codigo_horario(1) == "2A"
    assert id_horario(6, "L") == 60 and codigo_horario(60) == "6L"
    assert len(montar_horarios()) == 60


def test_carga_das_fontes_reais():
    tabelas, rel = montar_tabelas_das_fontes()
    assert rel["totais"] == {"PRO_PROFESSOR": 26, "DIS_DISCIPLINA": 48, "HOR_HORARIO": 60,
                             "ALO_ALOCACAO": 48, "GRA_GRADE_HORARIA": 181}
    assert rel["linhas_ignoradas"] == []
    assert len(rel["horarios_modificados"]) == 7
    redes2 = next(d for d in tabelas["DIS_DISCIPLINA"] if d["DIS_CODIGO"] == "ELET0071")
    assert redes2["DIS_PERIODO"] == 8 and redes2["DIS_CARGA_HORARIA"] == 60


def test_horario_modificado_entra_com_o_horario_atual():
    tabelas, rel = montar_tabelas_das_fontes()
    bd = next(m for m in rel["horarios_modificados"] if m["codigo"] == "CCMP0005")
    assert bd["original"] == "2C 2D 5E 5F" and bd["atual"] == "2C 2D 5C 5D"
    alo = next(a for a in tabelas["ALO_ALOCACAO"]
               if a["DIS_ID"] == next(d["DIS_ID"] for d in tabelas["DIS_DISCIPLINA"] if d["DIS_CODIGO"] == "CCMP0005"))
    carregados = {codigo_horario(g["HOR_ID"]) for g in tabelas["GRA_GRADE_HORARIA"] if g["ALO_ID"] == alo["ALO_ID"]}
    assert carregados == {"2C", "2D", "5C", "5D"}


def test_carga_horaria_vem_do_cp21_e_eletiva_recebe_60h():
    tabelas, _ = montar_tabelas_das_fontes()
    por_codigo = {d["DIS_CODIGO"]: d for d in tabelas["DIS_DISCIPLINA"]}
    assert por_codigo["CCMP0116"]["DIS_CARGA_HORARIA"] == 30   # Teoria dos Grafos
    assert por_codigo["CCMP0119"]["DIS_CARGA_HORARIA"] == 90   # Eletrônica Digital
    assert por_codigo["CCMP0172"]["DIS_CARGA_HORARIA"] == 45   # Sistemas Multimídia
    assert por_codigo["CCMP0078"]["DIS_ELETIVA"] and por_codigo["CCMP0078"]["DIS_CARGA_HORARIA"] == 60


def test_relatorio_de_linhas_ignoradas():
    oferta = [
        linha(2, "ANA", "CCMP0001", "D1", "1", "Não", "2A 2B", ""),
        linha(3, "", "CCMP0002", "D2", "1", "Não", "2C", ""),                # sem professor
        linha(4, "BIA", "XX01", "D3", "1", "Não", "2C", ""),                 # código inválido
        linha(5, "BIA", "CCMP0003", "D3", "11", "Não", "2C", ""),            # período inválido
        linha(6, "ANA", "CCMP0001", "D1", "1", "Não", "3A", ""),             # repetida
        linha(7, "BIA", "CCMP0004", "D4", "2", "Não", "9Z 1A", ""),          # nenhum horário válido
        linha(8, "BIA", "CCMP0005", "D5", "2", "Não", "4A 4M", ""),          # um horário inválido
    ]
    tabelas, rel = montar_tabelas(oferta, [cp21(2, "CCMP0001", 1, 30), cp21(3, "ERRADO", 1, 30)])
    motivos = [(i["linha"], i["motivo"]) for i in rel["linhas_ignoradas"]]
    assert (3, "linha sem professor") in motivos
    assert (4, "código de disciplina inválido") in motivos
    assert (5, "período inválido (esperado 1 a 10)") in motivos
    assert (6, "professor x disciplina repetido") in motivos
    assert (7, "nenhum horário válido") in motivos
    assert any(i["arquivo"] == "perfil_cp21.csv" for i in rel["linhas_ignoradas"])
    assert [h["horario"] for h in rel["horarios_ignorados"] if h["linha"] == 8] == ["4M"]
    assert rel["totais"]["ALO_ALOCACAO"] == 2
    assert "Linhas ignoradas (6)" in relatorio_em_markdown(rel)


def test_divergencia_de_periodo_com_o_cp21_vai_para_o_relatorio():
    oferta = [linha(2, "ANA", "CCMP0001", "D1", "8", "Não", "2A 2B", "")]
    _, rel = montar_tabelas(oferta, [cp21(2, "CCMP0001", 10, 30)])
    campos = {d["campo"] for d in rel["divergencias_cp21"]}
    assert campos == {"período"}


def test_carga_gravada_e_lida_do_sqlite(tmp_path):
    tabelas, _ = montar_tabelas_das_fontes()
    repo = RepositorioSQLite(str(tmp_path / "grade.db"))
    assert repo.esta_vazio()
    repo.substituir_tudo(tabelas)
    dados = repo.carregar_dados()
    assert len(dados["alocacoes"]) == 48
    assert dados["alocacoes"][0]["DIS_DISCIPLINA"]["DIS_CODIGO"] == montar_dados(tabelas)["alocacoes"][0]["DIS_DISCIPLINA"]["DIS_CODIGO"]
    assert repo.semestres() == [{"semestre": "2026.2", "linhas": 181}]
