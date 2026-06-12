# Runbook Local - Proyecto INFONAVIT

Este runbook documenta comandos operativos para validar el proyecto en entorno local. Ejecutar los comandos desde la raiz del repositorio.

## 1. Activar entorno

```powershell
.\.venv\Scripts\activate
```

## 2. Ejecutar tests

```powershell
python -m pytest -q
```

Resultado esperado actual:

```text
66 passed, 1 warning
```

El warning conocido de pandas/pyarrow no bloquea.

## 3. Levantar API local con uvicorn

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8080 --reload
```

La API queda disponible en:

```text
http://127.0.0.1:8080
```

Para detenerla, usar `Ctrl+C`.

## 4. Probar endpoints con curl

### Health de servicio

```powershell
curl http://127.0.0.1:8080/health
```

Respuesta esperada:

```json
{"status":"ok","service":"infonavit-strategic-report-api"}
```

### Health de base de datos

```powershell
$env:INFONAVIT_API_KEY="change_me_local_only"
curl -H "X-API-Key: change_me_local_only" http://127.0.0.1:8080/db/health
```

Si `DATABASE_URL` esta disponible y la base responde:

```json
{"status":"ok","database":"available"}
```

Si no hay credenciales o la base no responde, debe fallar de forma controlada:

```json
{"status":"error","database":"unavailable","message":"No se pudo conectar a PostgreSQL. Verifica host, puerto, base y credenciales."}
```

### Mini reporte JSON

```powershell
curl -H "X-API-Key: change_me_local_only" "http://127.0.0.1:8080/mini-report/json?current_year=2026&previous_year=2025&start_year=2025&end_year=2026"
```

### Mini reporte Markdown

```powershell
curl -H "X-API-Key: change_me_local_only" "http://127.0.0.1:8080/mini-report/markdown?current_year=2026&previous_year=2025&start_year=2025&end_year=2026"
```

Notas operativas:

- La API FastAPI no lee directamente del CSV.
- `/health` permanece publico.
- `/db/health`, `/mini-report/json` y `/mini-report/markdown` requieren header `X-API-Key`.
- La variable `INFONAVIT_API_KEY` debe estar configurada en `.env`, PowerShell o variable segura del entorno.
- `/mini-report/json` y `/mini-report/markdown` requieren PostgreSQL/Supabase disponible.
- La tabla `infonavit_historico` debe existir y estar poblada.
- La API no ejecuta migraciones.
- Antes de usar la API contra Supabase, validar `/db/health`, existencia de `infonavit_historico` y lectura mediante `data_access.py`.
- La API debe usar `DATABASE_URL` con usuario read-only.
- El migrador debe usar una credencial admin/migration separada.
- Cloud Run debe recibir solo la credencial read-only; la credencial admin no debe configurarse en Cloud Run.

## 5. Construir imagen Docker

```powershell
docker build -t infonavit-strategic-report-api .
```

## 6. Ejecutar contenedor sin `.env`

```powershell
docker run --rm --name infonavit-api-local -p 8080:8080 infonavit-strategic-report-api
```

En otro PowerShell:

```powershell
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/db/health
```

Sin `.env`, `/health` debe responder OK y `/db/health` debe fallar controladamente porque falta `INFONAVIT_API_KEY`, sin exponer credenciales.

## 7. Ejecutar contenedor con `.env`

```powershell
docker run --rm --name infonavit-api-local -p 8080:8080 --env-file .env infonavit-strategic-report-api
```

En otro PowerShell:

```powershell
curl http://127.0.0.1:8080/health
curl -H "X-API-Key: change_me_local_only" http://127.0.0.1:8080/db/health
curl -H "X-API-Key: change_me_local_only" "http://127.0.0.1:8080/mini-report/json?current_year=2026&previous_year=2025&start_year=2025&end_year=2026"
curl -H "X-API-Key: change_me_local_only" "http://127.0.0.1:8080/mini-report/markdown?current_year=2026&previous_year=2025&start_year=2025&end_year=2026"
```

## 8. Detener contenedor

Si el contenedor se ejecuto con `--rm`, detenerlo con:

```powershell
docker stop infonavit-api-local
```

Si queda un contenedor detenido con el mismo nombre:

```powershell
docker rm -f infonavit-api-local
```

## 9. Generar mini reporte local desde Supabase

Este comando lee Supabase/PostgreSQL, construye `df_master`, genera contexto analitico y guarda salidas locales en `outputs/mini_report/`.

```powershell
@'
import json
from database import engine
from data_access import load_df_master_from_db, validate_df_master_contract
from report_metrics import build_ai_context
from mini_report import generate_mini_report

