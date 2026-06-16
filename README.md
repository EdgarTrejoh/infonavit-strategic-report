# Reporte Ejecutivo INFONAVIT 2026

Pipeline Python para consolidar informacion del Sistema de Informacion Infonavit (SII), generar datasets analiticos, producir visualizaciones ejecutivas, exportar un PDF, sincronizar opcionalmente el historico consolidado con PostgreSQL y exponer un mini reporte ejecutivo via API.

El proyecto esta orientado a ejecucion operativa local y a una API de solo lectura publicada en Cloud Run, con Supabase PostgreSQL como primer destino productivo administrado.

## Estado Actual

- Python recomendado: 3.11.
- Entorno validado con Python 3.11.9.
- PostgreSQL configurable y no bloqueante si `database.fail_on_error: false`.
- ETL con zonas de trabajo para no procesar directamente originales.
- Validacion formal de contrato de datos.
- Logging por corrida.
- Manifest JSON por corrida ETL.
- Suite minima de pruebas con pytest.
- PDF ejecutivo generado correctamente para 2026.
- API FastAPI publicada en Cloud Run y validada.
- Reporte extendido con inflacion comparable, familias de linea, efecto mezcla y lectura asistida por IA.
- Release GitHub actual: `v0.8`.
- Estado vigente de pruebas: `136 passed`.
- Diagnostico protegido de metricas DB disponible en local: `/diagnostics/db-metrics`.
- Pendiente operativo inmediato: desplegar nueva revision Cloud Run con diagnostico DB y lectura robusta de metricas UTF-8/mojibake.

## Estructura

```text
001_reporte_2026_gpt/
|-- datos_entrada/              # Archivos originales de entrada; contenido ignorado por Git
|-- datos_work/                 # Copias temporales de trabajo; contenido ignorado por Git
|-- datos_procesados/           # Copias opcionales de archivos procesados; contenido ignorado por Git
|-- datos_error/                # Copias de archivos rechazados o fallidos; contenido ignorado por Git
|-- logs/                       # Logs y manifests de corrida; contenido ignorado por Git
|   `-- runs/
|-- respaldo/                   # Respaldos locales; contenido ignorado por Git
|-- salidas_viz_final/          # PNGs y PDF generados; contenido ignorado por Git
|-- tests/                      # Pruebas unitarias y operativas minimas
|-- viz/                        # Visualizaciones
|-- config.yaml                 # Configuracion operativa
|-- config.py                   # Defaults y variables inyectadas desde YAML
|-- contract_validator.py       # Validador de contrato CSV/dataset
|-- database.py                 # Conexion y health check PostgreSQL
|-- etl.py                      # DataManager y transformaciones analiticas
|-- main.py                     # Orquestador principal
|-- migrate_csv_to_pg.py        # Sincronizacion incremental PostgreSQL
|-- sii_excel_etl.py            # Ingesta Excel SII y zonas operativas
|-- requirements.txt
`-- PLAN_TRABAJO_ESTABILIZACION.md
```

## Requisitos

- Python 3.11 recomendado.
- Windows PowerShell o terminal equivalente.
- PostgreSQL opcional.

No usar Python 3.14 como base operativa por ahora.

## Instalacion

Desde la raiz del proyecto:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si `py` no esta disponible:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Validacion basica:

```powershell
python -c "import pandas, numpy, matplotlib, yaml, sqlalchemy; print('imports ok')"
python -c "import yaml; print(yaml.safe_load(open('config.yaml', encoding='utf-8')).keys())"
```

## Variables de Entorno

Crea `.env` a partir de `.env.example`.

Ejemplo:

```text
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
DB_HOST=localhost
DB_PORT=5432
DB_NAME=infonavit
INFONAVIT_API_KEY=change_me_local_only
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
INFLACION_COPILOT_URL=https://inflacion-copilot-api-490229283844.us-central1.run.app
INFLACION_COPILOT_TIMEOUT_SECONDS=20
```

Tambien puedes usar:

