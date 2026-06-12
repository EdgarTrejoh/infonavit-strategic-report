-- Template para crear un usuario PostgreSQL/Supabase de solo lectura para la API.
-- Reemplazar CHANGE_ME_STRONG_PASSWORD por una contrasena segura.
-- No guardar contrasenas reales en Git, README, issues, tickets ni logs.
-- Ejecutar con un usuario administrador/controlado, no desde la API.

BEGIN;

CREATE ROLE api_readonly
    LOGIN
    PASSWORD 'CHANGE_ME_STRONG_PASSWORD';

GRANT CONNECT ON DATABASE infonavit TO api_readonly;
GRANT USAGE ON SCHEMA public TO api_readonly;

GRANT SELECT ON TABLE public.infonavit_historico TO api_readonly;

-- Opcional: permitir lectura sobre vistas analiticas futuras.
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO api_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO api_readonly;

-- Defensa explicita: el usuario de API no debe escribir.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON TABLE public.infonavit_historico
FROM api_readonly;

COMMIT;

-- Validacion sugerida con la URL/usuario api_readonly:
-- SELECT COUNT(*) FROM public.infonavit_historico;
--
-- Validacion destructiva segura: ejecutar en transaccion y hacer ROLLBACK.
-- Deben fallar por permisos:
--
-- BEGIN;
-- INSERT INTO public.infonavit_historico (id_reporte) VALUES ('permission-test');
-- ROLLBACK;
--
-- BEGIN;
-- UPDATE public.infonavit_historico SET fuente = fuente WHERE false;
-- ROLLBACK;
--
-- BEGIN;
-- DELETE FROM public.infonavit_historico WHERE false;
-- ROLLBACK;
