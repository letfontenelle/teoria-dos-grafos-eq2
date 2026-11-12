"""
API da grade horária (FastAPI) e servidor do front-end.

Como rodar, de dentro de back-end:
    uvicorn main:app --reload
e abrir http://localhost:8000 (a documentação da API fica em /docs).

Os dados vêm das tabelas da equipe de dados no Supabase (precisa do .env);
a carga é feita por database/data_ingestion. Ver graphs/dados.py.
"""
import os
from collections import Counter
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from graphs.agendamento import ORDENS, expandir_sessoes
from graphs.coloracao import resumo_coloracao
from graphs.dados import DIAS, SEMESTRE_ATUAL, BancoSupabase
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
        self.repo = repo or BancoSupabase()
        self.dados = self.repo.carregar_dados()
        linhas = self.repo.carregar_grade(SEMESTRE_ATUAL)
        self.grade = GradeEmMemoria.de_linhas(self.dados, linhas, f"Banco: grade {SEMESTRE_ATUAL}")

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
    preferencias_professores: dict[int, list[str]] = Field(default_factory=dict)
    param_N: int | None = Field(default=None, ge=1)


class PedidoSemestre(BaseModel):
    semestre: str


class PedidoPreferencias(BaseModel):
    semestre: str = SEMESTRE_ATUAL
    preferencias_professores: dict[int, list[str]] = Field(default_factory=dict)


class PedidoPreferenciaProfessor(BaseModel):
    semestre: str = SEMESTRE_ATUAL
    horarios: list[str] = Field(default_factory=list)


class PedidoAnalisePreferencias(BaseModel):
    semestre: str = SEMESTRE_ATUAL
    ordem: str = "dsatur"
    param_N: int = Field(ge=1)


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
        "faixas": [{"faixa": h["HOR_FAIXA"], "inicio": h["HOR_INICIO"], "fim": h["HOR_FIM"]}
                   for h in d["horarios"] if h["HOR_DIA"] == min(DIAS)],
        "periodos": sorted({x["DIS_PERIODO"] for x in d["disciplinas"]}),
        "semestres": ctx.repo.semestres(),
        "ordens": [{"valor": o, "nome": NOMES_ORDEM[o]} for o in ORDENS],
        "banco": ctx.repo.descricao,
    }


@app.get("/api/preferencias")
def preferencias(semestre: str = SEMESTRE_ATUAL):
    semestre = semestre.strip()
    if not semestre:
        raise HTTPException(400, "Informe o semestre.")

    codigo_por_horario = {
        h["HOR_ID"]: f'{h["HOR_DIA"]}{h["HOR_FAIXA"]}'
        for h in ctx.dados["horarios"]
    }
    resultado = {}
    for linha in ctx.repo.carregar_preferencias(semestre):
        codigo = codigo_por_horario.get(linha["ho_id"])
        if codigo is None:
            raise HTTPException(500, f"Horário {linha['ho_id']} da tabela PRE_PREFERENCIA não encontrado.")
        resultado.setdefault(str(linha["pro_id"]), set()).add(codigo)

    return {
        "semestre": semestre,
        "preferencias_professores": {
            pro_id: sorted(codigos, key=lambda codigo: (int(codigo[:-1]), codigo[-1]))
            for pro_id, codigos in sorted(resultado.items(), key=lambda item: int(item[0]))
        },
    }


@app.put("/api/preferencias")
def salvar_preferencias(pedido: PedidoPreferencias):
    semestre = pedido.semestre.strip()
    if not semestre:
        raise HTTPException(400, "Informe o semestre.")

    professores = {p["PRO_ID"] for p in ctx.dados["professores"]}
    horarios_por_codigo = {
        f'{h["HOR_DIA"]}{h["HOR_FAIXA"]}': h
        for h in ctx.dados["horarios"]
        if h["HOR_FIM"] <= "13:00"
    }
    preferencias_por_horario = {}
    preferencias_normalizadas = {}
    for pro_id, codigos in pedido.preferencias_professores.items():
        if pro_id not in professores:
            raise HTTPException(422, f"Professor {pro_id} não encontrado.")
        codigos = set(codigos)
        codigos_invalidos = codigos - horarios_por_codigo.keys()
        if codigos_invalidos:
            raise HTTPException(
                422,
                f"Horário(s) inválido(s) ou após 13:00 para o professor {pro_id}: "
                f"{', '.join(sorted(codigos_invalidos))}.",
            )
        if codigos:
            preferencias_por_horario[pro_id] = {
                horarios_por_codigo[codigo]["HOR_ID"] for codigo in codigos
            }
            preferencias_normalizadas[str(pro_id)] = sorted(
                codigos, key=lambda codigo: (int(codigo[:-1]), codigo[-1])
            )

    registros = ctx.repo.salvar_preferencias(semestre, preferencias_por_horario)
    return {
        "semestre": semestre,
        "registros": registros,
        "preferencias_professores": preferencias_normalizadas,
    }