```text
DATABASE_URL=postgresql+psycopg2://usuario:password@host:5432/base
```

`.env` y `.env.*` estan ignorados por Git. `.env.example` si debe versionarse.

## Configuracion Principal

Archivo: `config.yaml`.

### Tiempo

```yaml
tiempo:
  anio_analisis: 2026
  anio_objetivo: 2026
  anio_previo: 2025
  anio_historico_inicio: 2024
```

`anio_historico_inicio` controla series como la carrera acumulada y el rango de portada.

### Entrada y salida

```yaml
rutas:
  archivo_entrada: "datos_entrada"
  carpeta_salida: "salidas_viz_final"
  nombre_pdf_prefijo: "Reporte_Estrategico_INFONAVIT"
```

`archivo_entrada` puede apuntar a:

- carpeta con Excels SII;
- Excel individual `.xls` o `.xlsx`;
- CSV consolidado.

## ETL Operativo

Configuracion:

```yaml
etl:
  mover_procesados: false
  usar_zona_trabajo: true
  ruta_work: datos_work
  ruta_procesados: datos_procesados
  ruta_error: datos_error
```

Comportamiento:

- `datos_entrada/` contiene archivos originales.
- Los originales no se mueven ni se modifican por defecto.
- Si `usar_zona_trabajo: true`, cada Excel se copia a `datos_work/` y se procesa la copia.
- Si un archivo falla, se copia a `datos_error/` y se registra el motivo.
- Si un archivo procesa bien y `mover_procesados: true`, se copia a `datos_procesados/`.
- Si `mover_procesados: false`, no se copia a procesados.

El ETL genera manifests en:

```text
logs/runs/run_YYYYMMDD_HHMMSS.json
```

Campos principales:

```json
{
  "run_id": "...",
  "started_at": "...",
  "finished_at": "...",
  "files": [
    {
      "source_file": "...",
      "work_file": "...",
      "status": "ok | error | skipped",
      "message": "...",
      "error_type": "...",
      "destination": "..."
    }
  ]
}
```

## Contrato de Datos

El CSV consolidado debe incluir:

- `id_reporte`
- `anio`
- `estado`
- `mes`
- `linea`
- `producto`
- `metrica`
- `valor`
- `periodicidad`
- `fuente`
- `timestamp`

Validaciones principales:

- columnas obligatorias;
- `id_reporte` presente;
- duplicados de `id_reporte`;
- `anio` valido;
- `mes` entre 1 y 12;
- `valor` numerico;
- catalogo de estados;
- metricas reconocidas;
- advertencia por comparabilidad temporal parcial.

## PostgreSQL

Configuracion:

```yaml
database:
  enabled: true
  fail_on_error: false
  health_check: true
```

Comportamiento:

- `enabled: false`: genera reporte sin tocar PostgreSQL.
- `enabled: true` y `fail_on_error: false`: intenta sincronizar; si falla, continua con el PDF.
- `enabled: true` y `fail_on_error: true`: si PostgreSQL falla, detiene la ejecucion.

El migrador usa `id_reporte` para upsert incremental en `infonavit_historico`.

Uso seguro del migrador manual:

```powershell
python migrate_csv_to_pg.py --help
python migrate_csv_to_pg.py --run --yes --csv-path SII_concentrado_v3.csv
```

Por seguridad, `python migrate_csv_to_pg.py` y `python migrate_csv_to_pg.py --help` no ejecutan migraciones. La carga real requiere confirmacion explicita con `--run --yes`.

Validacion recomendada en PostgreSQL:

```sql
SELECT
    COUNT(*) AS filas_totales,
    COUNT(DISTINCT id_reporte) AS ids_unicos
FROM infonavit_historico;

SELECT id_reporte, COUNT(*)
FROM infonavit_historico
GROUP BY id_reporte
HAVING COUNT(*) > 1;
```

## Ejecucion del Reporte

```powershell
.\.venv\Scripts\activate
python main.py
```

Resultado esperado:

