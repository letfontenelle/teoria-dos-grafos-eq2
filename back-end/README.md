# Back-end: geração da grade horária

Monta a grade de horários dos professores **sem choques**, com grafos e busca gulosa. Com os dados de exemplo (48 aulas, 10 períodos), gera tudo de uma vez com 0 choques.

## Como funciona

- Cada aula vira **sessões** de 2 horários (um bloco).
- O **grafo** liga as sessões que não podem ser juntas: mesmo professor ou mesmo período.
- A **busca gulosa** coloca cada sessão (em ordem alfabética do professor) no primeiro bloco livre de conflito.
- A semana tem 6 blocos por dia: A (07:10), B (08:50), C (10:30), D (12:10), E (13:50) e F (15:30), de 2 horários cada.
- **Manhã primeiro** (A, B, C): a tarde só entra se não couber.
- Duração = carga horária ÷ 15: 4 horários viram 2 sessões em dias diferentes, e 3 horários viram uma sessão contínua (ex.: 10:30 às 13:00).

## Arquivos

- `graphs/graph.py`: monta o grafo de conflitos.
- `graphs/agendamento.py`: divide as aulas, faz a busca gulosa e valida os choques.
- `demo_grade.py`: mostra a grade na tela, sem banco de dados.
- `testes/test_agendamento.py`: 18 testes.

## Como rodar

Precisa de Python 3.10 ou mais novo.

```powershell
git clone -b gabriel-agendamento https://github.com/Gabriel-Esteves-0404/teoria-dos-grafos-eq2.git
cd teoria-dos-grafos-eq2
python -m venv venv
venv\Scripts\Activate.ps1
cd back-end
pip install -r requirements.txt
python demo_grade.py
python -m pytest testes -v
```

Para outro período, `python demo_grade.py 7`. Para desenhar o grafo, `--grafo`. Não precisa de `.env` para a demo. Para usar o Supabase, copie `.env.example` para `.env` e preencha as chaves (nunca faça commit do `.env`).

## Falta

- Gravar a grade no Supabase (`GRA_GRADE_HORARIA`) e entregar o JSON para o front.
- Coluna de carga horária na tabela de disciplinas (hoje as durações vêm da planilha de exemplo).
- A confirmar com a professora: salas (hoje chega a 7 aulas ao mesmo tempo), uso do bloco D (atravessa o almoço) e o "perfil curricular e pleno".