df_master = load_df_master_from_db(engine, start_year=2025, end_year=2026)
validate_df_master_contract(df_master)

ai_context = build_ai_context(df_master, current_year=2026, previous_year=2025)
report_json, markdown = generate_mini_report(ai_context, output_dir="outputs/mini_report")
json.dumps(report_json, ensure_ascii=False)

print("filas_leidas=", len(df_master))
print("fecha_min=", df_master["fecha"].min().date())
print("fecha_max=", df_master["fecha"].max().date())
print("json_serializable=ok")
print("markdown_generado=ok")
'@ | python -
```

Archivos esperados:

```text
outputs/mini_report/mini_report.json
outputs/mini_report/mini_report.md
```

## 10. Retencion / higiene operativa

Dry-run seguro, sin borrar archivos:

```powershell
python retention.py --dry-run
```

Limpieza real, con confirmacion explicita:

```powershell
python retention.py --run --yes
```

La retencion solo opera sobre:

- `datos_work/`
- `datos_error/`
- `datos_procesados/`
- `logs/`
- `logs/runs/`

No toca `datos_entrada/`, `SII_concentrado_v3.csv`, `.env`, `.venv/` ni salidas finales.

## 11. Usuarios de base por minimo privilegio

Plantilla SQL sugerida:

```text
docs/sql/create_api_readonly_user.sql
```

Politica:

- La API FastAPI usa `DATABASE_URL` con usuario read-only.
- El migrador `migrate_csv_to_pg.py` usa credencial admin/migration separada.
- Cloud Run solo debe recibir la credencial read-only.
- La credencial admin/migration no debe configurarse en Cloud Run.
- No crear tabla `app_users` todavia; queda para una fase posterior con login, clientes, permisos por usuario o auditoria funcional.

Validaciones manuales sugeridas con el usuario read-only:

```sql
SELECT COUNT(*) FROM public.infonavit_historico;
```

Las siguientes operaciones deben fallar por permisos. Ejecutarlas solo dentro de una transaccion y terminar con `ROLLBACK`:

```sql
BEGIN;
INSERT INTO public.infonavit_historico (id_reporte) VALUES ('permission-test');
ROLLBACK;

BEGIN;
UPDATE public.infonavit_historico SET fuente = fuente WHERE false;
ROLLBACK;

BEGIN;
DELETE FROM public.infonavit_historico WHERE false;
ROLLBACK;
```

## 12. Migracion PostgreSQL manual

El migrador esta protegido contra ejecucion accidental.

No usar:

```powershell
python migrate_csv_to_pg.py
```

Para ver ayuda:

```powershell
python migrate_csv_to_pg.py --help
```

Para ejecutar una migracion real, usar confirmacion explicita:

```powershell
python migrate_csv_to_pg.py --run --yes --csv-path SII_concentrado_v3.csv
```

## 13. Notas de seguridad

- No compartir `.env`.
- No versionar `.env`.
- No imprimir `DATABASE_URL`.
- No imprimir ni compartir `INFONAVIT_API_KEY`.
- No imprimir usuario, password, host completo ni connection string.
- No ejecutar migraciones por accidente.
- Confirmar que `DATABASE_URL` apunta al ambiente correcto antes de cualquier operacion.
- Confirmar que `DATABASE_URL` de API usa usuario read-only.
- No usar credenciales admin/migration en Cloud Run.
- Usar Secret Manager o variables seguras de Cloud Run en despliegues futuros.
- No subir CSV, Excel, PDF, PNG, logs ni artefactos generados al repositorio.
