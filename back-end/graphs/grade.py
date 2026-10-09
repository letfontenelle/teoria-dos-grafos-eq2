"""
Grade em memória: o grafo de conflitos das sessões de aula, em que a "cor" de
cada vértice é o conjunto de faixas (HOR_ID) que a sessão ocupa.

É a ponte entre as três representações pedidas pela professora no card do
item 14:
  modelo de dados -> grafo   GradeEmMemoria.gerar(dados) ou .de_linhas(dados, linhas)
  grafo -> grade no front    estado(passo): sem cor = grade vazia, parcialmente
                             colorido = grade parcial, todo colorido = grade completa
  grafo -> modelo de dados   linhas(semestre) -> GRA_GRADE_HORARIA
  front -> grafo (extra)     mover(sessao, dia, faixa): o vértice troca de cor e
                             os conflitos com os vizinhos são recalculados
"""
from collections import defaultdict

try:
    from graphs.agendamento import construir_grafo_sessoes, gerar_grade, horarios_por_sessao, ORDENS
    from graphs.coloracao import maior_clique
except ImportError:  # quando executado de dentro da pasta graphs/
    from agendamento import construir_grafo_sessoes, gerar_grade, horarios_por_sessao, ORDENS
    from coloracao import maior_clique

LETRAS_FAIXA = "ABCDEFGHIJKL"
NOMES_ORDEM = {"dsatur": "DSATUR (saturação)", "alfabetica": "Gulosa (ordem alfabética)",
               "mais_conflitos": "Gulosa (maior grau primeiro)"}


def id_sessao(no):
    return f"{no[0]}-{no[1]}"


def no_da_sessao(texto):
    alo, n = str(texto).split("-")
    return int(alo), int(n)