- CSV consolidado local si se procesan Excels.
- PNGs en `salidas_viz_final/`.
- PDF en `salidas_viz_final/Reporte_Estrategico_INFONAVIT_2026.pdf`.
- Log de corrida en `logs/reporte_YYYYMMDD_HHMMSS.log`.
- Manifest ETL en `logs/runs/`.

## Logging

Cada ejecucion crea:

```text
logs/reporte_YYYYMMDD_HHMMSS.log
```

El log registra:

- carga de configuracion;
- ETL;
- validaciones;
- health check PostgreSQL;
- migracion;
- generacion de PNGs;
- exportacion PDF;
- errores con stack trace cuando aplica.

## Retencion y Limpieza Operativa

La politica de retencion esta configurada en modo seguro por defecto:

```yaml
retention:
  enabled: false
  dry_run: true
  max_age_days:
    datos_work: 7
    datos_error: 30
    datos_procesados: 90
    logs: 30
    manifests: 90
```

Comportamiento:

- `enabled: false`: no limpia archivos.
- `dry_run: true`: reporta que limpiaria, pero no borra.
- Nunca elimina `.gitkeep`.
- No toca `datos_entrada/`, `.env`, `.venv/`, `SII_concentrado_v3.csv` ni `salidas_viz_final/`.

La limpieza se ejecuta al final de `main.py`, pero con la configuracion actual queda deshabilitada.

Ejecucion manual segura:

```powershell
python retention.py --dry-run
```

Para limpieza real se requiere confirmacion explicita:

```powershell
python retention.py --run --yes
```

## Pruebas

## Capa de acceso a datos para mini reporte IA

Supabase/PostgreSQL conserva la tabla cruda `infonavit_historico` en formato largo. El modulo `data_access.py` transforma esa tabla a un `df_master` compatible con el contrato analitico del proyecto.

Flujo previsto:

- `infonavit_historico`: tabla cruda sincronizada desde CSV.
- `data_access.py`: transforma tabla larga a `df_master`.
- `report_metrics.py`: calcula metricas ejecutivas reutilizables.
- La capa IA consume JSON estructurado, no la tabla cruda.

Las vistas SQL quedan como fase posterior, una vez validado el contrato del mini reporte.

Nota de compatibilidad: con `pandas==3.0.3`, `data_access.py` ejecuta la consulta mediante SQLAlchemy `text()` y bind parameters, y construye el DataFrame desde el resultado. Esto evita depender de `pd.read_sql_query()` para conexiones SQLAlchemy en el endpoint `/mini-report/json`, manteniendo SQL parametrizado y acceso read-only.

Contratos diferenciados:

- `contract_validator.py`: valida el contrato de ingesta CSV largo.
- `data_access.py`: valida el contrato `df_master` para API/mini reporte.
- `report_metrics.py`: consume `df_master` y produce metricas/`ai_context`.
- `mini_report.py`: consume `ai_context`/JSON estructurado y genera Markdown/JSON.

Validacion de solo lectura Supabase -> `data_access.py` -> `report_metrics.py` -> JSON IA:

- Fecha de validacion: 2026-06-10.
- Filas leidas: 5,452.
- Rango de fechas: 2025-01-01 a 2026-04-01.
- Contrato `df_master`: OK.
- JSON serializable: OK.
- Variacion YTD comparable: 15.93%.
- Advertencia metodologica esperada: comparacion YTD, no anios completos.

Riesgos pendientes:

- `estado` y `mes` estan como `DOUBLE PRECISION` en la tabla cruda.
- `nombre_estado` depende de `config.ESTADOS_MX`.
- Las vistas SQL analiticas quedan para fase posterior.

## Capa de metricas para mini reporte e IA

El modulo `report_metrics.py` define funciones puras y testeables para preparar metricas reutilizables en el mini reporte ejecutivo y en la capa de interpretacion asistida por IA.

Entrada esperada: `df_master` con columnas:

- `fecha`
- `linea`
- `producto`
- `nombre_estado`
- `Monto`

Salida disponible:

