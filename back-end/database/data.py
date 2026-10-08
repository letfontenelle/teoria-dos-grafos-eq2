import sqlite3
connection = sqlite3.connect("upe.db")
cursor = connection.cursor()

#CRIANDO TABELAS

cursor.execute("""
CREATE TABLE IF NOT EXISTS pro_professor (
professor_id INTEGER PRIMARY KEY AUTOINCREMENT,
nome TEXT NOT NULL UNIQUE)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS dis_disciplina(

id_disciplina INTEGER PRIMARY KEY AUTOINCREMENT,
nome_disciplina TEXT NOT NULL UNIQUE,
professor_id INTEGER,
periodo INTEGER, 
FOREIGN KEY (professor_id) REFERENCES pro_professor(professor_id)
)


""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS id_cor(
id_cor INTEGER PRIMARY KEY,
nome_cor TEXT NOT NULL,
id_disciplina INTEGER,
FOREIGN KEY (id_disciplina) REFERENCES dis_disciplina(id_disciplina)


)



""")

#FUNÇÕES DE INSERÇÃO

def adicionar_professor(nome):
    cursor.execute("""
    SELECT professor_id
    FROM pro_professor
    WHERE nome = ?
    """, (nome,))

    professor = cursor.fetchone()

    if professor:
        return professor[0]

    cursor.execute("""
    INSERT INTO pro_professor (nome)
    VALUES (?)
    """, (nome,))

    return cursor.lastrowid

def adicionar_disciplina(nome, professor_id, periodo):
    cursor.execute("""
    SELECT id_disciplina
    FROM dis_disciplina
    WHERE nome_disciplina = ?
    """, (nome,))

    disciplina = cursor.fetchone()

    if disciplina:
        return disciplina[0]

    cursor.execute("""
    INSERT INTO dis_disciplina (
        nome_disciplina,
        professor_id,
        periodo
    )
    VALUES (?, ?, ?)
    """, (nome, professor_id, periodo))

    return cursor.lastrowid

cores = [
    (1, "cor_1"),
    (2, "cor_2"),
    (3, "cor_3"),
    (4, "cor_4"),
    (5, "cor_5"),
    (6, "cor_6"),
    (7, "cor_7"),
    (8, "cor_8"),
    (9, "cor_9"),
    (10, "cor_10"),
    (11, "cor_11"),
    (12, "cor_12"),
    (13, "cor_13"),
    (14, "cor_14"),
    (15, "cor_15"),
    (16, "cor_16"),
    (17, "cor_17"),
    (18, "cor_18")
]

cursor.executemany("""
INSERT OR IGNORE INTO id_cor (id_cor, nome_cor)
VALUES (?, ?)
""", cores)

def atribuir_disciplina(id_cor, id_disciplina):
    cursor.execute("""
    UPDATE id_cor
    SET id_disciplina = ?
    WHERE id_cor = ?
    """, (id_disciplina, id_cor))


#INSERINDO EXEMPLOS

eliane_id = adicionar_professor("Eliane Loyola")

grafos_id = adicionar_disciplina(
    "Teoria dos Grafos",
    eliane_id,
    5
)


import pandas as pd

df_professores = pd.read_sql_query(
    "SELECT * FROM pro_professor",
    connection,
    index_col="professor_id"
)

print(df_professores, "\n")


df_disciplinas = pd.read_sql_query(
    "SELECT * FROM dis_disciplina",
    connection,
    index_col="id_disciplina"
)

print(df_disciplinas, "\n")


df_cores = pd.read_sql_query(
    "SELECT * FROM id_cor",
    connection,
    index_col="id_cor"
)

print(df_cores, "\n")

#salvar
connection.commit()
#fechar
connection.close()