class GradeEmMemoria:
    def __init__(self, dados, sessoes, cores, ordem_coloracao, origem):
        """
        dados: professores, disciplinas, horarios e alocacoes (repositorio.carregar_dados()).
        sessoes: lista de sessões (dicts com ALO_ID = (alo_id, n), SLOTS e a alocação).
        cores: {(alo_id, n): (HOR_ID, ...)}.
        ordem_coloracao: vértices na ordem em que foram coloridos.
        """
        self.dados = dados
        self.horarios = {h["HOR_ID"]: h for h in dados["horarios"]}
        self.hor_por_dia_faixa = {(h["HOR_DIA"], h["HOR_FAIXA"]): h["HOR_ID"] for h in dados["horarios"]}
        self.sessoes = {s["ALO_ID"]: s for s in sessoes}
        self.G = construir_grafo_sessoes(sessoes)
        self.ordem = list(ordem_coloracao)
        self.origem = origem
        self.editada = False
        for no in self.G.nodes:
            self.G.nodes[no]["cor"] = tuple(cores.get(no, ()))

    # ------------------------------------------------------- construção ----
    @classmethod
    def gerar(cls, dados, ordem="dsatur"):
        """Gera a grade com a busca gulosa (agendamento.py) na ordem escolhida."""
        if ordem not in ORDENS:
            raise ValueError(f"ordem desconhecida: {ordem!r}")
        r = gerar_grade(dados["alocacoes"], dados["horarios"], semestre="", ordem=ordem)
        cores = horarios_por_sessao(r["sessoes"], r["colocacao"], r["blocos"])
        return cls(dados, r["sessoes"], cores, list(r["colocacao"]), f"Gerada: {NOMES_ORDEM[ordem]}")

    @classmethod
    def de_linhas(cls, dados, linhas, origem):
        """
        Instancia o grafo a partir de linhas da GRA_GRADE_HORARIA (grade salva
        no banco). Cada sequência de faixas seguidas da mesma alocação no mesmo
        dia vira uma sessão (vértice); a cor do vértice são essas faixas.
        """
        horarios = {h["HOR_ID"]: h for h in dados["horarios"]}
        alocacoes = {a["ALO_ID"]: a for a in dados["alocacoes"]}
        por_alo_dia = defaultdict(list)
        for l in linhas:
            if l["ALO_ID"] in alocacoes and l["HOR_ID"] in horarios:
                h = horarios[l["HOR_ID"]]
                por_alo_dia[(l["ALO_ID"], h["HOR_DIA"])].append(l["HOR_ID"])

        sessoes, cores, contador = [], {}, defaultdict(int)
        for (alo_id, _dia), hor_ids in sorted(por_alo_dia.items()):
            hor_ids = sorted(set(hor_ids))
            corrida = [hor_ids[0]]
            for h in hor_ids[1:] + [None]:
                if h is not None and h == corrida[-1] + 1:
                    corrida.append(h)
                    continue
                no = (alo_id, contador[alo_id])
                contador[alo_id] += 1
                sessao = dict(alocacoes[alo_id])
                sessao.update({"ALO_ID": no, "SLOTS": len(corrida)})
                sessoes.append(sessao)
                cores[no] = tuple(corrida)
                if h is not None:
                    corrida = [h]
        ordem = sorted(cores, key=lambda no: cores[no][0])
        return cls(dados, sessoes, cores, ordem, origem)

    # ---------------------------------------------------------- consulta ----
    def cores(self, passo=None):
        """Cores dos vértices; com passo=k, só os k primeiros coloridos têm cor."""
        coloridos = set(self.ordem if passo is None else self.ordem[:max(0, passo)])
        return {no: (self.G.nodes[no]["cor"] if no in coloridos else ()) for no in self.G.nodes}

    def conflitos(self, cores=None):
        """Arestas cujos extremos dividem alguma faixa (choque de professor ou de período)."""
        cores = cores or self.cores()
        saida = []
        for a, b, d in self.G.edges(data=True):
            comum = set(cores[a]) & set(cores[b])
            if comum:
                saida.append({"a": id_sessao(a), "b": id_sessao(b), "motivo": d.get("motivo"),
                              "horarios": [self.codigo(h) for h in sorted(comum)]})
        return saida

    def codigo(self, hor_id):
        h = self.horarios[hor_id]
        return f"{h['HOR_DIA']}{h['HOR_FAIXA']}"

    def estado(self, passo=None):
        total = len(self.ordem)
        passo = total if passo is None else max(0, min(passo, total))
        cores = self.cores(passo)
        conflitos = self.conflitos(cores)
        em_conflito = defaultdict(list)
        for c in conflitos:
            em_conflito[c["a"]].append(c["b"])
            em_conflito[c["b"]].append(c["a"])
        posicao = {no: i for i, no in enumerate(self.ordem)}

        sessoes = []
        for no in sorted(self.G.nodes, key=lambda n: (posicao.get(n, total), n)):
            s = self.sessoes[no]
            d = s["DIS_DISCIPLINA"]
            sid = id_sessao(no)
            sessoes.append({
                "id": sid, "alo_id": no[0], "pro_id": s["PRO_ID"], "professor": s.get("PRO_NOME"),
                "codigo": d["DIS_CODIGO"], "disciplina": d["DIS_DESCRICAO"], "periodo": d["DIS_PERIODO"],
                "eletiva": bool(d.get("DIS_ELETIVA")), "faixas": s["SLOTS"],
                "horarios": list(cores[no]), "rotulos": [self.codigo(h) for h in cores[no]],
                "colorida": bool(cores[no]), "passo": posicao.get(no, total) + 1,
                "conflito_com": em_conflito.get(sid, []),
            })

        coloridas = [no for no in self.G.nodes if cores[no]]
        return {
            "origem": self.origem, "editada": self.editada,
            "passo": passo, "total_passos": total,
            "situacao": "vazia" if passo == 0 else ("parcial" if passo < total else "completa"),
            "sessoes": sessoes,
            "conflitos": conflitos,
            "resumo": {
                "sessoes": self.G.number_of_nodes(), "arestas": self.G.number_of_edges(),
                "coloridas": len(coloridas), "conflitos": len(conflitos),
                "cores_usadas": len({cores[no] for no in coloridas}),
                "faixas_usadas": len({h for no in coloridas for h in cores[no]}),
            },
        }

    def grafo(self):
        """Vértices e arestas para desenhar o grafo de conflitos (com a cor atual)."""
        cores = self.cores()
        return {
            "vertices": [{"id": id_sessao(no), "codigo": self.sessoes[no]["DIS_DISCIPLINA"]["DIS_CODIGO"],
                          "periodo": self.sessoes[no]["DIS_DISCIPLINA"]["DIS_PERIODO"],
                          "professor": self.sessoes[no].get("PRO_NOME"),
                          "cor": " ".join(self.codigo(h) for h in cores[no])} for no in self.G.nodes],
            "arestas": [{"origem": id_sessao(a), "destino": id_sessao(b), "motivo": d.get("motivo")}
                        for a, b, d in self.G.edges(data=True)],
            "maior_clique": maior_clique(self.G),
        }

    # ------------------------------------------------------------ edição ----
    def mover(self, sessao, dia, faixa):
        """
        Move a sessão para começar em (dia, faixa), mantendo o número de faixas.
        No grafo, o vértice troca de cor; devolve os conflitos que ele passou a ter.
        """
        no = no_da_sessao(sessao)
        if no not in self.G:
            raise KeyError(f"sessão {sessao} não existe")
        faixa = faixa.upper()
        if faixa not in LETRAS_FAIXA:
            raise ValueError(f"faixa inválida: {faixa}")
        inicio = LETRAS_FAIXA.index(faixa)
        tamanho = self.sessoes[no]["SLOTS"]
        letras = LETRAS_FAIXA[inicio:inicio + tamanho]
        if len(letras) < tamanho or any((dia, l) not in self.hor_por_dia_faixa for l in letras):
            raise ValueError(f"a sessão tem {tamanho} faixas e não cabe a partir de {dia}{faixa}")
        self.G.nodes[no]["cor"] = tuple(self.hor_por_dia_faixa[(dia, l)] for l in letras)
        if no not in self.ordem:
            self.ordem.append(no)
        self.editada = True
        sid = id_sessao(no)
        return [c for c in self.conflitos() if sid in (c["a"], c["b"])]

    # ------------------------------------------------------------- saída ----
    def linhas(self, semestre):
        """Linhas da GRA_GRADE_HORARIA (uma por faixa ocupada)."""
        cores = self.cores()
        vistas, linhas = set(), []
        for no in self.ordem:
            for h in cores[no]:
                if (no[0], h) not in vistas:
                    vistas.add((no[0], h))
                    linhas.append({"GRA_SEMESTRE": semestre, "ALO_ID": no[0], "HOR_ID": h})
        return linhas

