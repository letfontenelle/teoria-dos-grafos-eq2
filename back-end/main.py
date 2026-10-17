"""
API da grade horária (FastAPI) e servidor do front-end.

Como rodar, de dentro de back-end:
    uvicorn main:app --reload
e abrir http://localhost:8000 (a documentação da API fica em /docs).

Na primeira execução com o banco vazio, a carga de dados roda sozinha a
partir de database/data (GradeProfessor + CP21).
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database.data_ingestion.data_ingestion import DIAS, FAIXAS, SEMESTRE_OFERTA, montar_tabelas_das_fontes
from database.repositorio import obter_repositorio
from graphs.agendamento import ORDENS
from graphs.coloracao import resumo_coloracao
from graphs.graph import construir_grafo_conflitos
from graphs.grade import NOMES_ORDEM, GradeEmMemoria

PASTA_FRONT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "front-end"))

class Contexto:
    """Banco e grade em memória compartilhados pelas rotas."""

    def __init__(self):
        self.repo = None
        self.dados = None
        self.grade = None

    def iniciar(self, repo=None):
        self.repo = repo or obter_repositorio()
        if self.repo.esta_vazio():
            self.repo.substituir_tudo(montar_tabelas_das_fontes()[0])
        self.dados = self.repo.carregar_dados()
        linhas = self.repo.carregar_grade(SEMESTRE_OFERTA)
        self.grade = GradeEmMemoria.de_linhas(self.dados, linhas, f"Banco: grade {SEMESTRE_OFERTA}")

    def exigir_grade(self):
        if self.grade is None:
            raise HTTPException(409, "Nenhuma grade em memória: gere ou carregue uma grade.")
        return self.grade


ctx = Contexto()


@asynccontextmanager
async def _ciclo_de_vida(_app):
    if ctx.repo is None:
        ctx.iniciar()
    yield


app = FastAPI(title="Grade horária por coloração de grafos — Equipe 02",
              description="Carga de dados, grafo de conflitos, coloração (DSATUR) e grade horária.",
              lifespan=_ciclo_de_vida)


class PedidoGerar(BaseModel):
    ordem: str = "dsatur"


class PedidoSemestre(BaseModel):
    semestre: str


class PedidoMover(BaseModel):
    sessao: str
    dia: int
    faixa: str


# ------------------------------------------------------------------ dados --
@app.get("/api/saude")
def saude():
    return {"ok": True, "banco": ctx.repo.descricao if ctx.repo else None}


@app.get("/api/dados")
def dados():
    """Professores, disciplinas, faixas de horário, períodos e semestres gravados."""
    d = ctx.dados
    return {
        "professores": d["professores"],
        "disciplinas": d["disciplinas"],
        "alocacoes": [{"ALO_ID": a["ALO_ID"], "PRO_ID": a["PRO_ID"], "DIS_ID": a["DIS_ID"]} for a in d["alocacoes"]],
        "dias": [{"dia": n, "nome": nome} for n, nome in DIAS.items()],
        "faixas": [{"faixa": f, "inicio": i, "fim": t} for f, i, t in FAIXAS],
        "periodos": sorted({x["DIS_PERIODO"] for x in d["disciplinas"]}),
        "semestres": ctx.repo.semestres(),
        "ordens": [{"valor": o, "nome": NOMES_ORDEM[o]} for o in ORDENS],
        "banco": ctx.repo.descricao,
    }


@app.get("/api/carga/relatorio")
def relatorio_carga():
    """Relatório da carga: linhas ignoradas, horários modificados e divergências com o CP21."""
    return montar_tabelas_das_fontes()[1]


# ------------------------------------------------------------------ grade --
@app.get("/api/grade")
def grade_atual(passo: int | None = None):
    """Grade em memória. passo=k mostra só os k primeiros vértices coloridos."""
    return ctx.exigir_grade().estado(passo)


@app.post("/api/grade/gerar")
def gerar(pedido: PedidoGerar):
    if pedido.ordem not in ORDENS:
        raise HTTPException(400, f"ordem inválida; use uma de {list(ORDENS)}")
    try:
        ctx.grade = GradeEmMemoria.gerar(ctx.dados, pedido.ordem)
    except ValueError as erro:
        raise HTTPException(422, str(erro))
    return ctx.grade.estado()


@app.post("/api/grade/carregar")
def carregar(pedido: PedidoSemestre):
    linhas = ctx.repo.carregar_grade(pedido.semestre)
    if not linhas:
        raise HTTPException(404, f"Nenhuma grade salva para o semestre {pedido.semestre}.")
    ctx.grade = GradeEmMemoria.de_linhas(ctx.dados, linhas, f"Banco: grade {pedido.semestre}")
    return ctx.grade.estado()


@app.post("/api/grade/mover")
def mover(pedido: PedidoMover):
    """Edição no front: a sessão muda de lugar e o vértice muda de cor no grafo."""
    grade = ctx.exigir_grade()
    try:
        novos = grade.mover(pedido.sessao, pedido.dia, pedido.faixa)
    except KeyError as erro:
        raise HTTPException(404, str(erro))
    except ValueError as erro:
        raise HTTPException(422, str(erro))
    estado = grade.estado()
    estado["conflitos_da_sessao"] = novos
    return estado


@app.post("/api/grade/salvar")
def salvar(pedido: PedidoSemestre):
    """Grava a grade em memória na GRA_GRADE_HORARIA (substitui a do semestre)."""
    semestre = pedido.semestre.strip()
    if not semestre:
        raise HTTPException(400, "Informe o semestre.")
    grade = ctx.exigir_grade()
    n = ctx.repo.salvar_grade(semestre, grade.linhas(semestre))
    grade.origem = f"Banco: grade {semestre}"
    grade.editada = False
    return {"semestre": semestre, "linhas": n, "conflitos": len(grade.conflitos()),
            "semestres": ctx.repo.semestres()}


# ------------------------------------------------------------------ grafo --
@app.get("/api/grafo")
def grafo():
    """Grafo de conflitos das sessões da grade em memória (vértices, arestas, cor atual)."""
    return ctx.exigir_grade().grafo()


@app.get("/api/grafo/coloracao")
def coloracao(algoritmo: str = "dsatur", nivel: str = "sessoes"):
    """
    Coloração pura (sem preferências de turno) para comparar com o limite
    inferior da maior clique. nivel: "alocacoes" (1 vértice por professor x
    disciplina) ou "sessoes" (1 vértice por bloco de aula).
    """
    if algoritmo not in ("dsatur", "guloso"):
        raise HTTPException(400, "algoritmo deve ser dsatur ou guloso")
    if nivel == "alocacoes":
        G = construir_grafo_conflitos(ctx.dados["alocacoes"])
    elif nivel == "sessoes":
        G = GradeEmMemoria.gerar(ctx.dados, "dsatur").G
    else:
        raise HTTPException(400, "nivel deve ser alocacoes ou sessoes")
    r = resumo_coloracao(G, algoritmo)
    rotulo = (lambda n: str(n)) if nivel == "alocacoes" else (lambda n: f"{n[0]}-{n[1]}")
    return {"algoritmo": algoritmo, "nivel": nivel, "vertices": G.number_of_nodes(), "arestas": G.number_of_edges(),
            "numero_de_cores": r["numero_de_cores"], "maior_clique": r["maior_clique"], "otima": r["otima"],
            "conflitos": len(r["conflitos"]), "passos": [[rotulo(v), c] for v, c in r["passos"]]}


# --------------------------------------------------------------- front-end --
if os.path.isdir(PASTA_FRONT):
    app.mount("/", StaticFiles(directory=PASTA_FRONT, html=True), name="front-end")
