#Adicionar arquivos csv para enviar para as tabelas no supabase

import pandas as pd
from connect import supabase

# Busca os dados e exibe no formato DataFrame
res = supabase.table("PROFESSOR").select("*").execute()
print(res.data)