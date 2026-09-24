Projeto De Teoria dos Grafos - Equipe 02
# Modelagem do Grafo para Montagem da Grade Horária

## 1. Mapeamento do Banco de Dados para o Grafo
Para a resolução do problema de agendamento de horários (Perfil Curricular e Pleno), o problema foi mapeado para um **Grafo de Conflitos para Coloração**:

* **Vértices (Nós - $V$):** Representam os registros da tabela `ALO_ALOCACAO`.
  * Cada nó é uma oferta de aula que necessita de um slot de horário.
  * **Atributos do Nó:** `PRO_ID` (Professor) e `DI_PERIODO` (Período/Perfil Curricular vindo de `DI_DISCIPLINA`).

* **Arestas (Incompatibilidades/Conflitos - $E$):**
  Uma aresta não direcionada conecta dois nós de alocação $A$ e $B$ quando existe restrição de horário:
  1. **Conflito de Professor:** $A.\text{PRO\_ID} == B.\text{PRO\_ID}$ (Um professor não ministra duas aulas no mesmo horário).
  2. **Conflito de Perfil Pleno / Curricular:** $A.\text{DI\_PERIODO} == B.\text{DI\_PERIODO}$ (Disciplinas do mesmo período não podem ter choque de horário para o aluno pleno).

* **Cores (Slots de Horário):**
  * As cores disponíveis no algoritmo correspondem aos registros da tabela `HO_HORARIO`.
  * **Objetivo:** Aplicar o algoritmo de coloração de grafos (ex: DSATUR) de modo que dois nós conectados por uma aresta recebam cores (horários) distintas.
  * O resultado final é persistido na tabela `GRA_GRADE_HORARIA`.