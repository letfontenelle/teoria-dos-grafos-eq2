"""
Carga de dados (Iteração 04, US-01).

Lê os materiais fornecidos pela professora e monta as tabelas do modelo de dados:

  data/grade_professor_2026_2.csv
      Extraído do GradeProfessor.pdf (Classroom, Iteração 02): uma linha por
      professor x disciplina, com os horários no padrão dia + faixa (ex.: 2C =
      segunda, 08:50). Para as 7 disciplinas com horário modificado, a coluna
      horarios_atuais traz o horário atual e horarios_originais o anterior.
  data/perfil_cp21.csv
      Grade de componentes do perfil curricular CP21 (ecomp.poli.br): período,
      carga horária e tipo das disciplinas obrigatórias.

Regras da carga:
  - Disciplina com horário modificado entra com o horário ATUAL; o original
    vai para o relatório.
  - Período: o da oferta (GradeProfessor). Quando o CP21 diz outra coisa, a
    divergência vai para o relatório.
  - Carga horária: a do CP21. Eletivas não aparecem por código no CP21 e
    recebem 60h ("Eletiva 60h" na grade do CP21).
  - Linhas inválidas não interrompem a carga: são ignoradas e listadas no
    relatório de linhas ignoradas, com o motivo.

Uso, de dentro de back-end:
    python -m database.data_ingestion.data_ingestion            # SQLite local
    python -m database.data_ingestion.data_ingestion --banco supabase
    python -m database.data_ingestion.data_ingestion --simular  # só valida
"""
import argparse
import csv
import os
import re
import sys

PASTA_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PASTA_BACKEND not in sys.path:
    sys.path.insert(0, PASTA_BACKEND)

PASTA_DADOS = os.path.join(PASTA_BACKEND, "database", "data")
ARQUIVO_OFERTA = os.path.join(PASTA_DADOS, "grade_professor_2026_2.csv")
ARQUIVO_CP21 = os.path.join(PASTA_DADOS, "perfil_cp21.csv")
ARQUIVO_RELATORIO = os.path.join(PASTA_DADOS, "relatorio_carga.md")
SEMESTRE_OFERTA = "2026.2"

DIAS = {2: "Segunda", 3: "Terça", 4: "Quarta", 5: "Quinta", 6: "Sexta"}
FAIXAS = [
    ("A", "07:10", "08:00"), ("B", "08:00", "08:50"), ("C", "08:50", "09:40"),
    ("D", "09:40", "10:30"), ("E", "10:30", "11:20"), ("F", "11:20", "12:10"),
    ("G", "12:10", "13:00"), ("H", "13:00", "13:50"), ("I", "13:50", "14:40"),
    ("J", "14:40", "15:30"), ("K", "15:30", "16:20"), ("L", "16:20", "17:10"),
]
LETRAS_FAIXA = "".join(f[0] for f in FAIXAS)
CARGA_ELETIVA = 60
HORAS_POR_FAIXA = 15  # 1 faixa por semana durante o semestre = 15h

RE_CODIGO = re.compile(r"^[A-Z]{4}\d{4}$")
RE_HORARIO = re.compile(r"^([2-6])([A-L])$")


# ------------------------------------------------------------- horários ----
def id_horario(dia, faixa):
    """HOR_ID de um dia (2..6) e faixa (A..L): segunda A = 1, sexta L = 60."""
    return (dia - 2) * len(FAIXAS) + LETRAS_FAIXA.index(faixa) + 1


def montar_horarios():
    """As 60 faixas da semana (tabela HOR_HORARIO)."""
    return [
        {"HOR_ID": id_horario(dia, letra), "HOR_DIA": dia, "HOR_FAIXA": letra,
         "HOR_INICIO": inicio, "HOR_FIM": fim}
        for dia in DIAS for letra, inicio, fim in FAIXAS
    ]


def ler_horario(codigo):
    """'2C' -> (2, 'C'). Levanta ValueError se o código não for dia 2-6 + faixa A-L."""
    m = RE_HORARIO.match(codigo.strip().upper())
    if not m:
        raise ValueError(f"horário inválido: {codigo!r} (esperado dia 2-6 + faixa A-L, ex.: 2C)")
    return int(m.group(1)), m.group(2)