@app.get("/api/professores/{pro_id}/preferencias")
def preferencias_do_professor(pro_id: int, semestre: str = SEMESTRE_ATUAL):
    semestre = semestre.strip()
    if not semestre:
        raise HTTPException(400, "Informe o semestre.")

    professores = {p["PRO_ID"] for p in ctx.dados["professores"]}
    if pro_id not in professores:
        raise HTTPException(404, f"Professor {pro_id} não encontrado.")

    codigo_por_horario = {
        h["HOR_ID"]: f'{h["HOR_DIA"]}{h["HOR_FAIXA"]}'
        for h in ctx.dados["horarios"]
    }
    codigos = []
    for linha in ctx.repo.carregar_preferencias_professor(semestre, pro_id):
        codigo = codigo_por_horario.get(linha["ho_id"])
        if codigo is None:
            raise HTTPException(500, f"Horário {linha['ho_id']} da tabela PRE_PREFERENCIA não encontrado.")
        codigos.append(codigo)

    return {
        "semestre": semestre,
        "pro_id": pro_id,
        "horarios": sorted(set(codigos), key=lambda codigo: (int(codigo[:-1]), codigo[-1])),
    }


@app.put("/api/professores/{pro_id}/preferencias")
def salvar_preferencias_do_professor(pro_id: int, pedido: PedidoPreferenciaProfessor):
    semestre = pedido.semestre.strip()
    if not semestre:
        raise HTTPException(400, "Informe o semestre.")

    professores = {p["PRO_ID"] for p in ctx.dados["professores"]}
    if pro_id not in professores:
        raise HTTPException(404, f"Professor {pro_id} não encontrado.")

    horarios_por_codigo = {
        f'{h["HOR_DIA"]}{h["HOR_FAIXA"]}': h
        for h in ctx.dados["horarios"]
        if h["HOR_FIM"] <= "13:00"
    }
    codigos = set(pedido.horarios)
    codigos_invalidos = codigos - horarios_por_codigo.keys()
    if codigos_invalidos:
        raise HTTPException(
            422,
            f"Horário(s) inválido(s) ou após 13:00: {', '.join(sorted(codigos_invalidos))}.",
        )

    horarios = {horarios_por_codigo[codigo]["HOR_ID"] for codigo in codigos}
    registros = ctx.repo.salvar_preferencias_professor(semestre, pro_id, horarios)
    return {
        "semestre": semestre,
        "pro_id": pro_id,
        "registros": registros,
        "horarios": sorted(codigos, key=lambda codigo: (int(codigo[:-1]), codigo[-1])),
    }


