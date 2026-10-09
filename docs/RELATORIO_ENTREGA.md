# Relatório de entrega — Iterações 03, 04 e 06

Equipe 02 · Projeto de Teoria dos Grafos · 08/10/2026

## 1. Situação antes desta entrega

A professora cobrou a equipe três vezes no Classroom e no Trello:

| Data | Onde | O que foi dito |
|---|---|---|
| 20/09 | Card *Modelo de Dados* | "Não está finalizado, favor fazer as correções solicitadas em sala de aula para o modelo de dados." |
| 20/09 | Card *Modelo em grafos* | Para concluir o card: (1) grafo em memória a partir do modelo de dados; (2) grade no front-end a partir do grafo (sem cor = vazia, parcial, completa); (3) grade salva no banco; (4) extra: mover a aula na tela muda a cor no grafo. |
| 24/09 | Atividade *Iteração 04* | A equipe não concluiu a Iteração 03, começou a 04 e não concluiu. Não deve iniciar novos cards antes de concluir os iniciados. |
| 05/10 | Atividade *Iteração 06* | "Vocês pararam de fazer entregas." Se os itens em atraso não forem entregues **nesta semana**, a equipe é desclassificada. Cada integrante deve escolher entre um plano de recuperação e voltar às aulas teóricas (1º EE em 15/10). |

