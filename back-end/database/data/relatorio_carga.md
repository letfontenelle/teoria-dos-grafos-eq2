# Relatório da carga de dados

Gerado por `database/data_ingestion/data_ingestion.py` a partir de `grade_professor_2026_2.csv` (GradeProfessor.pdf) e `perfil_cp21.csv` (perfil CP21).

## Totais carregados

| Tabela | Linhas |
|---|---|
| `PRO_PROFESSOR` | 26 |
| `DIS_DISCIPLINA` | 48 |
| `HOR_HORARIO` | 60 |
| `ALO_ALOCACAO` | 48 |
| `GRA_GRADE_HORARIA` | 181 |

Linhas lidas: 48 da oferta e 38 do CP21. Grade atual carregada no semestre `2026.2`.

## Linhas ignoradas (0)

Nenhuma linha ignorada: todas as linhas das fontes eram válidas.

## Horários ignorados (0)

Nenhum horário fora do padrão dia (2-6) + faixa (A-L).

## Disciplinas com horário modificado (7)

Carregadas com o horário atual, como pede a US-01.

| Código | Disciplina | Original | Atual (carregado) |
|---|---|---|---|
| CCMP0030 | PROJETO DE FINAL DE CURSO | 4I 4J 4K 4L | 5G 5H 5I 5J |
| CCMP0122 | PESQUISA OPERACIONAL | 4A 4B 5C 5D | 4A 4B 6A 6B |
| CCMP0039 | TEORIA DA COMPUTAÇÃO | 5C 5D 6E 6F | 5A 5B 5C 5D |
| CCMP0012 | GERENCIA DE PROJETO | 6C 6D 6E 6F | 6E 6F 6G 6H |
| CCMP0005 | BANCO DE DADOS | 2C 2D 5E 5F | 2C 2D 5C 5D |
| CCMP0132 | ENGENHARIA DE REQUISITOS | 2E 2F 5C 5D | 2E 2F 5E 5F |
| CCMP0081 | MODELAGEM ANALÍTICA | 4A 4B 5E 5F | 4A 4B 5C 5D |

## Divergências entre o CP21 e a oferta (5)

| Código | Disciplina | Campo | CP21 | Oferta 2026.2 | Decisão |
|---|---|---|---|---|---|
| CCMP0030 | PROJETO DE FINAL DE CURSO | período | 10 | 8 | mantido o período da oferta (é o que a coordenação usou na grade atual) |
| CCMP0030 | PROJETO DE FINAL DE CURSO | carga horária | 30h (2 faixas) | 4 faixas (60h) | mantida a carga do CP21; a grade gerada usa carga / 15 faixas |
| CCMP0173 | PROJETO EM ENGENHARIA DA COMPUTAÇÃO | período | 7 | 8 | mantido o período da oferta (é o que a coordenação usou na grade atual) |
| CCMP0006 | COMPILADORES | período | 8 | 6 | mantido o período da oferta (é o que a coordenação usou na grade atual) |
| CCMP0079 | INTERFACE HUMANO-COMPUTADOR | período | 6 | 8 | mantido o período da oferta (é o que a coordenação usou na grade atual) |

## Avisos

- Matrícula não informada nas fontes para os 26 professores (PRO_MATRICULA fica vazia).
- 10 eletivas (CCMP0078, CCMP0082, ADMT0002, ELET0025, CCMP0026, CCMP0012, CCMP0132, CCMP0081, CCMP0032, CCMP0023) não aparecem por código no CP21, que só reserva vagas "Eletiva 60h" no 9º e 10º períodos; receberam 60h.
