##conectar com banco 
cur = conn.cursor()

def tabela_curso(cur):
    cur.execute("""CREATE TABLE curso(
            CURSO_ID SERIAL PRIMARY KEY,
            CURSO_NOME VARCHAR(100) NOT NULL
            )""")


conn.commit()

cur.close()
conn.close()