- metricas YTD;
- YoY comparable;
- mix linea/producto;
- Pareto lineas;
- ranking estatal;
- contrato JSON-ready para IA.

Aclaraciones:

- no llama OpenAI directamente;
- no genera PDF todavia;
- no modifica visualizaciones actuales;
- no depende de PostgreSQL;
- no depende de archivos reales.

## Mini reporte ejecutivo sin IA

El modulo `mini_report.py` toma el JSON estructurado de `report_metrics.py` y genera:

- Markdown ejecutivo;
- JSON de mini reporte.

Esta capa no integra OpenAI directamente, no genera PDF y no modifica visualizaciones actuales. Sirve para revisar texto estructurado y secciones del reporte antes o junto con la capa asistida por IA.

## Mini reporte ejecutivo extendido

Los modulos `report_metrics_extended.py` y `mini_report_extended.py` amplian el contexto analitico usando solo `infonavit_historico`.

Metricas usadas:

- `Monto de credito Infonavit`;
- `Numero de creditos formalizados`.

El reporte extendido calcula:

- monto colocado YTD comparable;
- numero de creditos formalizados YTD comparable;
- ticket promedio = monto / creditos;
- variaciones absolutas y porcentuales contra anio previo;
- inflacion promedio comparable si `INFLACION_COPILOT_URL` esta configurada;
- variacion real del monto colocado y del ticket promedio usando ajuste compuesto;
- rankings por estado, linea y producto;
- narrativa deterministica sin IA.

Integracion opcional de inflacion:

- Variable: `INFLACION_COPILOT_URL`.
- Variable opcional de timeout: `INFLACION_COPILOT_TIMEOUT_SECONDS=20`.
- Servicio esperado: `GET /inflation/average-period?current_year=YYYY&previous_year=YYYY&month_limit=N`.
- Formula de crecimiento real: `(((1 + nominal_pct / 100) / inflation_factor) - 1) * 100`.
- El crecimiento real no se calcula como variacion nominal menos inflacion. Se calcula mediante deflactacion compuesta usando el factor de inflacion comparable.
- `inflation_factor = promedio INPC periodo actual / promedio INPC periodo previo`.
- Para 2026 vs 2025 con corte a mes 4, el factor se calcula con: promedio INPC enero-abril 2026 / promedio INPC enero-abril 2025.
- Este criterio aplica porque el reporte compara agregados YTD, no observaciones puntuales.
- `INFLACION_COPILOT_TIMEOUT_SECONDS` controla el timeout de consulta al servicio de inflacion. Es util ante cold starts de Cloud Run. Si no existe, no es numerica o es menor o igual a cero, se usa `20`; el maximo permitido es `60`.
- Si el servicio no esta configurado o no responde, el reporte sigue funcionando y agrega warning metodologico. El cliente reintenta una vez ante `ReadTimeout`.

Para agregados anuales o YTD, el reporte usa inflacion promedio comparable, no inflacion punto a punto. La inflacion punto a punto sirve para equivalencias de poder adquisitivo entre dos fechas; la inflacion promedio comparable sirve para deflactar montos agregados de periodos.

### Analisis por familia de linea

El bloque `line_family_analysis` analiza solo tres familias funcionales:

- Adquisicion de vivienda nueva.
- Adquisicion de vivienda existente/usada.
- Mejoramiento.

Para cada familia calcula:

- monto actual y previo;
- creditos actuales y previos;
- ticket promedio actual y previo;
- variacion nominal de monto;
- variacion real de monto si hay inflacion disponible;
- variacion de creditos;
- variacion nominal y real del ticket;
- participacion en monto;
- participacion en creditos;
- cambio de participacion en puntos porcentuales.

Campos principales del JSON:

