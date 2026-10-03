-- Run as the superuser by `pnpm db:setup`. Repeatable: roles and the database are created
-- if absent, and the role passwords are brought in line with db.env every time.
-- The passwords arrive as environment variables of the psql process and are never printed.
\set ON_ERROR_STOP on
\getenv writer_password OAW_KG_WRITER_PASSWORD
\getenv site_password OAW_SITE_PASSWORD

SELECT format('CREATE ROLE oaw_kg_writer LOGIN PASSWORD %L', :'writer_password')
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'oaw_kg_writer') \gexec
SELECT format('CREATE ROLE oaw_site LOGIN PASSWORD %L', :'site_password')
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'oaw_site') \gexec
SELECT format('ALTER ROLE oaw_kg_writer NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'writer_password') \gexec
SELECT format('ALTER ROLE oaw_site NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'site_password') \gexec

SELECT 'CREATE DATABASE openaiwill OWNER oaw_kg_writer'
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'openaiwill') \gexec

REVOKE ALL ON DATABASE openaiwill FROM PUBLIC;
GRANT CONNECT ON DATABASE openaiwill TO oaw_site;

\connect openaiwill
REVOKE ALL ON SCHEMA public FROM PUBLIC;