@app.post("/api/preferencias/analisar")
def analisar_preferencias(pedido: PedidoAnalisePreferencias):
    semestre = pedido.semestre.strip()
    if not semestre:
        raise HTTPException(400, "Informe o semestre.")
    if pedido.ordem not in ORDENS:
        raise HTTPException(400, f"ordem inválida; use uma de {list(ORDENS)}")

    professores = {p["PRO_ID"] for p in ctx.dados["professores"]}
    horarios_por_codigo = {
        f'{h["HOR_DIA"]}{h["HOR_FAIXA"]}': h
        for h in ctx.dados["horarios"]
        if h["HOR_FIM"] <= "13:00"
    }
    codigo_por_horario = {
        horario["HOR_ID"]: codigo for codigo, horario in horarios_por_codigo.items()
    }
    preferencias_por_horario = {}
    preferencias_por_codigo = {}
    for linha in ctx.repo.carregar_preferencias(semestre):
        pro_id, ho_id = linha["pro_id"], linha["ho_id"]
        if pro_id not in professores or ho_id not in codigo_por_horario:
            raise HTTPException(422, "A tabela PRE_PREFERENCIA contém professor ou horário inválido.")
        preferencias_por_horario.setdefault(pro_id, set()).add(ho_id)
        preferencias_por_codigo.setdefault(pro_id, set()).add(codigo_por_horario[ho_id])

    carga_por_professor = Counter()
    for sessao in expandir_sessoes(ctx.dados["alocacoes"]):
        carga_por_professor[sessao["PRO_ID"]] += sessao["SLOTS"]
    for pro_id, codigos in preferencias_por_codigo.items():
        minimo = carga_por_professor[pro_id] + pedido.param_N
        if len(codigos) < minimo:
            raise HTTPException(
                422,
                f"Professor {pro_id}: selecione pelo menos {minimo} horários "
                f"({carga_por_professor[pro_id]} necessários + N={pedido.param_N}).",
            )

    try:
        grade = GradeEmMemoria.gerar(
            ctx.dados, pedido.ordem, preferencias_por_horario or None
        )
    except ValueError as erro:
        raise HTTPException(422, str(erro))
    estado = grade.estado()
    alocados_por_professor = {}
    for sessao in estado["sessoes"]:
        alocados_por_professor.setdefault(sessao["pro_id"], set()).update(sessao["rotulos"])

    analise_por_professor = {}
    for pro_id, preferidos in sorted(preferencias_por_codigo.items()):
        alocados = alocados_por_professor.get(pro_id, set())
        fora_da_preferencia = alocados - preferidos
        analise_por_professor[str(pro_id)] = {
            "horarios_preferidos": sorted(
                preferidos, key=lambda codigo: (int(codigo[:-1]), codigo[-1])
            ),
            "horarios_alocados": sorted(
                alocados, key=lambda codigo: (int(codigo[:-1]), codigo[-1])
            ),
            "horarios_alocados_dentro_preferencia": sorted(
                alocados & preferidos, key=lambda codigo: (int(codigo[:-1]), codigo[-1])
            ),
            "horarios_alocados_fora_preferencia": sorted(
                fora_da_preferencia, key=lambda codigo: (int(codigo[:-1]), codigo[-1])
            ),
            "atendida_integralmente": not fora_da_preferencia,
        }

    return {
        "semestre": semestre,
        "param_N": pedido.param_N,
        "ordem": pedido.ordem,
        "analise_por_professor": analise_por_professor,
        "grafo": {"conflitos": estado["conflitos"], "resumo": estado["resumo"]},
        "grade": estado,
    }


# ------------------------------------------------------------------ grade --
@app.get("/api/grade")
def grade_atual(passo: int | None = None):
    """Grade em memória. passo=k mostra só os k primeiros vértices coloridos."""
    return ctx.exigir_grade().estado(passo)


@app.post("/api/grade/gerar")
def gerar(pedido: PedidoGerar):
    if pedido.ordem not in ORDENS:
        raise HTTPException(400, f"ordem inválida; use uma de {list(ORDENS)}")
    preferencias = {}
    preferencias_recebidas = {
        pro_id: set(horarios) for pro_id, horarios in pedido.preferencias_professores.items() if horarios
    }
    if preferencias_recebidas and pedido.param_N is None:
        raise HTTPException(422, "Defina um valor de N para aplicar as preferências de horário.")

    professores = {p["PRO_ID"] for p in ctx.dados["professores"]}
    horarios_por_codigo = {
        f'{h["HOR_DIA"]}{h["HOR_FAIXA"]}': h
        for h in ctx.dados["horarios"]
        if h["HOR_FIM"] <= "13:00"
    }
    carga_por_professor = Counter()
    for sessao in expandir_sessoes(ctx.dados["alocacoes"]):
        carga_por_professor[sessao["PRO_ID"]] += sessao["SLOTS"]

    for pro_id, codigos in preferencias_recebidas.items():
        if pro_id not in professores:
            raise HTTPException(422, f"Professor {pro_id} não encontrado.")
        codigos_invalidos = codigos - horarios_por_codigo.keys()
        if codigos_invalidos:
            raise HTTPException(
                422,
                f"Horário(s) inválido(s) ou após 13:00 para o professor {pro_id}: "
                f"{', '.join(sorted(codigos_invalidos))}.",
            )
        carga_necessaria = carga_por_professor[pro_id]
        minimo = carga_necessaria + pedido.param_N
        if len(codigos) < minimo:
            raise HTTPException(
                422,
                f"Professor {pro_id}: selecione pelo menos {minimo} horários "
                f"({carga_necessaria} necessários + N={pedido.param_N}).",
            )
        preferencias[pro_id] = {horarios_por_codigo[codigo]["HOR_ID"] for codigo in codigos}

    try:
        ctx.grade = GradeEmMemoria.gerar(ctx.dados, pedido.ordem, preferencias or None)
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
    try:
        n = ctx.repo.salvar_grade(semestre, grade.linhas(semestre))
    except ValueError as erro:
        raise HTTPException(400, str(erro))
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