```text
line_family_analysis.available
line_family_analysis.families[].family
line_family_analysis.families[].current
line_family_analysis.families[].previous
line_family_analysis.families[].variations.monto_nominal_pct
line_family_analysis.families[].variations.monto_real_pct
line_family_analysis.families[].variations.creditos_pct
line_family_analysis.families[].variations.ticket_nominal_pct
line_family_analysis.families[].variations.ticket_real_pct
line_family_analysis.families[].variations.share_monto_actual_pct
line_family_analysis.families[].variations.share_monto_previo_pct
line_family_analysis.families[].variations.share_creditos_actual_pct
line_family_analysis.families[].variations.share_creditos_previo_pct
line_family_analysis.families[].variations.share_monto_delta_pp
line_family_analysis.families[].variations.share_creditos_delta_pp
line_family_analysis.families[].executive_reading
```

El analisis por familia permite identificar efecto mezcla. Por ejemplo, una familia puede ganar participacion en creditos y presionar a la baja el ticket promedio agregado si su ticket absoluto es menor al ticket promedio total, aun cuando su propio ticket crezca en terminos reales.

Cruces futuros pendientes, no integrados todavia:

- Indice SHF de Precios de la Vivienda;
- salario minimo;
- derechohabientes IMSS.

Estos cruces no deben interpretarse como ya integrados hasta que existan datos, validacion y contrato especifico. La inflacion INPC solo debe interpretarse como integrada cuando `inflation_context.available=true`.

Si falta la metrica `Numero de creditos formalizados` en el periodo consultado, el reporte extendido no rellena creditos ni ticket con ceros silenciosos: devuelve valores nulos y agrega warning metodologico. La metrica real en base conserva acentos (`Número de créditos formalizados`).

## API minima FastAPI

La carpeta `api/` expone una primera API local de solo lectura para el mini reporte ejecutivo.

Endpoints disponibles:

- `GET /health`: estado del servicio, sin tocar Supabase.
- `GET /db/health`: health check seguro de PostgreSQL/Supabase; requiere `X-API-Key`.
- `GET /mini-report/json`: genera mini reporte JSON en memoria; requiere `X-API-Key`.
- `GET /mini-report/markdown`: genera mini reporte Markdown como texto plano; requiere `X-API-Key`.
- `GET /mini-report/extended/json`: genera reporte ejecutivo extendido JSON; requiere `X-API-Key`.
- `GET /mini-report/extended/markdown`: genera reporte ejecutivo extendido Markdown; requiere `X-API-Key`.
- `GET /mini-report/ai/json`: genera interpretacion ejecutiva asistida por IA sobre el JSON extendido; requiere `X-API-Key`.
- `GET /mini-report/ai/markdown`: genera Markdown con interpretacion ejecutiva asistida por IA; requiere `X-API-Key`.

La API integra una capa IA opcional para interpretar el JSON extendido; no genera PDF, no ejecuta migraciones y no modifica datos. La API ya fue publicada y validada en Cloud Run.

Los endpoints extendidos pueden consultar el servicio externo configurado en `INFLACION_COPILOT_URL` para agregar `inflation_context`, inflacion promedio comparable y crecimiento real. Si la variable no existe o el servicio falla, devuelven el reporte nominal con warning controlado, sin interrumpir la respuesta.

### Analisis asistido por IA

La capa `ai_extended_report.py` consume el JSON extendido ya calculado y produce una interpretacion ejecutiva estructurada. La IA no calcula metricas, no consulta la base de datos, no llama servicios externos de datos y no modifica el reporte deterministico.

Variables:

- `OPENAI_API_KEY`: habilita la llamada opcional a OpenAI.
- `OPENAI_MODEL`: modelo opcional; default `gpt-4.1-mini`.

Si `OPENAI_API_KEY` no esta configurada, los endpoints IA responden con:

```json
{"available": false, "reason": "AI service not configured"}
```

Reglas operativas:

- No registrar prompts completos en logs.
- No enviar credenciales, headers, API keys, connection strings ni variables de entorno.
- No afirmar causalidad que no este sustentada por el JSON.
- Si un cruce no esta integrado, debe mantenerse como cruce pendiente.
- `recommended_next_crosses` solo debe incluir cruces pendientes declarados en `future_crosses`.
- La prueba local y la publicacion Cloud Run con IA fueron validadas exitosamente para la version `v0.8`.

