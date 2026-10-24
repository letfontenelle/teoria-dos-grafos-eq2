# Projeto de Teoria dos Grafos - Equipe 02
## Modelagem do Grafo para Montagem da Grade Horária

Este repositório contém a modelagem em grafos e os algoritmos desenvolvidos para a resolução do problema de agendamento de horários (Perfil Curricular e Pleno).

---

## 1. Mapeamento do Banco de Dados para o Grafo

O problema foi mapeado para um **Grafo de Conflitos para Coloração** $G = (V, E)$:

* **Vértices (Nós - $V$):** Representam os registros de aulas a serem alocadas (tabela `ALO_ALOCACAO`).
  * Cada nó possui os atributos `PRO_ID` (Professor) e `DI_PERIODO` (Período/Perfil Curricular da disciplina).
* **Arestas (Incompatibilidades / Conflitos - $E$):** Conectam duas alocações sempre que houver restrição de horário simultâneo:
  1. **Conflito de Professor:** Um professor não pode ministrar duas aulas no mesmo horário.
  2. **Conflito de Perfil Curricular / Pleno:** Disciplinas do mesmo período não podem ter choque de horário para o aluno pleno.
* **Cores (Slots de Horário):** Representam os horários disponíveis (tabela `HO_HORARIO`).

---

## 2. Estratégia Algorítmica e Validação Matemática

Para responder com precisão tanto aos requisitos teóricos da disciplina quanto às restrições operacionais do sistema, o projeto adota duas abordagens complementares:

### 2.1. Modelo Teórico e Validação Limite (DSATUR)
Para análise gráfica e determinação do número cromático mínimo, utilizou-se a heurística **DSATUR (Degree of Saturation)** via `NetworkX`:
* **Resultado de Cores:** O DSATUR encontra uma solução válida utilizando **7 cores (slots de tempo)**.
* **Prova Teórica (Clique Máxima):** A maior clique ($\omega(G)$) identificada no grafo possui tamanho **7** (grupo de 7 aulas com conflitos mútuos). Como $\chi(G) \ge \omega(G)$, o resultado de 7 cores garante o limite inferior ótimo teórico para o conjunto de dados.

### 2.2. Geração Operacional da Grade
Para atender às regras de negócio da instituição (aulas agrupadas em blocos contínuos de 2h), a persistência na tabela `GRA_GRADE_HORARIA` utiliza busca gulosa com agendamento estruturado em blocos.

---

## 3. Capacidades de Instanciação do Grafo (`graph.py`)

O módulo `graphs/graph.py` foi atualizado para carregar a estrutura do grafo em memória sob múltiplos cenários:

1. **Instanciação a partir de Alocações Brutas (`construir_grafo_conflitos`):** Consome os dados brutos da tabela `ALO_ALOCACAO` e constrói o grafo de incompatibilidades antes do agendamento.
2. **Instanciação do Resultado Salvo no BD (`construir_grafo_da_grade_salva`):** Carrega os registros já processados da tabela `GRA_GRADE_HORARIA`, mapeando os vértices com seus respetivos horários (`HO_ID`) para validação e visualização em memória.

---

## 4. Como Executar e Validar Localmente

Certifique-se de ter as dependências instaladas e as variáveis de ambiente configuradas no arquivo `.env`.

Execute o script de teste do grafo:

```bash
python back-end/graphs/graph.py