"""API (main.py) com o Supabase simulado em memória (dados da planilha). Rodar: python -m pytest testes -v"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main  # noqa: E402
from graphs.dados import BancoSupabase, tabelas_da_planilha  # noqa: E402
from supabase_falso import ClienteSupabaseFalso  # noqa: E402


@pytest.fixture()
def cliente():
    main.ctx.iniciar(BancoSupabase(ClienteSupabaseFalso(tabelas_da_planilha())))
    with TestClient(main.app) as c:
        yield c


def test_dados_das_tabelas_da_equipe_de_dados(cliente):
    d = cliente.get("/api/dados").json()
    assert len(d["professores"]) == 26 and len(d["disciplinas"]) == 47
    assert d["semestres"] == [{"semestre": "2026.2", "linhas": 179}]
    assert [f["faixa"] for f in d["faixas"]] == list("ABCDEFGHIJKL")


def test_grade_inicial_e_a_grade_atual_do_banco(cliente):
    g = cliente.get("/api/grade").json()
    assert g["origem"] == "Banco: grade 2026.2" and g["situacao"] == "completa"


def test_gerar_e_ver_por_passos(cliente):
    g = cliente.post("/api/grade/gerar", json={"ordem": "dsatur"}).json()
    assert g["resumo"]["conflitos"] == 0 and g["total_passos"] == g["resumo"]["sessoes"]
    assert cliente.get("/api/grade", params={"passo": 0}).json()["situacao"] == "vazia"
    assert cliente.get("/api/grade", params={"passo": 5}).json()["resumo"]["coloridas"] == 5


def test_ordem_invalida(cliente):
    assert cliente.post("/api/grade/gerar", json={"ordem": "aleatoria"}).status_code == 400


def test_api_gera_grade_priorizando_preferencias_e_valida_parametro_n():
    class RepoTeste:
        descricao = "Teste"

        def carregar_dados(self):
            faixas = [
                ("07:10", "08:00"), ("08:00", "08:50"), ("08:50", "09:40"),
                ("09:40", "10:30"), ("10:30", "11:20"), ("11:20", "12:10"),
                ("12:10", "13:00"), ("13:00", "13:50"), ("13:50", "14:40"),
                ("14:40", "15:30"), ("15:30", "16:20"), ("16:20", "17:10"),
            ]
            horarios = [
                {"HOR_ID": dia * 12 + i + 1, "HOR_DIA": dia, "HOR_FAIXA": letra,
                 "HOR_INICIO": inicio, "HOR_FIM": fim}
                for dia in range(2, 7)
                for i, (letra, (inicio, fim)) in enumerate(zip("ABCDEFGHIJKL", faixas))
            ]
            disciplina = {
                "DIS_ID": 1, "DIS_CODIGO": "TST", "DIS_DESCRICAO": "Teste",
                "DIS_PERIODO": 1, "DIS_CARGA_HORARIA": 30,
            }
            alocacao = {
                "ALO_ID": 1, "PRO_ID": 10, "DIS_ID": 1, "PRO_NOME": "Professora",
                "DIS_DISCIPLINA": disciplina,
            }
            return {
                "professores": [{"PRO_ID": 10, "PRO_NOME": "Professora"}],
                "disciplinas": [disciplina], "horarios": horarios, "alocacoes": [alocacao],
            }

        def carregar_grade(self, _semestre):
            return []

    main.ctx.iniciar(RepoTeste())
    with TestClient(main.app) as c:
        pedido = {"ordem": "dsatur", "param_N": 1, "preferencias_professores": {"10": ["2A", "2B", "2C"]}}
        resposta = c.post("/api/grade/gerar", json=pedido)
        assert resposta.status_code == 200
        grade = resposta.json()
        assert grade["origem"].endswith("(com preferências de horário)")
        assert grade["sessoes"][0]["rotulos"] == ["2A", "2B"]

        sem_n = c.post("/api/grade/gerar", json={**pedido, "param_N": None})
        assert sem_n.status_code == 422 and "valor de N" in sem_n.json()["detail"]
        abaixo_do_minimo = c.post(
            "/api/grade/gerar",
            json={**pedido, "preferencias_professores": {"10": ["2A", "2B"]}},
        )
        assert abaixo_do_minimo.status_code == 422 and "pelo menos 3 horários" in abaixo_do_minimo.json()["detail"]
        apos_13 = c.post(
            "/api/grade/gerar",
            json={**pedido, "preferencias_professores": {"10": ["2A", "2B", "2H"]}},
        )
        assert apos_13.status_code == 422 and "após 13:00" in apos_13.json()["detail"]


def test_salvar_e_carregar(cliente):
    cliente.post("/api/grade/gerar", json={"ordem": "dsatur"})
    r = cliente.post("/api/grade/salvar", json={"semestre": "2027.1"}).json()
    assert r["linhas"] > 0 and {"semestre": "2027.1", "linhas": r["linhas"]} in r["semestres"]
    g = cliente.post("/api/grade/carregar", json={"semestre": "2027.1"}).json()
    assert g["origem"] == "Banco: grade 2027.1" and g["resumo"]["conflitos"] == 0
    assert cliente.post("/api/grade/carregar", json={"semestre": "1999.1"}).status_code == 404


def test_nao_sobrescreve_a_grade_da_carga(cliente):
    cliente.post("/api/grade/gerar", json={"ordem": "dsatur"})
    assert cliente.post("/api/grade/salvar", json={"semestre": "2026.2"}).status_code == 400
    assert cliente.get("/api/dados").json()["semestres"] == [{"semestre": "2026.2", "linhas": 179}]


def test_mover_cria_conflito_visivel(cliente):
    g = cliente.post("/api/grade/gerar", json={"ordem": "dsatur"}).json()
    a = g["sessoes"][0]
    b = next(s for s in g["sessoes"] if s["id"] != a["id"] and s["pro_id"] == a["pro_id"] and s["faixas"] == a["faixas"])
    r = cliente.post("/api/grade/mover", json={"sessao": a["id"], "dia": int(b["rotulos"][0][0]),
                                               "faixa": b["rotulos"][0][1]}).json()
    assert r["conflitos_da_sessao"] and r["editada"] is True
    assert cliente.post("/api/grade/mover", json={"sessao": "999-0", "dia": 2, "faixa": "A"}).status_code == 404


def test_grafo_e_coloracao(cliente):
    grafo = cliente.get("/api/grafo").json()
    assert grafo["vertices"] and grafo["arestas"]
    c = cliente.get("/api/grafo/coloracao", params={"nivel": "alocacoes"}).json()
    assert c["numero_de_cores"] == c["maior_clique"] and c["otima"]