Ejemplo local:

```powershell
$env:OPENAI_API_KEY="..."
$env:OPENAI_MODEL="gpt-4.1-mini"
Invoke-RestMethod `
  "http://127.0.0.1:8010/mini-report/ai/json?current_year=2026&previous_year=2025&month_limit=4" `
  -Headers @{ "X-API-Key" = "TU_API_KEY_LOCAL" }
```

Dependencia operativa de datos:

- La API FastAPI no lee directamente del CSV.
- `/mini-report/json`, `/mini-report/markdown` y endpoints extendidos requieren PostgreSQL/Supabase disponible.
- La tabla `infonavit_historico` debe existir y estar poblada.
- La API no ejecuta migraciones.
- Antes de levantar la API contra Supabase, validar `/db/health`, existencia de `infonavit_historico` y lectura mediante `data_access.py`.

Seguridad minima:

- `/health` permanece publico.
- `/db/health`, `/mini-report/json` y `/mini-report/markdown` requieren header `X-API-Key`.
- La key se configura con la variable `INFONAVIT_API_KEY`.
- En local puede definirse en `.env` o en la sesion de PowerShell.
- En Cloud Run debe configurarse con Secret Manager o variable segura.
- Nunca versionar, compartir ni registrar la API key.
- Swagger/OpenAPI (`/docs`, `/redoc`, `/openapi.json`) queda disponible en local.
- En Cloud Run debe configurarse `ENVIRONMENT=production` para desactivar `/docs`, `/redoc` y `/openapi.json`.

Ejemplo local sin valor real:

```powershell
$env:INFONAVIT_API_KEY="change_me_local_only"
curl -H "X-API-Key: change_me_local_only" "http://127.0.0.1:8080/mini-report/json?current_year=2026&previous_year=2025"
```

Credenciales de base por minimo privilegio:

- La API debe usar `DATABASE_URL` con un usuario PostgreSQL/Supabase de solo lectura.
- El usuario de API debe tener permisos `SELECT` sobre `public.infonavit_historico` y vistas analiticas futuras, si se crean.
- El migrador `migrate_csv_to_pg.py` debe usar una credencial admin/migration separada para cargas y upsert.
- Cloud Run debe recibir solo la credencial read-only de la API.
- La credencial admin/migration no debe configurarse en Cloud Run.
- No se crea tabla `app_users` todavia. Esa tabla queda para una fase posterior si se implementan login, clientes, permisos por usuario o auditoria funcional.
- Plantilla SQL sugerida: [docs/sql/create_api_readonly_user.sql](docs/sql/create_api_readonly_user.sql).

## Preparacion para Cloud Run

El proyecto incluye `Dockerfile` y `.dockerignore` para contenerizar la API FastAPI.

Comandos locales:

```powershell
docker build -t infonavit-strategic-report-api .
docker run --rm -p 8080:8080 infonavit-strategic-report-api
curl http://127.0.0.1:8080/health
```

Para probar con Supabase localmente, usar variables de entorno sin imprimir credenciales:

```powershell
docker run --rm -p 8080:8080 --env-file .env infonavit-strategic-report-api
```

El despliegue en Cloud Run debe realizarse de forma controlada. La configuracion productiva requiere variables de entorno y secretos seguros. Las variables sensibles deben configurarse mediante Secret Manager o variables seguras de Cloud Run, nunca en Git.

En Cloud Run configurar:

```text
ENVIRONMENT=production
```

Con esa variable se desactivan `/docs`, `/redoc` y `/openapi.json`. En local, si `ENVIRONMENT` no es `production`, la documentacion FastAPI permanece disponible para desarrollo.

Antes de nuevas actualizaciones productivas:

- configurar presupuesto y alertas en GCP;
- definir autenticacion;
- definir limites de instancia;
- configurar Secret Manager;
- construir y desplegar imagen;
- validar endpoint publico;
- monitorear costo y latencia.

