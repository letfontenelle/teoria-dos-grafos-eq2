import os
from dotenv import load_dotenv

load_dotenv()


def conectar_supabase():
    """
    Cria o cliente do Supabase com as chaves do .env.

    A conexão só é feita quando alguém pede (antes era feita ao importar o
    módulo, o que quebrava qualquer script quando o .env não existia).
    """
    from supabase import create_client

    db_url = os.getenv("SUPABASE_URL")
    db_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not db_url or not db_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY precisam estar no .env (veja .env.example).")
    return create_client(db_url, db_key)