No repositório, a `main` só tinha a estrutura inicial. O trabalho estava espalhado em branches e num fork: a carga no Supabase (Giovanna), o grafo e o DSATUR (Edward), o agendamento (Gabriel, PR #4) e os testes (Dyhego, PR #2). O projeto do Supabase está **pausado**: o endereço não resolve.

## 2. O que estava pendente

Levantamento feito no Classroom (instruções e devolutivas de cada atividade), no Trello (checklists e comentários) e nos materiais da professora (GradeProfessor.pdf, perfil CP21, relatório da UFOP).

| Iteração | Item cobrado | Situação em 07/10 |
|---|---|---|
| 03 | Modelo conceitual com as correções (nomenclatura, entidades da devolutiva, siglas de 3 letras) | Siglas de 3 letras pendentes (`DI_`, `HO_`); card em CONCLUÍDO com checklist 9/17 |
| 03 | Modelo lógico e modelo físico | Pendentes |
| 03 | UX: tela grade por professor e tela gerar grade | Figma só com a visão por professor; sem tela de gerar grade |
| 04 | Carga de dados (CP21 com carga horária; horários no padrão 2C tratando horário modificado; relatório de linhas ignoradas) | Planilha manual, sem carga horária, sem Redes de Computadores 2, sem relatório |
| 04 | Grafo em memória a partir do modelo de dados | Feito (Edward), mas lendo do Supabase pausado |
| 04 | Grade no front-end a partir do grafo (vazia, parcial, completa) | Não existia front-end |
| 04 | Grade salva no banco | Não feito |
| 04 | Extra: grafo a partir da grade editada no front-end | Não feito |
| 06 | Algoritmo de coloração implementado pela equipe, grade viável com carga/15 faixas, por período e por professor | Agendamento do Gabriel pronto (PR #4), sem carga horária, sem tela e sem persistência |

## 3. O que foi feito

Todo o código está no PR [#5](https://github.com/letfontenelle/teoria-dos-grafos-eq2/pull/5), que inclui os PRs #4 (Gabriel) e #2 (Dyhego). São 66 testes automatizados, todos passando.

### Iteração 03 — Modelo de dados
- Modelos **conceitual, lógico e físico** em [`docs/modelo-de-dados.md`](modelo-de-dados.md) e [`back-end/database/schema.sql`](../back-end/database/schema.sql).
- Correções da devolutiva: siglas de 3 letras (`DIS_DISCIPLINA`, `HOR_HORARIO`), colunas `SIGLA_ATRIBUTO` e as entidades pedidas (PROFESSOR, DISCIPLINA, ALOCAÇÃO, GRADE HORÁRIA). Também foram acrescentados `DIS_CARGA_HORARIA` e `DIS_ELETIVA`.
- [`migracao_supabase.sql`](../back-end/database/migracao_supabase.sql) para trocar as tabelas antigas quando o Supabase for reativado.

### Iteração 03 — UX
- Figma, seção **05 · Telas pendentes da Iteração 03**: telas *Grade por período* e *Gerar grade — coloração passo a passo*, montadas com os componentes e tokens do arquivo. Também foram criados os componentes Botão, Métrica, Progresso do período e o estado *Parcial* da faixa de status.
- As telas estão **implementadas** no sistema com os tokens e os três estados do protótipo (sem conflito, com conflito, vazio).

### Iteração 04 — Carga de dados e modelo em grafos
- **Carga** a partir dos materiais da professora: 26 professores, 48 disciplinas, 60 faixas, 48 alocações e 181 linhas da grade atual.
  - Horários no padrão **dia + faixa** (ex.: 2C).
  - As **7 disciplinas com horário modificado** entram com o horário atual.
  - Carga horária vem do **CP21**.
  - **Relatório de linhas ignoradas** em [`relatorio_carga.md`](../back-end/database/data/relatorio_carga.md).
- **Grafo em memória** a partir do banco: alocações (48 vértices, 118 arestas) e sessões de aula (89 vértices, 427 arestas).
- **Grade no front-end a partir do grafo:** a aba *Gerar grade* mostra a coloração passo a passo, de grafo sem cor (grade vazia) a parcial e completa.
- **Grade salva no banco:** *Salvar* grava na `GRA_GRADE_HORARIA`; *Carregar* reinstancia o grafo a partir da grade salva.
- **Extra:** arrastar uma aula na tela troca a cor do vértice no grafo e mostra os conflitos em vermelho.
- **Validação contra a realidade:** a grade atual da coordenação tem **0 conflitos** no modelo. Isso usa a regra descoberta nos dados: duas eletivas do mesmo período podem coincidir.

### Iteração 06 — Algoritmo de coloração e grade viável
- **DSATUR e guloso implementados pela equipe** (`graphs/coloracao.py`), com o desempate da referência da Iteração 06 (saturação, grau, id).
- No grafo de sessões, o DSATUR usa **13 cores = maior clique**, ou seja, é **ótimo** (atinge o número cromático). O guloso simples usa 14.
- **Grade gerada sem choques**, com carga/15 faixas por disciplina, exibida por período e por professor; gerar, salvar e carregar pela API.

### Documentação e repositório
- README com como rodar, [modelagem em grafos](../back-end/graphs/MODELAGEM.md), modelo de dados, relatório da carga e este relatório.
- `.gitignore`, `.env.example`, `requirements.txt` e os testes do Dyhego passando a ser executados (o arquivo se chamava `teste.py` e o pytest não o encontrava).

## 4. Trello

| Card | Antes | Depois |
|---|---|---|
| Modelo de Dados (It. 03) | CONCLUÍDO, checklist 9/17 | **VALIDANDO**, tudo marcado menos *Validação do PO*; link do modelo anexado; comentário com as correções |
| Projeto UX (It. 03) | CONCLUÍDO, sem as telas pendentes | **VALIDANDO**; comentário com o link da seção nova do Figma |
| Modelo em grafos (It. 04) | FAZENDO, 4/15 | **VALIDANDO**, tudo marcado menos *Validação do PO*; *Problemas encontrados* preenchido; comentário respondendo aos 4 itens da professora |
| Algoritmo de coloração (It. 06) | BACKLOG, 0/14 | **VALIDANDO**, tudo marcado menos *Validação do PO*; comentário com os resultados |

Os cards só vão para CONCLUÍDO depois da validação da professora, como ela definiu.

## 5. O que depende da equipe

1. **Responder à professora no Classroom (cada integrante).** Ela pediu que cada um escolha entre plano de recuperação e aulas teóricas. Sugestão de texto na seção 7.
2. **Revisar e mergear o PR #5.** Pela definição de pronto da equipe, alguém além da autora deve aprovar. Ao mergear, os PRs #4 e #2 são fechados automaticamente.
3. **Fechar o PR #1 (SQLite do Daniel).** Ele foi superado pelo `repositorio.py`, que tem SQLite local e Supabase com o mesmo schema.
4. **Reativar o Supabase** (Giovanna, dona do projeto). Depois, rodar `migracao_supabase.sql` + `schema.sql` no SQL Editor e `python -m database.data_ingestion.data_ingestion --banco supabase`. Até lá, o sistema funciona com SQLite local.
5. **Validar com a professora** as divergências entre o CP21 e a oferta: período de Compiladores, IHC, Projeto em Eng. da Computação e PFC; carga do PFC.
6. **Marcar a entrega no Classroom.** As atividades das Iterações 05 e 06 aparecem como "Não entregue".

Opcionais ainda não feitos: cadastros de curso e disciplina (Iteração 05) e de professor e horário (Iteração 07).

## 6. Roteiro de demonstração (5 minutos)

1. `cd back-end && uvicorn main:app` e abrir http://localhost:8000.
2. **Dados e carga:** fontes, 0 linhas ignoradas, 7 horários modificados, divergências com o CP21.
3. **Grade → Por período (5º):** grade atual da coordenação, "Sem conflitos nesta grade".
4. **Gerar grade → Gerar grade (DSATUR):** voltar ao passo 0 (grade vazia), animar (grade parcial, progresso por período) e chegar ao fim (completa). Mostrar "13 cores = maior clique".
5. **Grade → arrastar uma aula** para o horário de outra do mesmo período: o vértice muda de cor e aparece "Conflito de horário".
6. **Salvar** como 2027.1 e **Carregar**: o grafo volta a partir do banco.
7. **Grafo de conflitos:** o 5º período forma uma clique (todas as obrigatórias se conflitam).

## 7. Sugestão de resposta à professora (plano de recuperação)

> Professora, a Equipe 02 opta pelo plano de recuperação. Até 08/10 colocamos em validação no Trello os itens em atraso: Modelo de Dados (conceitual, lógico e físico com as correções e siglas de 3 letras), Projeto UX (telas de grade por período e de gerar grade no Figma e no sistema), Modelo em grafos com carga de dados (os 4 itens do seu comentário no card) e o Algoritmo de coloração (DSATUR implementado pela equipe, grade viável sem choques). Cada card tem o link do código e o comentário do que foi feito. Gostaríamos de apresentar a demonstração no próximo acompanhamento e seguir o cronograma a partir da Iteração 07.

## 8. Decisões técnicas e desvios em relação à Iteração 02

| Planejado | Feito | Motivo |
|---|---|---|
| Front-end em Next.js | HTML, CSS e JavaScript servidos pela API | Entregar nesta semana sem etapa de build; a migração continua possível |
| SQLAlchemy + Alembic | `schema.sql` versionado + repositório SQLite/Supabase | A equipe já usava o cliente do Supabase; o SQL atende o modelo físico pedido |
| PostgreSQL | PostgreSQL (Supabase) + SQLite local como alternativa | O Supabase está pausado; o mesmo schema roda nos dois |
| Planilha manual de dados | CSVs extraídos do GradeProfessor.pdf e do CP21 | A planilha não tinha Redes de Computadores 2 nem a carga horária, e a US-01 pede carga a partir dos materiais |
| Período do CP21 | Período da oferta, com divergências no relatório | É o que a coordenação usa na grade atual (com ele, a grade atual tem 0 conflitos) |
