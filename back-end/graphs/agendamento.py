"""
Agendamento: monta a grade de horários com busca gulosa.

1. Cada aula é dividida em sessões de 2 horários (um bloco). Aula de 4 horários
   gera 2 sessões; de 2 horários, 1 sessão; de 3 horários, 1 sessão contínua
   (um bloco e metade do seguinte, ex.: 10:30 às 13:00).
2. A semana tem 30 blocos: 6 por dia (A a F) x 5 dias.
     A 07:10-08:50 | B 08:50-10:30 | C 10:30-12:10
     D 12:10-13:50 | E 13:50-15:30 | F 15:30-17:10
3. O grafo de conflitos (graph.py) liga sessões que não podem ocorrer juntas:
   mesmo professor, mesmo período ou mesma aula.
4. Busca gulosa: as sessões, em ordem alfabética de professor (ou pela
   saturação, com ordem="dsatur"), ocupam o primeiro bloco livre de conflito.
5. Manhã (A, B, C) primeiro; a tarde (D, E, F) só é usada se a sessão não
   couber de manhã. Dentro do turno, escolhe o bloco menos ocupado e evita
   duas sessões da mesma aula no mesmo dia.

Não acessa o banco: recebe e devolve listas de dicionários.
"""
from collections import defaultdict

try:
    from graphs.graph import construir_grafo_conflitos
except ImportError:  # quando executado de dentro da pasta graphs/
    from graph import construir_grafo_conflitos

SLOTS_POR_BLOCO = 2
LETRAS = "ABCDEF"
DURACAO_PADRAO = 4   # horários por aula, enquanto o grupo não define outra regra
HORAS_POR_AULA_SEMANAL = 15  # carga horária / 15 = aulas por semana (60h -> 4, 30h -> 2)
TURNOS_PADRAO = ("ABC", "DEF")  # manhã primeiro; a tarde só se não couber


def duracao_pela_carga_horaria(carga_horaria):
    """60h -> 4 aulas por semana, 90h -> 6, 45h -> 3, 30h -> 2."""
    return max(1, round(carga_horaria / HORAS_POR_AULA_SEMANAL))


# ---------------------------------------------------------------- blocos ----
def montar_blocos(horarios, tamanho=SLOTS_POR_BLOCO):
    """
    Agrupa os horários de HOR_HORARIO em blocos de `tamanho` horários seguidos
    no mesmo dia (A, B, C...).

    horarios: lista de dicts com HOR_ID e HOR_DIA (os HOR_ID devem seguir a ordem
              cronológica dentro do dia).
    Retorna: lista de dicts {id, dia, letra, pos, ordem_dia, ho_ids}.
    """
    por_dia = defaultdict(list)
    for h in sorted(horarios, key=lambda h: h["HOR_ID"]):
        por_dia[h["HOR_DIA"]].append(h["HOR_ID"])

    blocos = []
    for ordem_dia, (dia, ids) in enumerate(por_dia.items()):
        for pos, ini in enumerate(range(0, len(ids) - tamanho + 1, tamanho)):
            blocos.append({
                "id": len(blocos),
                "dia": dia,
                "letra": LETRAS[pos] if pos < len(LETRAS) else str(pos + 1),
                "pos": pos,
                "ordem_dia": ordem_dia,
                "ho_ids": ids[ini:ini + tamanho],
            })
    return blocos


def _ordenar_blocos(blocos, espalhar):
    """espalhar=True: o bloco A de cada dia primeiro, depois o B de cada dia...
    espalhar=False: Segunda A, B, C... depois Terça A, B, C..."""
    if espalhar:
        return sorted(blocos, key=lambda b: (b["pos"], b["ordem_dia"]))
    return sorted(blocos, key=lambda b: (b["ordem_dia"], b["pos"]))


# --------------------------------------------------------------- sessões ----
def dividir_duracao(duracao, maximo=SLOTS_POR_BLOCO):
    """
    Divide as aulas da semana em sessões.
      4 -> [2, 2]      6 -> [2, 2, 2]      2 -> [2]
      3 -> [3]         (3 aulas seguidas no mesmo dia: um bloco inteiro mais a
                        primeira metade do bloco seguinte, ex.: 10:30 às 13:00)
      5 -> [3, 2]
    """
    partes = []
    if duracao % 2 == 1 and duracao >= 3:
        partes.append(3)
        duracao -= 3
    while duracao > 0:
        parte = min(duracao, maximo)
        partes.append(parte)
        duracao -= parte
    return partes


