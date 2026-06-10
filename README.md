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
22 passed, 1 warning
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

La base esta preparada para evolucionar hacia:

- Cloud Run u otro servicio de ejecucion;
- Supabase/PostgreSQL administrado;
- runner web o frontend para usuarios;
- CI con pruebas automatizadas;
- almacenamiento externo de insumos y salidas.

Antes de productivo, pendientes recomendados:

- ampliar fixture de Excel valido para multiples meses/productos si se requiere mayor cobertura;
- prueba opcional de integracion PostgreSQL;
- automatizacion/operacion productiva de la politica de retencion;
- README de `datos_entrada/` con convencion de nombres de archivos.

## Autor y Fuente

Autor: Edgar Trejo (@etrejoh)

El presente fue elaborado con datos del Sistema de Informacion Infonavit (SII) publicados en el portal www.portalmx.infonavit.org.mx.