## Preparacion Cloud Run y seguridad API

Se agrego el checklist [docs/CLOUD_RUN_DEPLOYMENT_CHECKLIST.md](docs/CLOUD_RUN_DEPLOYMENT_CHECKLIST.md) para despliegues y actualizaciones controladas.

- Cloud Run es el destino preferente de la API.
- La API sigue siendo solo lectura.
- La URL publicada se documenta en la seccion de validacion Cloud Run.
- Se documento checklist de despliegue con control de gasto.
- Se reviso prevencion basica de SQL injection.
- Se agregaron validaciones de parametros HTTP.
- Se agrego proteccion por header `X-API-Key` para endpoints operativos.
- Los secretos deben ir en Secret Manager o variables seguras de Cloud Run.

Pendientes:

- autenticacion formal si se expone a usuarios externos;
- presupuesto y alertas GCP;
- limites de instancia;
- monitoreo de latencia/costo.

## Validacion Cloud Run

URL publicada:

```text
https://infonavit-strategic-report-api-490229283844.us-west1.run.app
```

Validacion realizada el 2026-06-12:

- `/health` publico responde `200 OK`.
- `/db/health` sin `X-API-Key` responde `401`.
- `/mini-report/json` sin `X-API-Key` responde `401`.
- `/mini-report/markdown` sin `X-API-Key` responde `401`.
- `/db/health` con `X-API-Key` responde `200 OK` y `database=available`.
- `/mini-report/json` con `X-API-Key` responde `200 OK`, JSON serializable y 5 secciones esperadas.
- `/mini-report/markdown` con `X-API-Key` responde `200 OK` y contiene las 5 secciones del mini reporte.
- Todas las respuestas probadas incluyeron header `X-Request-ID`.

No se imprimio ni documento el valor real de `INFONAVIT_API_KEY`.

Validacion actualizada de `v0.8`:

- Prueba local con OpenAI: exitosa.
- Publicacion Cloud Run con OpenAI: validada y exitosa.
- Validacion local posterior: `136 passed`; `/diagnostics/db-metrics` confirma 10,904 filas para 2025-2026 y 5,452 filas por metrica de monto/creditos.
- La lectura local extendida recupera monto, creditos, ticket promedio, inflacion comparable y variaciones reales.
- Cloud Run debe actualizarse con una nueva revision para incorporar `/diagnostics/db-metrics` y la lectura robusta de metricas; antes del deploy el endpoint productivo puede seguir devolviendo ceros para colocacion INFONAVIT.
- Endpoints IA protegidos con `X-API-Key`:
  - `/mini-report/ai/json`
  - `/mini-report/ai/markdown`
- `OPENAI_API_KEY` y `OPENAI_MODEL` deben configurarse como secretos o variables seguras, nunca en Git.

## Observabilidad y seguridad operativa de la API

- La API genera un `request_id` por peticion y lo regresa en el header `X-Request-ID`.
- La API registra metodo HTTP, path, status code, duracion de la peticion y `request_id`.
- Los endpoints de mini reporte registran duraciones internas aproximadas: carga desde DB, calculo de metricas, render de mini reporte y total.
- Los endpoints de mini reporte siguen siendo de solo lectura.
- `/diagnostics/db-metrics` es un endpoint protegido de solo lectura para diagnosticar conteos por anio/metrica sin exponer filas de negocio ni secretos.
- Los parametros HTTP se validan antes de ejecutar consultas.
- No se permite SQL libre desde la API.
- No se registran credenciales, `DATABASE_URL`, `DB_PASSWORD` ni connection strings.
- Cloud Run debe mantener secretos seguros, presupuesto/alertas, limites de instancia y control de acceso revisados en cada actualizacion.

Ejecutar:

```powershell
.\.venv\Scripts\activate
python -m pytest -q
```

Cobertura minima actual:

