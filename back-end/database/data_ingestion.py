#Adicionar arquivos csv para enviar para as tabelas no supabase
import pandas as pd
from connect import supabase

tabelas = [
    ('professor.csv', 'PROFESSOR'),
    ('disciplina.csv', 'DISCIPLINA'),
    ('horario.csv', 'HORARIO'),
    ('alocacao.csv', 'ALOCACAO'),       
    ('grade_horaria.csv', 'GRADE_HORARIA') 
]

def csv_supabase(tabelas):
    for arquivo, tabela in tabelas:
        df = pd.read_csv(arquivo)
        df = df.where(pd.notnull(df), None)
        data = df.to_dict(orient='records')
        response = supabase.table(tabela).upinsert(data).execute()
        print(f"Dados inseridos na tabela {tabela}: {response.data}")    
  
    
