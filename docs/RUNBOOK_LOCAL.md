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
95 passed
```

El warning historico de pandas/pyarrow dejo de aparecer tras la actualizacion a `pandas==3.0.3`.

## 3. Levantar API local con uvicorn

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8080 --reload
```

La API queda disponible en:

```text
http://127.0.0.1:8080
```

En local, si `ENVIRONMENT` no es `production`, la documentacion FastAPI queda disponible en:

```text
http://127.0.0.1:8080/docs
http://127.0.0.1:8080/redoc
http://127.0.0.1:8080/openapi.json
```

En Cloud Run debe usarse `ENVIRONMENT=production`; con esa configuracion `/docs`, `/redoc` y `/openapi.json` quedan desactivados.

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

### Mini reporte extendido JSON

```powershell
curl -H "X-API-Key: change_me_local_only" "http://127.0.0.1:8080/mini-report/extended/json?current_year=2026&previous_year=2025&start_year=2025&end_year=2026"
```

### Mini reporte extendido Markdown

```powershell
curl -H "X-API-Key: change_me_local_only" "http://127.0.0.1:8080/mini-report/extended/markdown?current_year=2026&previous_year=2025&start_year=2025&end_year=2026"
```

Notas operativas:

- La API FastAPI no lee directamente del CSV.
- `/health` permanece publico.
- `/db/health`, `/mini-report/json`, `/mini-report/markdown` y endpoints extendidos requieren header `X-API-Key`.
- La variable `INFONAVIT_API_KEY` debe estar configurada en `.env`, PowerShell o variable segura del entorno.
- La variable opcional `INFLACION_COPILOT_URL` permite agregar inflacion comparable y crecimiento real al reporte extendido.
- `/mini-report/json`, `/mini-report/markdown` y endpoints extendidos requieren PostgreSQL/Supabase disponible.
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

## 10. Generar mini reporte extendido local desde Supabase

Este comando lee Supabase/PostgreSQL con `DATABASE_URL_READONLY`, carga monto y creditos, consulta inflacion si `INFLACION_COPILOT_URL` esta configurada, genera contexto analitico extendido y guarda salidas locales en `outputs/mini_report/`.

Para integrar inflacion comparable en local:

```powershell
$env:INFLACION_COPILOT_URL="https://inflacion-copilot-api-490229283844.us-central1.run.app"
```

Si la variable no existe o el servicio no responde, el reporte extendido se genera de todos modos con `inflation_context.available=false` y warning metodologico.

```powershell
@'
from dotenv import load_dotenv
import json
import os

load_dotenv()
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL_READONLY", "")

from database import engine
from data_access import load_long_metrics_from_db
from inflation_client import fetch_average_period_inflation
from report_metrics_extended import add_inflation_context, build_extended_context
from mini_report_extended import generate_extended_report

raw = load_long_metrics_from_db(engine, start_year=2025, end_year=2026)
context = build_extended_context(raw, current_year=2026, previous_year=2025)
period = context["period"]
inflation = fetch_average_period_inflation(
    current_year=period["current_year"],
    previous_year=period["previous_year"],
    month_limit=period["month_limit"],
)
context = add_inflation_context(context, inflation)
report_json, markdown = generate_extended_report(context, output_dir="outputs/mini_report")
json.dumps(report_json, ensure_ascii=False)

print("raw_shape=", raw.shape)
print("json_path=outputs/mini_report/mini_report_extended.json")
print("markdown_path=outputs/mini_report/mini_report_extended.md")
print("markdown_chars=", len(markdown))
print("creditos_actual=", report_json["summary"]["creditos_actual"])
print("ticket_promedio_actual=", report_json["summary"]["ticket_promedio_actual"])
print("inflation_available=", report_json["inflation_context"]["available"])
print("inflation_pct=", report_json["inflation_context"].get("inflation_pct"))
print("monto_variacion_real_pct=", report_json["inflation_context"].get("monto_variacion_real_pct"))
print("line_family_analysis_available=", report_json["line_family_analysis"]["available"])
for family in report_json["line_family_analysis"]["families"]:
    variations = family["variations"]
    print("family=", family["family"])
    print("  share_monto_actual_pct=", variations["share_monto_actual_pct"])
    print("  share_creditos_actual_pct=", variations["share_creditos_actual_pct"])
    print("  share_monto_delta_pp=", variations["share_monto_delta_pp"])
    print("  share_creditos_delta_pp=", variations["share_creditos_delta_pp"])
'@ | python -
```

Archivos esperados:

```text
outputs/mini_report/mini_report_extended.json
outputs/mini_report/mini_report_extended.md
```

Validacion esperada con datos 2025-2026 cargados:

```text
raw_shape= (10904, 7)
creditos_actual > 0
ticket_promedio_actual calculado
inflation_available=True si `INFLACION_COPILOT_URL` esta configurada y disponible
line_family_analysis_available=True
families_count=3
```

La formula de crecimiento real usada por el reporte extendido es:

```text
(((1 + nominal_pct / 100) / inflation_factor) - 1) * 100
```

El bloque `line_family_analysis` incluye solo tres familias funcionales:

- Adquisicion de vivienda nueva.
- Adquisicion de vivienda existente/usada.
- Mejoramiento.

Cada familia reporta monto, creditos, ticket promedio, variaciones nominales/reales, participacion en monto, participacion en creditos y cambios de participacion en puntos porcentuales. La participacion se calcula contra el total general del reporte extendido, no contra el subtotal de las tres familias.

## 11. Retencion / higiene operativa

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

## 12. Usuarios de base por minimo privilegio

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

## 13. Migracion PostgreSQL manual

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

## 14. Notas de seguridad

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
