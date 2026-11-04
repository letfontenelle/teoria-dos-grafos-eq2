"""
Ponte entre as tabelas da equipe de dados e o grafo.

As tabelas são as do Supabase, carregadas por database/data_ingestion a partir
da planilha database/data/modelo_grade_professor.xlsx:

  PRO_PROFESSOR      PRO_ID, PRO_NOME, PRO_MATRICULA
  DI_DISCIPLINA      DI_ID, DI_CODIGO, DI_DESCRICAO, DI_PERIODO
  HO_HORARIO         HO_ID, HO_DIA ("Segunda"), HO_FAIXA ("07:10-08:00"), HO_COR
  ALO_ALOCACAO       ALO_ID, PRO_ID, DI_ID
  GRA_GRADE_HORARIA  GRA_ID, GRA_SEMESTRE, ALO_ID, HO_ID

O grafo (graphs/grade.py e graphs/agendamento.py) usa os nomes DIS_ e HOR_ e o
horário no padrão dia (2 a 6) + faixa (A a L), ex.: 2C. montar_dados() faz
essa tradução; nada é gravado de volta com esses nomes.

A carga horária não está no banco. Ela vem da grade atual: cada faixa por
semana durante o semestre equivale a 15h.
"""
import os
from collections import Counter

DIAS = {2: "Segunda", 3: "Terça", 4: "Quarta", 5: "Quinta", 6: "Sexta"}
LETRAS_FAIXA = "ABCDEFGHIJKL"
HORAS_POR_FAIXA = 15
SEMESTRE_ATUAL = "2026.2"  # grade carregada pela equipe de dados
TABELAS = {"PRO_PROFESSOR": "PRO_ID", "DI_DISCIPLINA": "DI_ID", "HO_HORARIO": "HO_ID",
           "ALO_ALOCACAO": "ALO_ID", "GRA_GRADE_HORARIA": "GRA_ID"}
PLANILHA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "data",
                        "modelo_grade_professor.xlsx")


def montar_dados(tabelas):
    """Tabelas do Supabase (dict nome -> linhas) no formato que o grafo usa."""
    faixas_do_dia = sorted({h["HO_FAIXA"] for h in tabelas["HO_HORARIO"]})
    numero_do_dia = {nome: n for n, nome in DIAS.items()}
    horarios = []
    for h in sorted(tabelas["HO_HORARIO"], key=lambda h: h["HO_ID"]):
        inicio, fim = h["HO_FAIXA"].split("-")
        horarios.append({"HOR_ID": h["HO_ID"], "HOR_DIA": numero_do_dia[h["HO_DIA"]],
                         "HOR_FAIXA": LETRAS_FAIXA[faixas_do_dia.index(h["HO_FAIXA"])],
                         "HOR_INICIO": inicio, "HOR_FIM": fim})

    faixas_na_grade = Counter(g["ALO_ID"] for g in tabelas["GRA_GRADE_HORARIA"]
                              if str(g["GRA_SEMESTRE"]) == SEMESTRE_ATUAL)
    carga_da_disciplina = Counter()
    for a in tabelas["ALO_ALOCACAO"]:
        carga_da_disciplina[a["DI_ID"]] += faixas_na_grade[a["ALO_ID"]] * HORAS_POR_FAIXA

    disciplinas = [{"DIS_ID": d["DI_ID"], "DIS_CODIGO": d["DI_CODIGO"], "DIS_DESCRICAO": d["DI_DESCRICAO"],
                    "DIS_PERIODO": int(d["DI_PERIODO"]), "DIS_CARGA_HORARIA": carga_da_disciplina[d["DI_ID"]]}
                   for d in sorted(tabelas["DI_DISCIPLINA"], key=lambda d: d["DI_ID"])]
    professores = sorted(tabelas["PRO_PROFESSOR"], key=lambda p: p["PRO_ID"])

    dis = {d["DIS_ID"]: d for d in disciplinas}
    nome = {p["PRO_ID"]: p["PRO_NOME"] for p in professores}
    alocacoes = []
    for a in sorted(tabelas["ALO_ALOCACAO"], key=lambda a: a["ALO_ID"]):
        # Carga da alocação: quando dois professores dividem a disciplina, cada um tem as suas faixas.
        d = dict(dis[a["DI_ID"]], DIS_CARGA_HORARIA=faixas_na_grade[a["ALO_ID"]] * HORAS_POR_FAIXA or None)
        alocacoes.append({"ALO_ID": a["ALO_ID"], "PRO_ID": a["PRO_ID"], "DIS_ID": a["DI_ID"],
                          "PRO_NOME": nome[a["PRO_ID"]], "DIS_DISCIPLINA": d})
    return {"professores": professores, "disciplinas": disciplinas, "horarios": horarios, "alocacoes": alocacoes}