- contrato de columnas obligatorias;
- `id_reporte` no nulo;
- duplicados de `id_reporte`;
- rango de `mes`;
- anios configurados;
- advertencia por ventanas temporales parciales;
- ETL operativo con Excel invalido;
- manifest y zona de error;
- CSV en carpeta marcado como `skipped`.
- smoke test de grafica principal con salida PNG temporal.
- politica de retencion en modo deshabilitado, dry-run y limpieza real controlada.

Resultado esperado actual:

```text
La suite completa debe pasar con `python -m pytest -q`. En la ultima validacion local del bloque de diagnostico DB se obtuvo `136 passed`.
```

El warning historico de pandas/pyarrow dejo de aparecer tras la actualizacion a `pandas==3.0.3`.

`pytest.ini` filtra warnings deprecados internos de matplotlib/pyparsing para mantener la salida de pruebas legible.

## CI GitHub Actions

El repositorio incluye `.github/workflows/ci.yml` para validar automaticamente:

- `python -m pytest -q` con Python 3.11;
- `docker build -t infonavit-strategic-report-api .`.

El CI corre en `push` a `main` y en `pull_request` hacia `main`. No usa `.env`, no usa secrets, no se conecta a Supabase real, no ejecuta migraciones, no publica imagen Docker y no despliega Cloud Run. El deploy queda como fase manual/controlada posterior.

## Politica de Git

El repositorio debe versionar:

- codigo;
- configuracion sin secretos;
- documentacion;
- tests;
- estructuras vacias con `.gitkeep`;
- muestras controladas futuras en `data_samples/`.

No debe versionar:

- `.env`;
- `.venv/`;
- CSVs productivos;
- Excels;
- PNGs;
- PDFs;
- logs;
- manifests;
- zonas operativas con datos;
- respaldos reales.

## Seguridad y mantenimiento

- Dependabot queda configurado para revisar dependencias `pip` semanalmente.
- `requirements.txt` se mantiene anclado para reproducibilidad; las actualizaciones deben entrar por PR y con pruebas.
- `database.py` evita devolver mensajes crudos de conexion PostgreSQL para no exponer credenciales.
- Los aliases simples de estados usados por el ETL se configuran en `config.yaml` bajo `estado_aliases`, con fallback interno para compatibilidad.
- `pip-audit` queda como evaluacion posterior; no se agrega todavia al flujo de CI.

## Publicacion Productiva

Decision tecnica de destino inicial de datos:

- Desarrollo local: PostgreSQL local.
- Primer despliegue productivo: Supabase PostgreSQL.
- Futuro enterprise/GCP: Cloud SQL o BigQuery.

Motivo:

- mantiene compatibilidad PostgreSQL;
- el proyecto ya soporta `DATABASE_URL`;
- reduce complejidad operativa frente a Cloud SQL para una primera version;
- es suficiente para el primer mini reporte interpretativo;
- permite centralizar datos para la capa IA.

Criterio para IA:

- la IA no consume datos crudos directamente;
- la IA consume JSON estructurado generado por `report_metrics_extended.py` y `mini_report_extended.py`;
- la IA no calcula metricas, no ejecuta SQL y no modifica datos.

Estado validado en Supabase:

- `health_check` exitoso.
- Tabla remota `infonavit_historico` disponible.
- Conteo validado:
  - `filas_totales`: 109430
  - `ids_unicos`: 109430
  - `grupos_duplicados`: 0
- El migrador manual esta protegido: requiere `--run --yes` para ejecutar cambios.

Pendientes recomendados posteriores a `v0.8`:

- definir vistas/tablas analiticas para mini reporte;
- ampliar fixture de Excel valido para multiples meses/productos si se requiere mayor cobertura;
- automatizacion/operacion productiva de la politica de retencion;
- monitoreo de latencia/costo Cloud Run;
- presupuesto y alertas GCP;
- politica de backups/restore Supabase;
- autenticacion formal si la API se expone a usuarios externos.

## Autor y Fuente

Autor: Edgar Trejo (@etrejoh)

El presente fue elaborado con datos del Sistema de Informacion Infonavit (SII) publicados en el portal www.portalmx.infonavit.org.mx.
