import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.connection.connect import supabase

caminho_excel = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/modelo_grade_professor.xlsx'))
dados_excel = pd.read_excel(caminho_excel, sheet_name=None)

print("Abas reais do Excel:", list(dados_excel.keys()))

tabelas = [
    ('PRO_PROFESSOR', 'PRO_PROFESSOR'),
    ('DI_DISCIPLINA', 'DI_DISCIPLINA'),
    ('HO_HORARIO', 'HO_HORARIO'),
    ('ALO_ALOCACAO', 'ALO_ALOCACAO'),
    ('GRA_GRADE_HORARIA', 'GRA_GRADE_HORARIA')
]

def csv_supabase(tabelas):
    if not supabase:
        print("Erro: Conexão com o Supabase não estabelecida.")
        return None
    
    for arquivo, tabela in tabelas:
        check = supabase.table(tabela).select("*", count="exact").limit(1).execute()
        if check.count > 0:
            print(f"A tabela {tabela} já possui dados. Pulando inserção.")
            continue
        df = dados_excel[arquivo]
        mapeamento_colunas = {
            'DIA': 'HO_DIA',
            'HORARIO': 'HO_HORARIO',
            'COR': 'HO_COR'
        }
        df = df.rename(columns=mapeamento_colunas)
        
        data = [{k: (None if pd.isna(v) else v) for k, v in rec.items()} for rec in df.to_dict(orient='records')]
        
        response = supabase.table(tabela).upsert(data).execute()
        print(f"Dados inseridos na tabela {tabela}: {response.data}")
        
        
def gestao_dados(tabelas):
    print("INFORMAÇÃO DOS DADOS INSERIDOS NO SUPABASE:")
    for arquivo, tabela in tabelas:
        supabase_info = supabase.table(tabela).select("*").execute()
        print(supabase_info.data)

if __name__ == "__main__":
    csv_supabase(tabelas)
    print("Dados inseridos com sucesso no Supabase.")
    gestao_dados(tabelas)
    