def linhas_da_grade(tabelas, semestre):
    """Linhas da GRA_GRADE_HORARIA de um semestre, com HO_ID como HOR_ID."""
    return [{"GRA_SEMESTRE": semestre, "ALO_ID": g["ALO_ID"], "HOR_ID": g["HO_ID"]}
            for g in sorted(tabelas["GRA_GRADE_HORARIA"], key=lambda g: (g["ALO_ID"], g["HO_ID"]))
            if str(g["GRA_SEMESTRE"]) == semestre]


def tabelas_da_planilha(caminho=PLANILHA):
    """
    Mesmas tabelas lidas da planilha da equipe de dados, sem internet.
    Como na carga, o ID de cada linha é a sua posição (1, 2, 3...).
    """
    import pandas as pd

    tabelas = {}
    for nome, chave in TABELAS.items():
        df = pd.read_excel(caminho, sheet_name=nome).astype(object)
        linhas = [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in df.to_dict(orient="records")]
        for i, linha in enumerate(linhas, start=1):
            linha[chave] = i
        tabelas[nome] = linhas
    for g in tabelas["GRA_GRADE_HORARIA"]:
        g["GRA_SEMESTRE"] = str(g["GRA_SEMESTRE"])
    for d in tabelas["DI_DISCIPLINA"]:
        d["DI_PERIODO"] = str(d["DI_PERIODO"])
    return tabelas


class BancoSupabase:
    """Lê e grava nas tabelas da equipe de dados no Supabase (precisa do .env)."""

    descricao = "Supabase"

    def __init__(self, cliente=None):
        if cliente is None:
            from database.connection.connect import supabase as cliente
        self.cliente = cliente

    def _ler(self, tabela, colunas="*", semestre=None):
        """Todas as linhas, de 1000 em 1000 (limite por consulta do Supabase)."""
        linhas = []
        while True:
            consulta = self.cliente.table(tabela).select(colunas).order(TABELAS[tabela])
            if semestre is not None:
                consulta = consulta.eq("GRA_SEMESTRE", semestre)
            pagina = consulta.range(len(linhas), len(linhas) + 999).execute().data
            linhas += pagina
            if len(pagina) < 1000:
                return linhas

    def carregar_dados(self):
        tabelas = {nome: self._ler(nome) for nome in TABELAS if nome != "GRA_GRADE_HORARIA"}
        tabelas["GRA_GRADE_HORARIA"] = self._ler("GRA_GRADE_HORARIA", semestre=SEMESTRE_ATUAL)
        return montar_dados(tabelas)

    def carregar_grade(self, semestre):
        return linhas_da_grade({"GRA_GRADE_HORARIA": self._ler("GRA_GRADE_HORARIA", semestre=semestre)}, semestre)

    def salvar_grade(self, semestre, linhas):
        """Substitui a grade do semestre. A grade atual (carga da equipe de dados) não é sobrescrita."""
        if semestre == SEMESTRE_ATUAL:
            raise ValueError(f"A grade {SEMESTRE_ATUAL} é a carga da equipe de dados; salve com outro semestre.")
        gra = lambda: self.cliente.table("GRA_GRADE_HORARIA")  # noqa: E731
        gra().delete().eq("GRA_SEMESTRE", semestre).execute()
        if linhas:
            # GRA_ID não é gerado pelo banco: continua a partir do maior que existe.
            ultimo = gra().select("GRA_ID").order("GRA_ID", desc=True).limit(1).execute().data
            proximo = (ultimo[0]["GRA_ID"] if ultimo else 0) + 1
            gra().insert([{"GRA_ID": proximo + i, "GRA_SEMESTRE": semestre, "ALO_ID": l["ALO_ID"], "HO_ID": l["HOR_ID"]}
                        for i, l in enumerate(linhas)]).execute()
        return len(linhas)

    def semestres(self):
        contagem = Counter(g["GRA_SEMESTRE"] for g in self._ler("GRA_GRADE_HORARIA", "GRA_ID, GRA_SEMESTRE"))
        return [{"semestre": s, "linhas": n} for s, n in sorted(contagem.items())]
