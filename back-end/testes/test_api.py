"""API (main.py) com um banco SQLite temporário. Rodar: python -m pytest testes -v"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main  # noqa: E402
from database.repositorio import RepositorioSQLite  # noqa: E402


@pytest.fixture()
def cliente(tmp_path):
    main.ctx.iniciar(RepositorioSQLite(str(tmp_path / "api.db")))  # banco vazio: a carga roda sozinha
    with TestClient(main.app) as c:
        yield c


def test_dados_carregados_automaticamente(cliente):
    d = cliente.get("/api/dados").json()
    assert len(d["professores"]) == 26 and len(d["disciplinas"]) == 48
    assert d["semestres"] == [{"semestre": "2026.2", "linhas": 181}]


def test_grade_inicial_e_a_grade_atual_do_banco(cliente):
    g = cliente.get("/api/grade").json()
    assert g["origem"] == "Banco: grade 2026.2" and g["situacao"] == "completa"
    assert g["resumo"]["conflitos"] == 0


def test_gerar_e_ver_por_passos(cliente):
    g = cliente.post("/api/grade/gerar", json={"ordem": "dsatur"}).json()
    assert g["resumo"]["conflitos"] == 0 and g["total_passos"] == g["resumo"]["sessoes"]
    assert cliente.get("/api/grade", params={"passo": 0}).json()["situacao"] == "vazia"
    assert cliente.get("/api/grade", params={"passo": 5}).json()["resumo"]["coloridas"] == 5


def test_ordem_invalida(cliente):
    assert cliente.post("/api/grade/gerar", json={"ordem": "aleatoria"}).status_code == 400


def test_salvar_e_carregar(cliente):
    cliente.post("/api/grade/gerar", json={"ordem": "dsatur"})
    r = cliente.post("/api/grade/salvar", json={"semestre": "2027.1"}).json()
    assert r["linhas"] > 0 and {"semestre": "2027.1", "linhas": r["linhas"]} in r["semestres"]
    g = cliente.post("/api/grade/carregar", json={"semestre": "2027.1"}).json()
    assert g["origem"] == "Banco: grade 2027.1" and g["resumo"]["conflitos"] == 0
    assert cliente.post("/api/grade/carregar", json={"semestre": "1999.1"}).status_code == 404


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


def test_relatorio_da_carga(cliente):
    rel = cliente.get("/api/carga/relatorio").json()
    assert rel["linhas_ignoradas"] == [] and len(rel["horarios_modificados"]) == 7