def expandir_sessoes(alocacoes, duracoes=None, duracao_padrao=DURACAO_PADRAO):
    """
    Transforma cada alocação em uma ou mais sessões de até 2 horários.

    Quantos horários a aula tem por semana, em ordem de prioridade:
      1. `duracoes` ({ALO_ID: nº de horários}), se a aula estiver lá;
      2. a carga horária da disciplina (DIS_DISCIPLINA.DIS_CARGA_HORARIA) / 15;
      3. `duracao_padrao`.
    Cada sessão ganha ALO_ID = (alo_id_original, n) e o campo SLOTS.
    """
    duracoes = duracoes or {}
    sessoes = []
    for alo in alocacoes:
        alo_id = alo["ALO_ID"]
        disc = alo.get("DIS_DISCIPLINA")
        carga = disc.get("DIS_CARGA_HORARIA") if isinstance(disc, dict) else None
        if duracoes.get(alo_id):
            duracao = duracoes[alo_id]
        elif carga:
            duracao = duracao_pela_carga_horaria(carga)
        else:
            duracao = duracao_padrao
        for n, slots in enumerate(dividir_duracao(duracao)):
            sessao = dict(alo)
            sessao["ALO_ID"] = (alo_id, n)
            sessao["SLOTS"] = slots
            sessao["SPAN"] = -(-slots // SLOTS_POR_BLOCO)  # blocos que a sessão ocupa
            sessoes.append(sessao)
    return sessoes


# ---------------------------------------------------------- ordenação -------
def _nome_professor(s):
    nome = s.get("PRO_NOME") or (s.get("PRO_PROFESSOR") or {}).get("PRO_NOME")
    return nome if nome else f"{s.get('PRO_ID') or 0:08d}"


def _nome_disciplina(s):
    disc = s.get("DIS_DISCIPLINA") or {}
    return s.get("DIS_NOME") or (disc.get("DIS_DESCRICAO") if isinstance(disc, dict) else "") or ""


ORDENS = ("alfabetica", "mais_conflitos", "dsatur")


def _ordenar_sessoes(sessoes, G, ordem):
    if ordem == "mais_conflitos":
        return sorted(sessoes, key=lambda s: (-G.degree(s["ALO_ID"]), _nome_professor(s),
                                              _nome_disciplina(s), s["ALO_ID"]))
    # padrão: ordem alfabética do professor (depois disciplina)
    return sorted(sessoes, key=lambda s: (_nome_professor(s), _nome_disciplina(s), s["ALO_ID"]))


# ------------------------------------------------------- busca gulosa -------
def colocar_sessoes(G, sessoes, blocos, ordem="alfabetica", espalhar=True,
                    turnos=TURNOS_PADRAO):
    """
    Busca gulosa. Para cada sessão (na ordem escolhida), descarta as posições
    em que já há uma sessão em conflito e escolhe uma das que sobraram.

    Uma sessão de 3 horários ocupa DOIS blocos seguidos do mesmo dia (ex.: C e
    D: 10:30 às 13:00); as demais ocupam um bloco.

    ordem         : "alfabetica" (professor, depois disciplina), "mais_conflitos"
                    (maior grau primeiro) ou "dsatur" (a cada passo, a sessão com
                    mais blocos já bloqueados pelos vizinhos colocados, ou seja,
                    maior grau de saturação; empate: maior grau, depois nome).
    espalhar=True : escolhe a posição livre menos ocupada (evitando repetir o
                    dia de uma sessão da mesma aula).
    espalhar=False: escolhe a primeira posição livre (Segunda A, B, C...).
    turnos        : grupos de letras em ordem de preferência. Com ("ABC", "DEF"),
                    a sessão vai para a manhã e só vai para a tarde se não houver
                    nenhuma posição livre de manhã (vale a letra do primeiro
                    bloco). Use ("ABCDEF",) para não ter preferência de turno.

    Retorna {ALO_ID da sessão: (id do bloco, ...)}. Levanta ValueError se uma
    sessão não couber em lugar nenhum.
    """
    ordem_blocos = _ordenar_blocos(blocos, espalhar)
    posicao = {b["id"]: i for i, b in enumerate(ordem_blocos)}
    por_dia_pos = {(b["ordem_dia"], b["pos"]): b for b in blocos}

    def posicoes(span):
        """Todas as formas de colocar uma sessão que ocupa `span` blocos seguidos."""
        ops = []
        for b in ordem_blocos:
            seq = [b]
            for k in range(1, span):
                prox = por_dia_pos.get((b["ordem_dia"], b["pos"] + k))
                if prox is None:
                    break
                seq.append(prox)
            if len(seq) == span:
                ops.append(tuple(seq))
        return ops

    if ordem not in ORDENS:
        raise ValueError(f"ordem desconhecida: {ordem!r} (use {', '.join(ORDENS)})")

    colocacao = {}
    carga_bloco = defaultdict(int)
    carga_dia = defaultdict(int)
    mesma_aula_no_dia = defaultdict(int)

    def bloqueados(no):
        ocupados = set()
        for v in G[no]:
            ocupados.update(colocacao.get(v, ()))
        return ocupados

    pendentes = _ordenar_sessoes(sessoes, G, "alfabetica" if ordem == "dsatur" else ordem)
    while pendentes:
        if ordem == "dsatur":
            # Saturação: quantos blocos (cores) os vizinhos já colocados ocupam.
            s = min(pendentes, key=lambda x: (-len(bloqueados(x["ALO_ID"])), -G.degree(x["ALO_ID"])))
            pendentes.remove(s)
        else:
            s = pendentes.pop(0)
        no = s["ALO_ID"]
        ocupados = bloqueados(no)
        livres = [op for op in posicoes(s.get("SPAN", 1))
                  if not any(b["id"] in ocupados for b in op)]
        if not livres:
            raise ValueError(
                f"A sessão {no} (professor {_nome_professor(s)}) não cabe em nenhum dos "
                f"{len(blocos)} blocos: todos têm algum conflito."
            )
        if espalhar:
            for letras in turnos:
                do_turno = [op for op in livres if op[0]["letra"] in letras]
                if do_turno:
                    livres = do_turno
                    break
            escolhido = min(livres, key=lambda op: (
                mesma_aula_no_dia[(no[0], op[0]["dia"])],
                sum(carga_bloco[b["id"]] for b in op),
                carga_dia[op[0]["dia"]],
                posicao[op[0]["id"]],
            ))
        else:
            escolhido = livres[0]
        colocacao[no] = tuple(b["id"] for b in escolhido)
        for b in escolhido:
            carga_bloco[b["id"]] += 1
            carga_dia[b["dia"]] += 1
        mesma_aula_no_dia[(no[0], escolhido[0]["dia"])] += 1
    return colocacao


def horarios_por_sessao(sessoes, colocacao, blocos):
    """{ALO_ID da sessão: [HOR_ID, ...]} com as faixas que cada sessão colocada ocupa."""
    por_id = {b["id"]: b for b in blocos}
    saida = {}
    for s in sessoes:
        if s["ALO_ID"] not in colocacao:
            continue
        horarios_da_sessao = []
        for bloco_id in colocacao[s["ALO_ID"]]:
            horarios_da_sessao += por_id[bloco_id]["ho_ids"]
        saida[s["ALO_ID"]] = horarios_da_sessao[: s["SLOTS"]]
    return saida


def gerar_linhas_grade(sessoes, colocacao, blocos, semestre):
    """Gera as linhas (GRA_SEMESTRE, ALO_ID, HOR_ID) da GRA_GRADE_HORARIA."""
    return [{"GRA_SEMESTRE": semestre, "ALO_ID": sessao[0], "HOR_ID": ho_id}
            for sessao, ho_ids in horarios_por_sessao(sessoes, colocacao, blocos).items()
            for ho_id in ho_ids]


# ------------------------------------------------------------ validação ----
def validar_grade(linhas, alocacoes):
    """Procura choques na grade pronta. Lista vazia = grade correta."""
    info = {a["ALO_ID"]: a for a in alocacoes}

    def periodo(alo_id):
        disc = info[alo_id].get("DIS_DISCIPLINA")
        return disc.get("DIS_PERIODO") if isinstance(disc, dict) else None

    def eletiva(alo_id):
        disc = info[alo_id].get("DIS_DISCIPLINA")
        return bool(disc.get("DIS_ELETIVA")) if isinstance(disc, dict) else False

    por_slot = defaultdict(set)
    vistos = set()
    violacoes = []
    for l in linhas:
        chave = (l["ALO_ID"], l["HOR_ID"])
        if chave in vistos:
            violacoes.append(f"Linha repetida: aula {l['ALO_ID']} no horário {l['HOR_ID']}")
        vistos.add(chave)
        por_slot[l["HOR_ID"]].add(l["ALO_ID"])

    for ho_id, aulas in sorted(por_slot.items()):
        aulas = sorted(aulas)
        for i in range(len(aulas)):
            for j in range(i + 1, len(aulas)):
                a, b = aulas[i], aulas[j]
                pa, pb = info[a].get("PRO_ID"), info[b].get("PRO_ID")
                if pa is not None and pa == pb:
                    violacoes.append(f"Horário {ho_id}: aulas {a} e {b} têm o mesmo professor ({pa})")
                da, db = periodo(a), periodo(b)
                if da is not None and da == db and not (eletiva(a) and eletiva(b)):
                    violacoes.append(f"Horário {ho_id}: aulas {a} e {b} são do mesmo período ({da})")
    return violacoes


# ---------------------------------------------------------- orquestração ----
def construir_grafo_sessoes(sessoes):
    """Grafo de conflitos das sessões (vértice = (ALO_ID, n))."""
    G = construir_grafo_conflitos(sessoes)

    # Sessões da mesma aula nunca podem coincidir (garantia extra, caso a aula
    # não tenha professor nem período preenchidos).
    por_aula = defaultdict(list)
    for s in sessoes:
        por_aula[s["ALO_ID"][0]].append(s["ALO_ID"])
    for ids in por_aula.values():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                G.add_edge(ids[i], ids[j], motivo="mesma_aula")
    return G


def gerar_grade(alocacoes, horarios, semestre, duracoes=None, duracao_padrao=DURACAO_PADRAO,
                ordem="alfabetica", espalhar=True, letras_permitidas=LETRAS,
                turnos=TURNOS_PADRAO):
    """
    Fluxo completo, sem banco de dados:
      alocações -> sessões -> grafo -> busca gulosa -> linhas da grade -> validação.

    letras_permitidas: quais blocos podem ser usados (ex.: "ABC" = só de manhã,
                       sem nunca usar a tarde).
    turnos: preferência de turno (padrão: manhã primeiro, tarde só se precisar).
    Retorna dict com: linhas, violacoes, grafo, colocacao, blocos, sessoes.
    """
    blocos = [b for b in montar_blocos(horarios) if b["letra"] in letras_permitidas]
    sessoes = expandir_sessoes(alocacoes, duracoes, duracao_padrao)
    G = construir_grafo_sessoes(sessoes)

    colocacao = colocar_sessoes(G, sessoes, blocos, ordem=ordem, espalhar=espalhar, turnos=turnos)
    linhas = gerar_linhas_grade(sessoes, colocacao, blocos, semestre)
    return {
        "linhas": linhas,
        "violacoes": validar_grade(linhas, alocacoes),
        "grafo": G,
        "colocacao": colocacao,
        "blocos": blocos,
        "sessoes": sessoes,
    }


def grafo_para_dict(G, colocacao, blocos):
    """Formato simples (JSON) para o front desenhar o grafo."""
    por_id = {b["id"]: b for b in blocos}
    return {
        "nos": [
            {
                "id": f"{n[0]}-{n[1]}",
                "alo_id": n[0],
                "pro_id": d.get("pro_id"),
                "periodo": d.get("dis_periodo"),
                "dia": por_id[colocacao[n][0]]["dia"],
                "bloco": "+".join(por_id[i]["letra"] for i in colocacao[n]),
            }
            for n, d in G.nodes(data=True)
        ],
        "arestas": [
            {"origem": f"{a[0]}-{a[1]}", "destino": f"{b[0]}-{b[1]}", "motivo": d.get("motivo")}
            for a, b, d in G.edges(data=True)
        ],
    }