def codigo_horario(hor_id):
    """1 -> '2A', 60 -> '6L'."""
    dia, idx = divmod(hor_id - 1, len(FAIXAS))
    return f"{dia + 2}{LETRAS_FAIXA[idx]}"


# ---------------------------------------------------------------- leitura --
def ler_csv(caminho):
    """Lê um CSV separado por ';' e devolve (número da linha, dicionário)."""
    with open(caminho, encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        return [(n, {k: (v or "").strip() for k, v in linha.items()})
                for n, linha in enumerate(leitor, start=2)]


def _inteiro(texto):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return None


# -------------------------------------------------------------- montagem ---
def montar_tabelas(oferta, perfil, semestre=SEMESTRE_OFERTA):
    """
    oferta, perfil: listas de (número da linha, dicionário), como em ler_csv.
    Retorna (tabelas, relatorio). tabelas tem as chaves PRO_PROFESSOR,
    DIS_DISCIPLINA, HOR_HORARIO, ALO_ALOCACAO e GRA_GRADE_HORARIA.
    """
    rel = {
        "semestre": semestre,
        "linhas_lidas": {"oferta": len(oferta), "cp21": len(perfil)},
        "linhas_ignoradas": [],
        "horarios_ignorados": [],
        "horarios_modificados": [],
        "divergencias_cp21": [],
        "avisos": [],
    }

    def ignorar(arquivo, linha, motivo, dados):
        rel["linhas_ignoradas"].append(
            {"arquivo": arquivo, "linha": linha, "motivo": motivo,
             "conteudo": "; ".join(v for v in dados.values() if v)})

    # Perfil CP21
    cp21 = {}
    for n, r in perfil:
        codigo, periodo, carga = r.get("codigo", ""), _inteiro(r.get("periodo")), _inteiro(r.get("carga_horaria"))
        if not RE_CODIGO.match(codigo):
            ignorar("perfil_cp21.csv", n, "código de disciplina inválido", r)
        elif periodo is None or not 1 <= periodo <= 10:
            ignorar("perfil_cp21.csv", n, "período inválido (esperado 1 a 10)", r)
        elif carga is None or carga <= 0:
            ignorar("perfil_cp21.csv", n, "carga horária inválida", r)
        elif codigo in cp21:
            ignorar("perfil_cp21.csv", n, "disciplina repetida no perfil", r)
        else:
            cp21[codigo] = {"periodo": periodo, "carga": carga, "descricao": r.get("descricao", ""),
                            "eletiva": r.get("tipo", "").lower().startswith("eletiva")}

    # Oferta (GradeProfessor)
    validas = []
    vistas = set()
    for n, r in oferta:
        professor = " ".join(r.get("professor", "").upper().split())
        codigo = r.get("codigo", "").upper()
        periodo = _inteiro(r.get("periodo"))
        if not professor:
            ignorar("grade_professor_2026_2.csv", n, "linha sem professor", r)
            continue
        if not RE_CODIGO.match(codigo):
            ignorar("grade_professor_2026_2.csv", n, "código de disciplina inválido", r)
            continue
        if periodo is None or not 1 <= periodo <= 10:
            ignorar("grade_professor_2026_2.csv", n, "período inválido (esperado 1 a 10)", r)
            continue
        if (professor, codigo) in vistas:
            ignorar("grade_professor_2026_2.csv", n, "professor x disciplina repetido", r)
            continue

        horarios = []
        for cod in r.get("horarios_atuais", "").replace(",", " ").split():
            try:
                dia, faixa = ler_horario(cod)
            except ValueError as erro:
                rel["horarios_ignorados"].append({"linha": n, "codigo": codigo, "horario": cod, "motivo": str(erro)})
                continue
            hor_id = id_horario(dia, faixa)
            if hor_id not in horarios:
                horarios.append(hor_id)
        if not horarios:
            ignorar("grade_professor_2026_2.csv", n, "nenhum horário válido", r)
            continue

        vistas.add((professor, codigo))
        original = r.get("horarios_originais", "")
        if original:
            rel["horarios_modificados"].append({
                "codigo": codigo, "disciplina": r.get("disciplina", ""),
                "original": " ".join(original.replace(",", " ").split()),
                "atual": " ".join(codigo_horario(h) for h in horarios)})
        validas.append({"linha": n, "professor": professor, "codigo": codigo, "periodo": periodo,
                        "descricao": r.get("disciplina", "").upper(),
                        "eletiva": r.get("eletiva", "").lower().startswith("s"),
                        "horarios": horarios})

    # Professores (ordem alfabética)
    nomes = sorted({v["professor"] for v in validas})
    professores = [{"PRO_ID": i, "PRO_NOME": nome, "PRO_MATRICULA": None} for i, nome in enumerate(nomes, 1)]
    pro_id = {p["PRO_NOME"]: p["PRO_ID"] for p in professores}
    if professores:
        rel["avisos"].append(f"Matrícula não informada nas fontes para os {len(professores)} professores "
                             "(PRO_MATRICULA fica vazia).")

    # Disciplinas (ordem em que aparecem na oferta)
    disciplinas, dis_id, eletivas_sem_cp21 = [], {}, []
    for v in validas:
        codigo = v["codigo"]
        if codigo in dis_id:
            continue
        perfil_cp = cp21.get(codigo)
        faixas = len(v["horarios"])
        if perfil_cp:
            carga = perfil_cp["carga"]
            if perfil_cp["periodo"] != v["periodo"]:
                rel["divergencias_cp21"].append({
                    "codigo": codigo, "disciplina": v["descricao"], "campo": "período",
                    "cp21": perfil_cp["periodo"], "oferta": v["periodo"],
                    "decisao": "mantido o período da oferta (é o que a coordenação usou na grade atual)"})
        elif v["eletiva"]:
            carga = CARGA_ELETIVA
            eletivas_sem_cp21.append(codigo)
        else:
            carga = faixas * HORAS_POR_FAIXA
            rel["avisos"].append(f"{codigo} {v['descricao']}: obrigatória fora do CP21; "
                                 f"carga {carga}h calculada pelas faixas da oferta.")
        if faixas * HORAS_POR_FAIXA != carga:
            rel["divergencias_cp21"].append({
                "codigo": codigo, "disciplina": v["descricao"], "campo": "carga horária",
                "cp21": f"{carga}h ({carga // HORAS_POR_FAIXA} faixas)",
                "oferta": f"{faixas} faixas ({faixas * HORAS_POR_FAIXA}h)",
                "decisao": "mantida a carga do CP21; a grade gerada usa carga / 15 faixas"})
        dis_id[codigo] = len(disciplinas) + 1
        disciplinas.append({"DIS_ID": dis_id[codigo], "DIS_CODIGO": codigo, "DIS_DESCRICAO": v["descricao"],
                            "DIS_PERIODO": v["periodo"], "DIS_CARGA_HORARIA": carga,
                            "DIS_ELETIVA": v["eletiva"]})

    if eletivas_sem_cp21:
        rel["avisos"].append(f"{len(eletivas_sem_cp21)} eletivas ({', '.join(eletivas_sem_cp21)}) não aparecem por "
                             f"código no CP21, que só reserva vagas \"Eletiva 60h\" no 9º e 10º períodos; "
                             f"receberam {CARGA_ELETIVA}h.")
    for codigo in sorted(set(cp21) - set(dis_id)):
        rel["avisos"].append(f"{codigo} {cp21[codigo]['descricao']}: está no CP21 mas não foi ofertada em {semestre}.")

    # Alocações e grade atual
    alocacoes, grade = [], []
    for v in validas:
        alo = {"ALO_ID": len(alocacoes) + 1, "PRO_ID": pro_id[v["professor"]], "DIS_ID": dis_id[v["codigo"]]}
        alocacoes.append(alo)
        grade += [{"GRA_SEMESTRE": semestre, "ALO_ID": alo["ALO_ID"], "HOR_ID": h} for h in v["horarios"]]

    tabelas = {
        "PRO_PROFESSOR": professores,
        "DIS_DISCIPLINA": disciplinas,
        "HOR_HORARIO": montar_horarios(),
        "ALO_ALOCACAO": alocacoes,
        "GRA_GRADE_HORARIA": grade,
    }
    rel["totais"] = {nome: len(linhas) for nome, linhas in tabelas.items()}
    return tabelas, rel


def montar_tabelas_das_fontes(semestre=SEMESTRE_OFERTA):
    """Atalho: lê os dois CSVs da pasta data/ e monta as tabelas."""
    return montar_tabelas(ler_csv(ARQUIVO_OFERTA), ler_csv(ARQUIVO_CP21), semestre)


# ------------------------------------------------------------- relatório ---
def relatorio_em_markdown(rel):
    t = rel["totais"]
    linhas = [
        "# Relatório da carga de dados",
        "",
        "Gerado por `database/data_ingestion/data_ingestion.py` a partir de "
        "`grade_professor_2026_2.csv` (GradeProfessor.pdf) e `perfil_cp21.csv` (perfil CP21).",
        "",
        "## Totais carregados",
        "",
        "| Tabela | Linhas |",
        "|---|---|",
    ] + [f"| `{nome}` | {qtd} |" for nome, qtd in t.items()] + [
        "",
        f"Linhas lidas: {rel['linhas_lidas']['oferta']} da oferta e {rel['linhas_lidas']['cp21']} do CP21. "
        f"Grade atual carregada no semestre `{rel['semestre']}`.",
        "",
        f"## Linhas ignoradas ({len(rel['linhas_ignoradas'])})",
        "",
    ]
    if rel["linhas_ignoradas"]:
        linhas += ["| Arquivo | Linha | Motivo | Conteúdo |", "|---|---|---|---|"]
        linhas += [f"| {i['arquivo']} | {i['linha']} | {i['motivo']} | {i['conteudo']} |" for i in rel["linhas_ignoradas"]]
    else:
        linhas.append("Nenhuma linha ignorada: todas as linhas das fontes eram válidas.")
    linhas += ["", f"## Horários ignorados ({len(rel['horarios_ignorados'])})", ""]
    if rel["horarios_ignorados"]:
        linhas += ["| Linha | Disciplina | Horário | Motivo |", "|---|---|---|---|"]
        linhas += [f"| {i['linha']} | {i['codigo']} | {i['horario']} | {i['motivo']} |" for i in rel["horarios_ignorados"]]
    else:
        linhas.append("Nenhum horário fora do padrão dia (2-6) + faixa (A-L).")
    linhas += [
        "", f"## Disciplinas com horário modificado ({len(rel['horarios_modificados'])})", "",
        "Carregadas com o horário atual, como pede a US-01.", "",
        "| Código | Disciplina | Original | Atual (carregado) |", "|---|---|---|---|",
    ] + [f"| {m['codigo']} | {m['disciplina']} | {m['original']} | {m['atual']} |" for m in rel["horarios_modificados"]]
    linhas += [
        "", f"## Divergências entre o CP21 e a oferta ({len(rel['divergencias_cp21'])})", "",
        "| Código | Disciplina | Campo | CP21 | Oferta 2026.2 | Decisão |", "|---|---|---|---|---|---|",
    ] + [f"| {d['codigo']} | {d['disciplina']} | {d['campo']} | {d['cp21']} | {d['oferta']} | {d['decisao']} |"
         for d in rel["divergencias_cp21"]]
    linhas += ["", "## Avisos", ""] + [f"- {a}" for a in rel["avisos"]] + [""]
    return "\n".join(linhas)


# ---------------------------------------------------------------- execução -
def main(argv=None):
    parser = argparse.ArgumentParser(description="Carga inicial do banco a partir do GradeProfessor e do CP21.")
    parser.add_argument("--banco", choices=["sqlite", "supabase"], default=None,
                        help="destino da carga (padrão: variável BANCO ou sqlite)")
    parser.add_argument("--simular", action="store_true", help="só valida e gera o relatório, sem gravar")
    args = parser.parse_args(argv)

    tabelas, rel = montar_tabelas_das_fontes()
    with open(ARQUIVO_RELATORIO, "w", encoding="utf-8") as f:
        f.write(relatorio_em_markdown(rel))

    print("Totais:", ", ".join(f"{k}={v}" for k, v in rel["totais"].items()))
    print(f"Linhas ignoradas: {len(rel['linhas_ignoradas'])} | horários modificados: "
          f"{len(rel['horarios_modificados'])} | divergências CP21: {len(rel['divergencias_cp21'])}")
    print(f"Relatório: {os.path.relpath(ARQUIVO_RELATORIO)}")
    if args.simular:
        return

    from database.repositorio import obter_repositorio
    repo = obter_repositorio(args.banco)
    repo.substituir_tudo(tabelas)
    print(f"Carga gravada no banco ({repo.descricao}).")


if __name__ == "__main__":
    main()
