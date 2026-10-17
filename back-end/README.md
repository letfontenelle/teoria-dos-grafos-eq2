# Back-end: geração da grade horária

Monta a grade de horários dos professores **sem choques**, com grafos e coloração. Com os dados reais de 2026.2 (48 alocações, 10 períodos), gera tudo de uma vez com 0 choques.

## Como funciona

- Cada aula vira **sessões** de 2 faixas (um bloco); uma aula de 3 faixas vira uma sessão contínua. Número de faixas por semana = faixas que a aula tem na grade atual (a carga horária, faixas × 15h, não está no banco).
- O **grafo** liga as sessões que não podem ser juntas: mesmo professor, mesmo período ou mesma disciplina. (O código aceita a exceção de duas eletivas do mesmo período, mas o banco ainda não diz quais disciplinas são eletivas.)
- A **busca gulosa** coloca cada sessão no primeiro bloco livre de conflito. A próxima sessão é escolhida pela ordem alfabética do professor, pelo maior grau ou pelo **DSATUR** (maior saturação primeiro).
- A semana tem 6 blocos por dia, de 2 faixas cada. Em código interno são A a F; na tela, aparecem no padrão da POLI: AB (07:10), CD (08:50), EF (10:30), GH (12:10), IJ (13:50) e KL (15:30).
- **Manhã primeiro**: a tarde só entra se não couber.

## Arquivos

- `main.py`: API FastAPI e servidor do front-end.
- `database/` (equipe de dados): conexão com o Supabase (`connection/connect.py`), planilha `data/modelo_grade_professor.xlsx` e carga no Supabase (`data_ingestion/data_ingestion.py`).
- `graphs/dados.py`: lê as tabelas do Supabase (`PRO_`, `DI_`, `HO_`, `ALO_`, `GRA_`) e grava as grades salvas; traduz para o formato do grafo.
- `graphs/graph.py`: monta o grafo de conflitos das alocações e exporta em JSON.
- `graphs/coloracao.py`: guloso e DSATUR implementados pela equipe.
- `graphs/agendamento.py`: divide as aulas em sessões, faz a busca gulosa e valida os choques.
- `graphs/grade.py`: grafo <-> grade <-> banco (coloração parcial, mover aula, salvar).
- `demo_grade.py`: mostra a grade no terminal, sem banco de dados.
- `testes/`: 59 testes (pytest), com a planilha e um Supabase simulado em memória.

## Como rodar

Precisa de Python 3.10 ou mais novo. De dentro de `back-end`:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload       # abre em http://localhost:8000
```

Outros comandos:

```bash
python -m pytest testes -v                       # testes
python database/data_ingestion/data_ingestion.py # carga da planilha no Supabase (pula tabelas com dados)
python graphs/graph.py                           # exporta graph.json e desenha o grafo
python demo_grade.py 7 --dsatur                  # grade do 7º período no terminal
```

A API precisa do `.env` com as chaves do Supabase: copie `.env.example` (na raiz do repositório) para `.env` e preencha. Salvar uma grade grava na `GRA_GRADE_HORARIA` com outro semestre; a grade 2026.2 (carga da equipe de dados) não é sobrescrita.

## Falta (decisões para validar com a professora)

- Salas: o modelo ainda não tem salas (itens opcionais 10, 16 e 17).
- Uso do bloco GH (12:10–13:50), que atravessa o almoço. Hoje é evitado pela preferência de manhã.
- Dados que ainda não estão no banco (equipe de dados): carga horária, quais disciplinas são eletivas e Redes de Computadores 2. Sem a marcação de eletiva, a grade atual aparece com 6 choques entre disciplinas do mesmo período.
