##conectar com banco 
cur = conn.cursor()

def table_curso(cur):
    cur.execute("""CREATE TABLE curso(
            CURSO_ID SERIAL PRIMARY KEY,
            CURSO_NOME VARCHAR(100) NOT NULL
            )""")
    
def table_perfil_curricular(cur):
    cur.execute("""CREATE TABLE PERFIL_CURRICULAR(
            PERFIL_ID SERIAL PRIMARY KEY,
            PERFIL_TIPO VARCHAR(100) NOT NULL
            )""")
    
def table_disciplina(cur):
    cur.execute("""CREATE TABLE DISCIPLINA(
            DISCIPLINA_ID SERIAL PRIMARY KEY,
            DISCIPLINA_CODIGO VARCHAR(100) NOT NULL, 
            DISCIPLINA_DESCRICAO VARCHAR(100) NOT NULL,
            DISCIPLINA_PERIODO VARCHAR(100) NOT NULL
            )""")   
    
def table_professor(cur):
    cur.execute("""CREATE TABLE PROFESSOR(
            PRO_ID SERIAL PRIMARY KEY,
            PRO_NOME VARCHAR(100) NOT NULL, 
            PRO_MATRICULA integer NOT NULL
            )""")
                    


conn.commit()

cur.close()
conn.close()