# Reporte Ejecutivo INFONAVIT 2026

Pipeline Python para consolidar informacion del Sistema de Informacion Infonavit (SII), generar datasets analiticos, producir visualizaciones ejecutivas, exportar un PDF y sincronizar opcionalmente el historico consolidado con PostgreSQL.

El proyecto esta orientado a ejecucion operativa local y deja lista la base para despliegues posteriores en servicios como Cloud Run, Supabase u otra infraestructura administrada.

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

## Pruebas

## Capa de acceso a datos para mini reporte IA

Supabase/PostgreSQL conserva la tabla cruda `infonavit_historico` en formato largo. El modulo `data_access.py` transforma esa tabla a un `df_master` compatible con el contrato analitico del proyecto.

Flujo previsto:

- `infonavit_historico`: tabla cruda sincronizada desde CSV.
- `data_access.py`: transforma tabla larga a `df_master`.
- `report_metrics.py`: calcula metricas ejecutivas reutilizables.
- IA futura: consumira JSON estructurado, no la tabla cruda.

Las vistas SQL quedan como fase posterior, una vez validado el contrato del mini reporte.

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

El modulo `report_metrics.py` define funciones puras y testeables para preparar metricas reutilizables en un futuro mini reporte ejecutivo con insights asistidos por IA.

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

- no integra OpenAI todavia;
- no genera PDF todavia;
- no modifica visualizaciones actuales;
- no depende de PostgreSQL;
- no depende de archivos reales.

## Mini reporte ejecutivo sin IA

El modulo `mini_report.py` toma el JSON estructurado de `report_metrics.py` y genera:

- Markdown ejecutivo;
- JSON de mini reporte.

Esta capa no integra OpenAI todavia, no genera PDF y no modifica visualizaciones actuales. Sirve como paso previo para revisar texto estructurado y secciones del reporte antes de automatizar insights con IA.

## API minima FastAPI

La carpeta `api/` expone una primera API local de solo lectura para el mini reporte ejecutivo.

Endpoints disponibles:

- `GET /health`: estado del servicio, sin tocar Supabase.
- `GET /db/health`: health check seguro de PostgreSQL/Supabase.
- `GET /mini-report/json`: genera mini reporte JSON en memoria.
- `GET /mini-report/markdown`: genera mini reporte Markdown como texto plano.

La API no integra OpenAI todavia, no genera PDF, no ejecuta migraciones y no modifica datos. Es una base futura para publicar en Cloud Run, que se mantiene como destino preferente para la API por escalado a cero y control de gasto.

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

No se ha desplegado todavia en Google Cloud. Cloud Run queda como destino preferente futuro por escalado a cero y control de gasto. Las variables sensibles deben configurarse mediante Secret Manager o variables seguras de Cloud Run, nunca en Git.

Antes de desplegar:

- configurar presupuesto y alertas en GCP;
- definir autenticacion;
- definir limites de instancia;
- configurar Secret Manager;
- construir y desplegar imagen;
- validar endpoint publico;
- monitorear costo y latencia.

## Preparacion Cloud Run y seguridad API

Se agrego el checklist [docs/CLOUD_RUN_DEPLOYMENT_CHECKLIST.md](docs/CLOUD_RUN_DEPLOYMENT_CHECKLIST.md) para despliegue futuro.

- Cloud Run sera el destino preferente futuro de la API.
- La API sigue siendo solo lectura.
- No se desplego todavia.
- Se documento checklist de despliegue con control de gasto.
- Se reviso prevencion basica de SQL injection.
- Se agregaron validaciones de parametros HTTP.
- Los secretos deben ir en Secret Manager o variables seguras de Cloud Run.

Pendientes:

- autenticacion/API key;
- deploy real Docker/Cloud Run;
- presupuesto y alertas GCP;
- limites de instancia;
- monitoreo de latencia/costo.

## Observabilidad y seguridad operativa de la API

- La API genera un `request_id` por peticion y lo regresa en el header `X-Request-ID`.
- La API registra metodo HTTP, path, status code, duracion de la peticion y `request_id`.
- Los endpoints de mini reporte registran duraciones internas aproximadas: carga desde DB, calculo de metricas, render de mini reporte y total.
- Los endpoints de mini reporte siguen siendo de solo lectura.
- Los parametros HTTP se validan antes de ejecutar consultas.
- No se permite SQL libre desde la API.
- No se registran credenciales, `DATABASE_URL`, `DB_PASSWORD` ni connection strings.
- Cloud Run requiere configuracion posterior de Secret Manager, presupuesto, limites de instancia y control de acceso.

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
54 passed, 1 warning
```

El warning conocido proviene de `pandas==2.2.0` al importar pandas. Indica que `pyarrow` sera una dependencia requerida en pandas 3.0. No bloquea la ejecucion ni invalida las pruebas. Por ahora no se agrega `pyarrow` a `requirements.txt` para evitar una dependencia pesada que el proyecto todavia no usa directamente.

`pytest.ini` filtra warnings deprecados internos de matplotlib/pyparsing para mantener la salida de pruebas legible. El warning de pandas/pyarrow se conserva visible por decision operativa.

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
- permite centralizar datos para una futura capa IA.

Criterio para IA:

- la IA no consumira datos crudos directamente;
- la IA consumira JSON estructurado generado por `report_metrics.py` o vistas/tablas analiticas.

Estado validado en Supabase:

- `health_check` exitoso.
- Tabla remota `infonavit_historico` disponible.
- Conteo validado:
  - `filas_totales`: 109430
  - `ids_unicos`: 109430
  - `grupos_duplicados`: 0
- El migrador manual esta protegido: requiere `--run --yes` para ejecutar cambios.

Antes de productivo, pendientes recomendados:

- definir vistas/tablas analiticas para mini reporte;
- ampliar fixture de Excel valido para multiples meses/productos si se requiere mayor cobertura;
- prueba opcional de integracion PostgreSQL;
- automatizacion/operacion productiva de la politica de retencion;
- README de `datos_entrada/` con convencion de nombres de archivos.

## Autor y Fuente

Autor: Edgar Trejo (@etrejoh)

El presente fue elaborado con datos del Sistema de Informacion Infonavit (SII) publicados en el portal www.portalmx.infonavit.org.mx.
