# Modelagem do Grafo para Montagem da Grade Horária

Itens 14 (modelo em grafos, Iteração 04) e 15 (algoritmo de coloração, Iteração 06) do backlog.

## 1. Mapeamento do Banco de Dados para o Grafo

O problema de agendamento (perfil curricular e aluno pleno) é mapeado para um **grafo de conflitos para coloração**.

* **Vértices ($V$):**
  * No grafo de **alocações** (`construir_grafo_conflitos`), cada vértice é um registro de `ALO_ALOCACAO` (professor x disciplina), com os atributos `PRO_ID`, `DIS_PERIODO` e `DIS_ELETIVA` vindos do banco.
  * No grafo de **sessões** (`construir_grafo_sessoes`, usado na grade), cada alocação vira uma ou mais sessões de aula: carga horária / 15 faixas por semana, divididas em blocos de 2 faixas (uma aula de 3 faixas é uma sessão contínua). Uma disciplina de 60h tem 2 sessões, por exemplo.

* **Arestas ($E$):** dois vértices $A$ e $B$ são ligados quando não podem ocupar o mesmo horário:
  1. **Conflito de professor:** $A.\text{PRO\_ID} = B.\text{PRO\_ID}$. Um professor não ministra duas aulas ao mesmo tempo.
  2. **Conflito de perfil pleno/curricular:** $A.\text{DIS\_PERIODO} = B.\text{DIS\_PERIODO}$, **exceto quando as duas são eletivas**. O aluno blocado precisa conseguir cursar todas as obrigatórias do seu período e qualquer eletiva junto com elas; entre duas eletivas, ele escolhe, então elas podem coincidir.
  3. **Mesma disciplina** (só no grafo de sessões): as sessões da mesma alocação não podem coincidir.

* **Cores:** a cor de um vértice é o horário que ele ocupa. No grafo de sessões, cada cor é um **bloco** de faixas seguidas de `HOR_HORARIO` (ex.: `2C 2D` = segunda, 08:50–10:30). Uma coloração própria (vizinhos com cores diferentes) é uma grade sem choques.
* **Persistência:** a coloração vira linhas de `GRA_GRADE_HORARIA` (`ALO_ID`, `HOR_ID`, `GRA_SEMESTRE`). O caminho inverso também existe: uma grade salva no banco é lida e transformada de novo em grafo colorido (`GradeEmMemoria.de_linhas`).

### Por que a regra das eletivas

Aplicando o modelo à grade **atual** da coordenação (GradeProfessor.pdf, semestre 2026.2), a única fonte de "choque" eram 3 pares de **eletivas** do mesmo período (9º: Computação Natural x Métodos Formais; 10º: Formação de Empreendedores x PDI e Conversão Eletromecânica x Redes Neurais). Nenhuma obrigatória colide com outra do mesmo período, nem com eletiva do mesmo período. Com a regra, a grade real tem **0 conflitos** no modelo, o que valida a modelagem contra a realidade (teste `test_grade_atual_da_coordenacao_nao_tem_conflitos_no_modelo`).

## 2. Algoritmos de coloração (implementados pela equipe)

Conforme a Iteração 02, o NetworkX é usado só como estrutura de grafo. Os algoritmos estão em `coloracao.py`, seguindo a referência da Iteração 06 (Vieira, *Heurística Matemática Aplicada ao Problema da Coloração de Grafos*, UFOP, seção 4.3.1) e Brélaz (1979):

* **Guloso sequencial:** cada vértice, na ordem dada, recebe a menor cor que nenhum vizinho já colorido usa.
* **DSATUR (Degree of Saturation):** a cada passo escolhe o vértice sem cor com **maior grau de saturação** (quantas cores diferentes os vizinhos já têm). Empate: maior grau. Depois: menor id. O vértice recebe a menor cor disponível.
* **Limite inferior:** o tamanho da maior clique ($\omega(G)$). Todos os vértices de uma clique precisam de cores diferentes, então $\chi(G) \ge \omega(G)$. Se a coloração usa $\omega(G)$ cores, ela é ótima.

Na **geração da grade** (`agendamento.py`), a busca gulosa do Gabriel coloca as sessões em blocos de horário respeitando preferências de turno (manhã primeiro) e espalhando as sessões da mesma disciplina em dias diferentes. A ordem em que as sessões são escolhidas pode ser alfabética por professor, por maior grau ou **DSATUR** (padrão no front-end).

## 3. Resultados com os dados reais (2026.2)

| Grafo | Vértices | Arestas | DSATUR | Guloso | Maior clique | Ótimo? |
|---|---|---|---|---|---|---|
| Alocações (professor x disciplina) | 48 | 118 | 7 cores | 7 cores | 7 | sim |
| Sessões (blocos de aula) | 89 | 427 | 13 cores | 14 cores | 13 | DSATUR sim, guloso não |

* A grade gerada tem **0 choques** de professor ou de período, e cada disciplina recebe exatamente carga / 15 faixas (testes em `testes/test_grade_memoria.py`).
* Gerar a grade completa leva poucos milissegundos.

## 4. Do grafo para a grade, e da grade para o grafo

O card do item 14 pede quatro coisas, todas em `grade.py` e expostas pela API (`main.py`):

1. **Grafo em memória a partir do modelo de dados:** `GradeEmMemoria.gerar(dados)` e `GradeEmMemoria.de_linhas(dados, linhas)` leem as tabelas do banco.
2. **Grade no front-end a partir do grafo:** `GET /api/grade?passo=k` devolve só os $k$ primeiros vértices coloridos. Com o grafo **sem cor**, a grade é **vazia**; **parcialmente colorido**, a grade é **parcial**; **totalmente colorido**, a grade é **completa**.
3. **Grade no modelo de dados:** `POST /api/grade/salvar` grava a grade em memória (gerada ou editada na tela) em `GRA_GRADE_HORARIA`.
4. **Extra: grafo a partir da grade editada no front-end.** Arrastar uma aula para outra faixa chama `POST /api/grade/mover`. O vértice troca de cor no grafo e os conflitos com os vizinhos são recalculados e mostrados em vermelho.

## Justificativa técnica

* **Complexidade:** coloração de grafos é NP-difícil. O DSATUR é $O(n^2)$ e, com os dados reais, atinge o limite inferior da maior clique, ou seja, encontra o número cromático.
* **Garantia de zero conflitos:** antes de dar uma cor a um vértice, o algoritmo descarta as cores já usadas pelos vizinhos. Um validador independente (`validar_grade`) confere a grade pronta faixa a faixa.
