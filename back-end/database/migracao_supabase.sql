-- Migração do Supabase para o modelo corrigido (siglas de 3 letras).
--
-- Rodar UMA vez no SQL Editor do Supabase, depois de reativar o projeto.
-- Apaga as tabelas antigas (DI_DISCIPLINA, HO_HORARIO e as que dependiam
-- delas) e recria tudo com schema.sql. Os dados voltam com a carga:
--     python -m database.data_ingestion.data_ingestion --banco supabase
--
-- Atenção: os dados das tabelas antigas são perdidos. Eles vinham da
-- planilha manual e são substituídos pela carga a partir do GradeProfessor.pdf
-- e do perfil CP21.

DROP TABLE IF EXISTS "GRA_GRADE_HORARIA" CASCADE;
DROP TABLE IF EXISTS "ALO_ALOCACAO" CASCADE;
DROP TABLE IF EXISTS "HO_HORARIO" CASCADE;
DROP TABLE IF EXISTS "DI_DISCIPLINA" CASCADE;
DROP TABLE IF EXISTS "HOR_HORARIO" CASCADE;
DROP TABLE IF EXISTS "DIS_DISCIPLINA" CASCADE;
DROP TABLE IF EXISTS "PRO_PROFESSOR" CASCADE;

-- Em seguida, cole aqui o conteúdo de schema.sql e execute.
