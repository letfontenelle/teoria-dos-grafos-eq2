"""
Cliente do Supabase em memória para os testes: aceita as mesmas chamadas que
graphs/dados.py faz (table, select, eq, order, range, limit, delete, insert).
"""
from types import SimpleNamespace


class ClienteSupabaseFalso:
    def __init__(self, tabelas):
        self.tabelas = tabelas

    def table(self, nome):
        return _Consulta(self.tabelas, nome)


class _Consulta:
    def __init__(self, tabelas, nome):
        self.tabelas, self.nome = tabelas, nome
        self.acao, self.colunas, self.novas = "select", "*", None
        self.filtros, self.ordem, self.desc, self.inicio, self.fim = [], None, False, 0, None

    def select(self, colunas="*"):
        self.colunas = colunas
        return self

    def eq(self, coluna, valor):
        self.filtros.append((coluna, valor))
        return self

    def order(self, coluna, desc=False):
        self.ordem, self.desc = coluna, desc
        return self

    def range(self, inicio, fim):
        self.inicio, self.fim = inicio, fim + 1
        return self

    def limit(self, n):
        self.fim = self.inicio + n
        return self

    def delete(self):
        self.acao = "delete"
        return self

    def insert(self, linhas):
        self.acao, self.novas = "insert", linhas
        return self

    def execute(self):
        linhas = self.tabelas[self.nome]
        if self.acao == "insert":
            ids = {l["GRA_ID"] for l in linhas} if self.nome == "GRA_GRADE_HORARIA" else set()
            for l in self.novas:
                if self.nome == "GRA_GRADE_HORARIA" and (l.get("GRA_ID") is None or l["GRA_ID"] in ids):
                    raise ValueError("GRA_ID ausente ou repetido")  # o Supabase recusa: não tem valor padrão
                ids.add(l.get("GRA_ID"))
                linhas.append(dict(l))
            return SimpleNamespace(data=self.novas)
        alvo = [l for l in linhas if all(l[c] == v for c, v in self.filtros)]
        if self.acao == "delete":
            self.tabelas[self.nome] = [l for l in linhas if l not in alvo]
            return SimpleNamespace(data=alvo)
        if self.ordem:
            alvo = sorted(alvo, key=lambda l: l[self.ordem], reverse=self.desc)
        alvo = alvo[self.inicio:self.fim]
        if self.colunas != "*":
            colunas = [c.strip() for c in self.colunas.split(",")]
            alvo = [{c: l[c] for c in colunas} for l in alvo]
        return SimpleNamespace(data=[dict(l) for l in alvo])
