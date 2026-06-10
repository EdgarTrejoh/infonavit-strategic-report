# Plan de Trabajo - Estabilizacion del Proyecto INFONAVIT

## 1. Objetivo

Crear una ruta de trabajo clara, priorizada y ejecutable para estabilizar el proyecto INFONAVIT antes de realizar refactors mayores.

El proyecto es un pipeline Python para generar un reporte ejecutivo que integra carga de configuracion, ETL, generacion de datasets analiticos, visualizaciones, exportacion a PDF y sincronizacion relacionada con PostgreSQL.

Este documento busca:

- Registrar hallazgos relevantes.
- Priorizar acciones de estabilizacion.
- Definir entregables y criterios de aceptacion.
- Permitir retomar el trabajo en el futuro sin perder contexto.
- Separar trabajo inmediato de backlog tecnico.

Alcance original de este plan:

- No reorganizar toda la estructura del proyecto.
- No eliminar archivos sin confirmacion.

Nota de estado: este documento ya no es solo un plan inicial; tambien funciona como bitacora de estabilizacion. Varias acciones ya fueron implementadas, validadas y confirmadas en commits.

## 2. Diagnostico resumido

Hallazgos principales detectados:

- El entorno Python no se pudo ejecutar correctamente.
- `python` no esta disponible en `PATH`.
- `.venv\Scripts\python.exe` respondio "Acceso denegado".
- El README indica Python 3.9+, pero el entorno local parece usar Python 3.14.2.
- `requirements.txt` contiene dependencias duplicadas o inconsistentes.
- Existe riesgo de acoplamiento entre generacion de PDF y PostgreSQL.
- Antes de modificar `main.py`, debe confirmarse el acoplamiento real revisando llamadas a `migrate_csv_to_pg.py`, SQLAlchemy, psycopg2, funciones de sincronizacion, upsert o subprocess.
- En la revision inicial se observo que `main.py` importa y llama `migrate`, por lo que PostgreSQL parece participar en el flujo principal. Aun asi, cualquier ajuste debe partir de una confirmacion puntual.
- El ETL puede mover archivos fuente despues de procesarlos.
- Hay manejo parcial de errores con `print`, `return False`, `except Exception` amplio o `except: pass`.
- La validacion del contrato CSV es limitada.
- La migracion a PostgreSQL requiere `id_reporte`.
- Hay posible codificacion danada en documentacion.
- Inicialmente no se observaban pruebas automatizadas minimas; actualmente existe suite base con `pytest`.
- Existe un CSV consolidado grande en la raiz del proyecto.
- La estructura es funcional, pero requiere mayor control operativo.

## 3. Principios de trabajo

- Primero estabilidad, luego elegancia.
- No hacer refactor amplio sin necesidad.
- No modificar visualizaciones ni logica analitica salvo que sea indispensable.
- No mover insumos originales por defecto.
- Todo cambio debe ser reversible o trazable.
- PostgreSQL no debe bloquear la generacion del reporte si asi se configura.
- Confirmar hallazgos antes de modificar codigo.
- Priorizar cambios pequenos, verificables y documentados.
- Mantener compatibilidad con la estructura actual mientras se estabiliza.

## Diagnostico de entorno de ejecucion

### Hallazgos historicos iniciales

- `python` no esta en `PATH`.
- `py` no esta en `PATH`.
- `.venv` apunta a Python 3.14.2.
- `.venv\Scripts\python.exe` falla con "Acceso denegado".
- Python bundled de Codex es 3.12.13, pero no tiene dependencias instaladas.
- Las pruebas no llegaron a ejecutar ETL, visualizaciones ni PostgreSQL.

Estos hallazgos se conservan como historial del primer intento de ejecucion. No deben leerse como el estado vigente del proyecto despues de la reconstruccion/validacion posterior del entorno.

### Clasificacion

**Problemas del proyecto**

- `requirements.txt` tenia dependencias duplicadas o inconsistentes.
- `requirements.txt` no declaraba de forma explicita todas las dependencias directas observadas, por ejemplo `seaborn`.
- Estos problemas de dependencias fueron atendidos en el Bloque 1 mediante la limpieza de `requirements.txt`.

**Problemas del entorno**

- `python` no estaba disponible en `PATH` durante el primer diagnostico.
- `py` no estaba disponible en `PATH` durante el primer diagnostico.
- El Python bundled de Codex 3.12.13 no tiene instaladas las dependencias del proyecto.
- El entorno virtual inicial fue creado con Python 3.14.2, version no recomendada como base operativa por ahora.
- Estado posterior: existe un entorno virtual ejecutable con Python 3.11.9. Por lo tanto, los hallazgos de `python`/`py` fuera de `PATH` quedan como historicos y no como bloqueo vigente del pipeline.

**Problemas de permisos**

- En el primer diagnostico, `.venv\Scripts\python.exe` fallo con "Acceso denegado".
- En el primer diagnostico, `.venv\Scripts\pip.exe` tambien quedo inutilizable porque dependia del Python bloqueado dentro de `.venv`.
- Estado posterior: `.venv` pudo ejecutarse con Python 3.11.9 usando permisos elevados en Codex.

**Problemas de dependencias**

- Las pruebas con Python bundled se detuvieron por modulos faltantes como `PyYAML` y `matplotlib`.
- La carga de `config.yaml` no pudo validarse porque `yaml` no esta disponible en ese Python.
- `main.py` no pudo iniciar por falta de `yaml` en Python bundled y por permisos en `.venv`.
- Ejecucion posterior con `.venv` Python 3.11.9 y `PYTHONUTF8=1` completo el pipeline correctamente.
- El PDF generado fue revisado por el usuario y confirmado como correcto.

### Conclusion

El primer diagnostico no permitia considerar el proyecto validado ni fallido porque la ejecucion se detuvo antes de correr la logica real del pipeline.

Ese estado ya fue superado: con el entorno virtual Python 3.11.9, `main.py` completo ejecucion, sincronizo PostgreSQL, genero visualizaciones y produjo el PDF esperado. El usuario confirmo que el PDF generado es correcto.

El pendiente operativo original de salida Unicode en consola Windows fue corregido en los mensajes operativos detectados. La ejecucion ya fue validada sin `PYTHONUTF8=1`.

### Acciones historicas recomendadas para entorno local Windows

Ejecutar manualmente desde PowerShell en la raiz del proyecto:

```powershell
where python
where py
python --version
py --version
```

Si Python no existe, instalar Python 3.11 o Python 3.12 desde fuente oficial o Microsoft Store. La version preferente para este proyecto es Python 3.11.

Eliminar el entorno virtual danado solo despues de confirmar que no contiene archivos relevantes:

```powershell
rmdir /s /q .venv
```

Crear nuevo entorno con Python 3.11:

```powershell
py -3.11 -m venv .venv
```

Si `py` no existe:

```powershell
python -m venv .venv
```

Activar entorno:

```powershell
.\.venv\Scripts\activate
```

Actualizar pip:

```powershell
python -m pip install --upgrade pip
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Validar imports base:

```powershell
python -c "import pandas, numpy, matplotlib, yaml, sqlalchemy; print('imports ok')"
```

Validar carga de config:

```powershell
python -c "import yaml; print(yaml.safe_load(open('config.yaml', encoding='utf-8')).keys())"
```

Ejecutar:

```powershell
python main.py
```

### Restricciones historicas de ese diagnostico

- No modificar `main.py`.
- No tocar PostgreSQL.
- No mover datos.
- No avanzar al Bloque 2.
- No asumir que el pipeline falla hasta tener un entorno Python funcional.

## Estado actual comprobado

- Python 3.11.9 instalado y usado por `.venv`.
- Entorno virtual reconstruido o validado posteriormente con Python 3.11.9.
- Dependencias instaladas.
- Imports base validados.
- Imports del proyecto validados.
- `config.yaml` validado.
- ETL ejecutado.
- PostgreSQL sincronizado.
- 41 PNG generados.
- PDF generado: `Reporte_Estrategico_INFONAVIT_2026.pdf`.
- PDF revisado visualmente por el usuario y confirmado como correcto.
- Etapa 2 validada con PDF generado sin `PYTHONUTF8=1`.
- Modo DB no bloqueante validado: con PostgreSQL no disponible y `fail_on_error: false`, el PDF se genero.
- Pendiente operativo original de salida Unicode en consola Windows corregido en mensajes operativos detectados.
- README operativo actualizado y corregido en ASCII/UTF-8.
- `.gitignore` profesional aplicado; datos productivos, salidas, logs, manifests y entornos locales quedan fuera del versionamiento.
- `SII_concentrado_v3.csv`, `viz.py.bak` y `salidas_viz_final/.gitkeep` fueron retirados del indice de Git sin borrar archivos locales.
- Tests minimos agregados y validados: `14 passed, 1 warning`.
- Politica de retencion/limpieza operativa agregada en modo seguro:
  - `retention.enabled: false`;
  - `retention.dry_run: true`;
  - no borra nada por defecto;
  - excluye `.gitkeep`;
  - no toca `datos_entrada/`, `.env`, `.venv/`, CSV consolidado ni salidas finales.
- Commits recientes:
  - `5f19fa1 chore: stabilize ETL pipeline and reporting workflow`
  - `afb8b6b test: add validator and ETL operational coverage`
  - `ab8bd1e chore: remove obsolete project state document`
  - `3b727ac docs: update operational README`

## 4. Etapas priorizadas

Las etapas 1 a 4 forman el primer bloque de trabajo y deben atenderse antes de iniciar refactors grandes. Las etapas 5 a 8 quedan como siguientes fases o backlog tecnico controlado.

### Etapa 1 - Estabilizacion de entorno y dependencias

**Objetivo**

Garantizar que el proyecto pueda instalarse y ejecutarse desde un entorno Python limpio y reproducible.

**Hallazgos relacionados**

- `python` no esta disponible en `PATH`.
- `.venv\Scripts\python.exe` respondio "Acceso denegado".
- README indica Python 3.9+, pero el entorno local parece usar Python 3.14.2.
- `requirements.txt` contiene duplicados como `pandas>=2.0` y `pandas==2.2.0`, `openpyxl>=3.1` y `openpyxl==3.1.2`.
- Debe confirmarse que `.venv` este en `.gitignore`.

**Acciones propuestas**

- Definir version objetivo recomendada: Python 3.11 o Python 3.12.
- No usar Python 3.14 como base operativa por ahora.
- Reconstruir `.venv` si esta danado o bloqueado.
- Validar comandos basicos:
  - `python --version`
  - `python -m pip --version`
  - `python -m pip install -r requirements.txt`
  - `python -c "import pandas, matplotlib, sqlalchemy"`
- Limpiar `requirements.txt` eliminando duplicados y versiones contradictorias.
- Crear o actualizar `.env.example`.
- Confirmar que `.venv` este excluido en `.gitignore`.

**Entregables**

- Version objetivo de Python definida.
- `.venv` validado o reconstruido.
- `requirements.txt` limpio.
- `.env.example` revisado.
- `.gitignore` validado.
- Registro de comandos de verificacion.

**Criterios de aceptacion**

- El proyecto puede activar un entorno virtual limpio.
- Las dependencias se instalan sin conflictos.
- Los imports base funcionan.
- La version Python usada coincide con la version definida.
- La ejecucion base puede probarse sin errores de entorno.

**Riesgos**

- Falta de permisos locales para ejecutar `.venv`.
- Incompatibilidades entre versiones recientes de Python y paquetes cientificos.
- Dependencias transitivas no fijadas.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado

**Avance registrado - Bloque 1**

- Version detectada inicialmente en `.venv`: Python 3.14.2, segun `.venv\pyvenv.cfg`.
- Version recomendada para operacion: Python 3.11 como preferente; Python 3.12 como alternativa valida.
- No se recomienda usar Python 3.14 como base operativa por ahora.
- Hallazgo inicial: `python` no estaba disponible en `PATH` dentro del primer diagnostico.
- Hallazgo inicial: `py` no estaba disponible en `PATH` dentro del primer diagnostico.
- Hallazgo inicial: `.venv\Scripts\python.exe` no pudo ejecutarse: "Acceso denegado".
- Hallazgo inicial: `.venv\Scripts\pip.exe` no pudo ejecutarse porque dependia del Python bloqueado.
- `requirements.txt` fue limpiado para eliminar duplicados e inconsistencias.
- `.env.example` fue actualizado sin credenciales reales.
- `.gitignore` fue validado y contiene `.venv/`.
- Pruebas con Python bundled de Codex 3.12.13 fallaron por dependencias no instaladas, por ejemplo `PyYAML` y `matplotlib`.
- `main.py` no alcanzo ETL ni PostgreSQL; fallo al importar `yaml` usando el Python bundled y fallo por "Acceso denegado" usando `.venv`.
- Posteriormente, `.venv` fue ejecutable con permisos elevados y reporto Python 3.11.9.
- Imports base y del proyecto fueron exitosos.
- `config.yaml` fue validado.
- ETL fue ejecutado.
- PostgreSQL fue sincronizado.
- Se generaron 41 PNG.
- `main.py` completo fue exitoso al ejecutar con `PYTHONUTF8=1`.
- El usuario confirmo que el PDF generado es correcto.

### Etapa 2 - Separacion entre generacion de reporte y PostgreSQL

**Objetivo**

Evitar que una falla de PostgreSQL bloquee la generacion del PDF cuando el proyecto este configurado para operar sin base de datos.

Definicion productiva acordada: PostgreSQL es importante para la persistencia historica, pero no debe bloquear el flujo principal de generacion del reporte salvo que se configure explicitamente `fail_on_error: true`.

**Hallazgos relacionados**

- Existe riesgo de acoplamiento entre generacion de PDF y PostgreSQL.
- `main.py` debe revisarse antes de cualquier ajuste para confirmar si llama directamente a:
  - `migrate_csv_to_pg.py`
  - SQLAlchemy
  - psycopg2
  - alguna funcion de sincronizacion o upsert
  - subprocess para ejecutar migracion
- En la revision inicial se observo una llamada a `migrate`, por lo que parece existir acoplamiento operativo.
- Para publicacion productiva, el pipeline debe quedar preparado para conectarse a PostgreSQL administrado, por ejemplo Supabase o Cloud SQL, sin credenciales en codigo.
- Para ejecucion como servicio, por ejemplo Google Cloud Run, la generacion del PDF debe poder completarse aunque la base no este disponible si `fail_on_error: false`.

**Acciones propuestas**

- Confirmar el acoplamiento real antes de modificar `main.py`.
- Si no hay llamada real a PostgreSQL, no modificar logica; documentar que la migracion se ejecuta por separado.
- Si si hay acoplamiento, proponer configuracion en `config.yaml`:

```yaml
database:
  enabled: true
  fail_on_error: false
  health_check: true
```

- Definir comportamiento esperado:
  - `enabled: false`: genera reporte sin tocar PostgreSQL.
  - `enabled: true` y `fail_on_error: false`: intenta migrar, pero si falla continua con el PDF.
  - `enabled: true` y `fail_on_error: true`: si falla PostgreSQL, detiene ejecucion.
- Agregar bloque `database` en `config.yaml`.
- Ajustar `main.py` para leer y aplicar la politica `database.enabled`, `database.fail_on_error` y `database.health_check`.
- Agregar health check de PostgreSQL sin exponer contrasena.
- Hacer que fallas de DB no bloqueen la generacion del PDF cuando `fail_on_error: false`.
- Documentar modo reporte sin DB.
- Actualizar README o este plan con modo local/productivo.
- Mantener compatibilidad con variables actuales:
  - `DB_HOST`
  - `DB_PORT`
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
- Dejar preparado soporte futuro para `DATABASE_URL`, util en Supabase, Cloud SQL, Cloud Run u otros servicios administrados.
- Documentar destino futuro opcional de artefactos:
  - PDF local en `salidas_viz_final/`;
  - almacenamiento administrado futuro, por ejemplo Google Cloud Storage.

**Entregables**

- Diagnostico confirmado de acoplamiento.
- Propuesta de configuracion `database.enabled`.
- Propuesta de configuracion `database.fail_on_error`.
- Propuesta de configuracion `database.health_check`.
- Definicion de health check.
- Flujo esperado documentado.
- Politica local/productiva documentada.
- Cables preparados para ambiente productivo con PostgreSQL administrado.

**Criterios de aceptacion**

- Queda claro si PostgreSQL es obligatorio u opcional.
- El modo sin DB esta documentado.
- La falla de PostgreSQL tiene comportamiento controlado.
- No se exponen credenciales en logs.
- Con `database.enabled: false`, el reporte no intenta conectarse a PostgreSQL.
- Con `database.enabled: true` y `database.fail_on_error: false`, una falla de PostgreSQL queda registrada y el PDF se genera.
- Con `database.enabled: true` y `database.fail_on_error: true`, una falla de PostgreSQL detiene el proceso.
- El health check informa disponibilidad de DB sin mostrar contrasena.
- La configuracion es compatible con ejecucion local y con despliegue futuro en Supabase, Cloud SQL o Google Cloud Run.

**Riesgos**

- Cambiar el flujo puede ocultar fallas reales de sincronizacion si no se registra correctamente.
- Si el reporte depende de datos actualizados en DB, debe aclararse el origen de verdad.
- En productivo, si `fail_on_error: false`, puede generarse un PDF correcto sin que la tabla historica quede sincronizada; debe quedar visible en logs.
- Servicios administrados pueden requerir SSL, cadena `DATABASE_URL` o reglas de red adicionales.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado

**Avance registrado - Etapa 2**

- Se agrego bloque `database` en `config.yaml` con:
  - `enabled: true`
  - `fail_on_error: false`
  - `health_check: true`
- `main.py` lee la politica `database.enabled`, `database.fail_on_error` y `database.health_check`.
- Se agrego health check sencillo de PostgreSQL.
- Se agrego soporte para `DATABASE_URL` como cable futuro para Supabase, Cloud SQL, Cloud Run u otros servicios administrados.
- Se retiro salida Unicode de mensajes operativos que bloqueaban consola Windows.
- Prueba con PostgreSQL disponible:
  - health check OK;
  - migracion OK;
  - PDF generado correctamente sin `PYTHONUTF8`.
- Prueba con PostgreSQL no disponible:
  - health check fallo;
  - se registro error;
  - con `fail_on_error: false`, el proceso continuo;
  - PDF generado correctamente.

### Etapa 3 - Proteccion del ETL e insumos

**Objetivo**

Evitar perdida, movimiento no deseado o procesamiento silenciosamente incorrecto de archivos fuente.

**Hallazgos relacionados**

- El ETL puede mover archivos fuente despues de procesarlos.
- Hay errores silenciosos en operaciones de movimiento.
- El formato Excel tiene supuestos rigidos.
- Si el anio no se detecta, existe riesgo de asignar `0` silenciosamente.
- Falta una alerta explicita cuando `archivo_entrada` apunta a una carpeta que no contiene archivos `.xls` o `.xlsx` procesables.
- Falta aclarar al usuario que un `.csv` dentro de `datos_entrada/` no se procesa automaticamente si la entrada configurada es una carpeta.

**Acciones propuestas**

- No mover archivos fuente originales por defecto.
- Preferir copia de trabajo.
- Proponer estructura operativa:

```text
datos_entrada/
datos_work/
datos_procesados/
datos_error/
```

- Hacer configurable cualquier movimiento de archivos.
- El pipeline puede copiar, registrar y archivar, pero no debe desaparecer insumos originales salvo instruccion explicita.
- Eliminar `except: pass`.
- Registrar errores de movimiento o lectura con logging.
- Validar estructura del Excel antes de procesar:
  - nombre de archivo
  - anio detectado
  - filas de encabezado
  - meses validos
  - metricas reconocidas
  - columnas minimas
- Generar alerta explicita si `archivo_entrada` es carpeta y no contiene archivos `.xls` o `.xlsx`.
- Aclarar en la alerta que, si se desea usar un CSV directo, `archivo_entrada` debe apuntar a la ruta exacta del CSV.
- Si el anio no se detecta, fallar temprano o permitir fallback configurable, pero no asignar `0` silenciosamente.

**Entregables**

- Politica documentada de manejo de insumos.
- Propuesta de carpetas de trabajo.
- Lista de validaciones previas de Excel.
- Identificacion de movimientos de archivo a controlar.
- Registro de errores silenciosos a corregir.
- Alerta definida para carpeta sin archivos `.xls` o `.xlsx`.
- Mensaje definido para distinguir carpeta de Excels vs CSV directo.

**Criterios de aceptacion**

- Los insumos originales no se alteran sin configuracion explicita.
- Los archivos problematicos se registran y pueden enviarse a `datos_error`.
- Un Excel invalido falla con mensaje claro.
- No hay movimientos silenciosos sin log.
- Si la carpeta de entrada no contiene `.xls` o `.xlsx`, el usuario recibe una alerta clara antes de continuar.
- Si existe un CSV en la carpeta pero la configuracion espera Excels, el usuario recibe una indicacion accionable.

**Riesgos**

- Aumentar trazabilidad puede requerir ajustes en rutas actuales.
- Cambiar politica de movimiento puede generar acumulacion de archivos si no se define limpieza.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado

**Avance registrado - Etapa 3**

- Se agrego bloque `etl` en `config.yaml` con `mover_procesados: false`.
- Se agrego default `ETL_MOVER_PROCESADOS = False` en `config.py`.
- `main.py` carga la politica `etl.mover_procesados`.
- El ETL de carpeta pasa `mover_procesados` a la consolidacion.
- Si `archivo_entrada` apunta a carpeta y no hay `.xls` o `.xlsx`, se registra alerta clara.
- Si existen `.csv` dentro de la carpeta, se registra alerta indicando que no se procesan automaticamente como entrada de carpeta y que debe configurarse la ruta exacta del CSV.
- Los archivos fuente originales ya no se mueven por defecto.
- El movimiento a `datos_procesados` solo ocurre si `etl.mover_procesados: true`.
- Se elimino el `except: pass` del movimiento de archivos.
- Los errores de lectura/procesamiento/movimiento se registran con `logging.exception`.
- Si un Excel no cumple el patron `SII_YYYY`, el proceso falla temprano con mensaje claro.
- Se agrego validacion minima de estructura Excel antes de procesar columnas.
- Validacion ejecutada:
  - carpeta sin `.xls/.xlsx` genero alerta;
  - `etl.mover_procesados` cargo como `False`;
  - archivo sin anio en nombre genero `ValueError` claro;
  - `main.py` completo genero PDF correctamente.

### Etapa 4 - Validacion formal del contrato de datos

**Objetivo**

Crear un validador reutilizable para asegurar que el CSV consolidado o dataset base cumple el contrato requerido antes del ETL analitico y antes de la migracion PostgreSQL.

**Hallazgos relacionados**

- La validacion CSV actual es limitada.
- La migracion a PostgreSQL requiere `id_reporte`.
- El ETL analitico requiere columnas minimas y catalogos consistentes.
- Falta validar que los anios definidos en `config.yaml` existan realmente en el dataset cargado.
- La ausencia de datos para `anio_analisis` puede provocar errores tardios en visualizaciones, por ejemplo `no numeric data to plot`.
- Algunas graficas de comparacion anual pueden estar comparando anios completos contra anios parciales, por ejemplo 12 meses de 2025 contra 4 meses de 2026.
- Las graficas identificadas para analisis temprano de comparabilidad temporal son:
  - `22_reporte_ejecutivo.png`
  - `24_yoy_por_linea.png`
  - `40_cagr_productos.png`

**Acciones propuestas**

- Crear una seccion tecnica para un validador formal.
- Modulo sugerido:
  - `etl/validators.py`
  - o `core/contract_validator.py`
- Validaciones minimas:
  - columnas obligatorias
  - `id_reporte` existe
  - `id_reporte` no nulo
  - `id_reporte` unico
  - `anio` valido
  - anios definidos en `config.yaml` existen en el dataset cargado
  - `mes` entre 1 y 12
  - `valor` numerico
  - `estado` reconocido
  - metrica reconocida
  - producto y linea validos si aplica
  - nulos relevantes
  - duplicados criticos
  - consistencia de catalogo de estados
- Reutilizar el mismo validador antes del ETL analitico y antes de la migracion PostgreSQL.
- Definir si el validador debe fallar, advertir o generar reporte segun severidad.
- Generar alerta temprana si `anio_analisis`, `anio_objetivo` o `anio_previo` no existen en los datos disponibles.
- Para visualizaciones que dependen de un anio especifico, detener con mensaje claro antes de llegar a errores genericos de pandas.
- Agregar validacion de comparabilidad temporal:
  - detectar meses disponibles por anio;
  - identificar el ultimo mes disponible del anio de analisis;
  - para comparaciones YoY, usar ventanas equivalentes, por ejemplo enero-abril 2026 contra enero-abril 2025;
  - distinguir entre acumulado observado, anio completo, proyeccion y CAGR;
  - alertar si una grafica intenta comparar 12 meses contra un anio parcial.
- Definir criterio base recomendado: usar YTD comparable como regla inicial para graficas de desempeno.
- Documentar el criterio temporal en titulos, subtitulos o notas de fuente cuando aplique.

**Entregables**

- Especificacion del contrato CSV.
- Lista de validaciones.
- Propuesta de modulo reutilizable.
- Criterios de severidad para errores y advertencias.
- Alerta definida para anios de `config.yaml` inexistentes en el dataset.
- Criterio documentado de comparabilidad temporal YTD.
- Inventario inicial de graficas que requieren revision por ventanas temporales.

**Criterios de aceptacion**

- El contrato de datos queda documentado.
- Las validaciones son reutilizables.
- Los errores criticos impiden migracion o reporte segun configuracion.
- Los duplicados y nulos relevantes se detectan antes del procesamiento.
- La ausencia de datos para el anio de analisis se detecta antes de generar graficas.
- El usuario recibe una recomendacion clara: ajustar `config.yaml` o cargar/consolidar datos del anio requerido.
- Las comparaciones anuales usan ventanas equivalentes o declaran explicitamente que son proyecciones/anios completos.
- Las graficas `22_reporte_ejecutivo.png`, `24_yoy_por_linea.png` y `40_cagr_productos.png` tienen criterio temporal revisado antes de ajustarse.

**Riesgos**

- Validaciones demasiado estrictas pueden bloquear datos historicos existentes.
- Catalogos incompletos pueden generar falsos positivos.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado

**Avance registrado - Etapa 4**

- Se agrego modulo reutilizable `contract_validator.py`.
- El validador revisa contrato base del CSV/dataset:
  - columnas obligatorias;
  - `id_reporte` existente y no vacio;
  - duplicados por `id_reporte`;
  - `anio` valido;
  - `mes` entre 1 y 12;
  - `valor` numerico;
  - estado reconocido;
  - metrica reconocida;
  - `linea`, `producto` y `metrica` no vacios.
- El ETL analitico valida el CSV consolidado antes de construir `df_master`.
- La migracion PostgreSQL reutiliza el validador antes del upsert.
- Se agrego validacion de anios configurados en `config.yaml` contra anios disponibles en el dataset.
- Se agrego alerta de comparabilidad temporal:
  - detecta si `anio_analisis` tiene menos meses que `anio_previo`;
  - recomienda ventana YTD comparable para graficas YoY.
- Las graficas identificadas para ajuste futuro siguen documentadas:
  - `22_reporte_ejecutivo.png`;
  - `24_yoy_por_linea.png`;
  - `40_cagr_productos.png`.
- Validaciones ejecutadas:
  - sintaxis OK;
  - ETL OK;
  - `main.py` completo OK;
  - PDF 2026 generado correctamente;
  - validador detecto anio configurado inexistente en prueba controlada;
  - validador emitio advertencia por ventana temporal parcial 2026 vs 2025.
- Avance posterior en graficas comparativas:
  - `22_reporte_ejecutivo.png` ya usa ventana YTD comparable automatica;
  - titulo corregido de "Ejecutido" a "Ejecutivo";
  - se agrego nota de comparacion YTD comparable;
  - `24_yoy_por_linea.png` ya usa ventana YTD comparable automatica;
  - en `24_yoy_por_linea.png` se ajusto el eje y la posicion de etiquetas para valores positivos y negativos;
  - `40_cagr_productos.png` ya usa ventana YTD comparable automatica;
  - en `40_cagr_productos.png`, `periodo=3` se interpreta como tres anios calendario de historial, por lo que el rango dinamico correcto es 2024-2026;
  - en `40_cagr_productos.png` el CAGR se calcula entre 2024 y 2026 usando meses comparables Ene-Abr para cada anio del periodo;
  - se ajusto el titulo dinamico y la nota de comparacion YTD comparable.
  - `41_matriz_cagr_estados.png` ya usa el mismo criterio de CAGR YTD comparable;
  - en `41_matriz_cagr_estados.png`, `periodo=3` se interpreta como tres anios calendario de historial, el rango dinamico es 2024-2026 y el monto actual se muestra como YTD;
  - se ajusto el titulo dinamico, el eje Y y la nota de comparacion YTD comparable.
  - `09_carrera_acumulada.png` ya usa el rango configurado en `anio_historico_inicio`, por lo que muestra 2024, 2025 y 2026 cuando `anio_historico_inicio` es 2024 y `anio_objetivo` es 2026.
- Ajuste visual PDF:
  - las graficas se insertan en el PDF sobre pagina carta horizontal fija;
  - se agrego escala configurable `pdf.figure_scale`;
  - el valor operativo actual es `0.84` para dejar margenes visibles y evitar graficas pegadas a los bordes;
  - los PNG individuales conservan su resolucion original.
- Ajuste de portada PDF:
  - el rango de portada usa `anio_historico_inicio` y `anio_objetivo`;
  - se agrego autor: Edgar Trejo (@etrejoh);
  - se agrego leyenda de fuente con datos del Sistema de Informacion Infonavit (SII) publicados en `www.portalmx.infonavit.org.mx`.

### Etapa 5 - Logging y manejo de errores basico

**Objetivo**

Mejorar la trazabilidad operativa sin alterar la logica analitica.

**Hallazgos relacionados**

- Hay uso de `print` para mensajes operativos.
- Existen retornos `False` como senal de error sin contexto estructurado.
- Hay `except Exception` amplio y posibles `except: pass`.
- El uso de simbolos Unicode o emojis en mensajes de consola puede fallar en Windows con codificacion `cp1252`.

**Acciones propuestas**

- Estandarizar `logging`.
- Reducir `print` operativos.
- Crear logs por ejecucion:

```text
logs/reporte_YYYYMMDD_HHMMSS.log
```

- Usar:
  - `logger.info`
  - `logger.warning`
  - `logger.error`
  - `logger.exception`
- Quitar simbolos Unicode y emojis de mensajes operativos; usar texto ASCII para evitar errores de encoding en Windows.
- Separar errores de:
  - archivo
  - CSV
  - datos invalidos
  - esquema
  - base de datos
- Mantener salida clara para usuario operativo.

**Entregables**

- Convencion de logging.
- Propuesta de archivo de log por corrida.
- Inventario de `print` operativos a sustituir.
- Clasificacion basica de errores.
- Mensajes operativos sin emojis ni simbolos Unicode.

**Criterios de aceptacion**

- Cada ejecucion deja trazabilidad.
- Los errores criticos muestran causa raiz.
- Las credenciales no aparecen en logs.
- Las advertencias no detienen el flujo salvo que sean criticas.
- La ejecucion en consola Windows no falla por imprimir simbolos Unicode.

**Riesgos**

- Exceso de logging puede dificultar lectura si no se clasifica bien.
- Cambiar demasiados puntos a la vez puede introducir ruido.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado

**Avance ejecutado**

- Se centralizo la configuracion de logging en `main.py`.
- Cada corrida crea un archivo `logs/reporte_YYYYMMDD_HHMMSS.log`.
- Se reemplazaron `print` operativos por `logger.info`, `logger.warning`, `logger.error` o `logger.exception`.
- La migracion PostgreSQL registra lectura CSV, validaciones, duplicados, upsert y consultas recomendadas.
- La generacion de PNG/PDF registra cada grafica creada y agregada al reporte.
- Se valido con `main.py` completo.
- Evidencia: `logs/reporte_20260609_142057.log`.

### Mini-etapa - ETL operativo con zonas de trabajo

**Objetivo**

Agregar manejo minimo y seguro de archivos de entrada para no procesar directamente originales, registrar archivos exitosos o fallidos y preparar el flujo para operacion productiva.

**Implementado**

- Configuracion en `config.yaml`:
  - `etl.usar_zona_trabajo`;
  - `etl.ruta_work`;
  - `etl.ruta_procesados`;
  - `etl.ruta_error`.
- Defaults equivalentes en `config.py`.
- Creacion automatica de carpetas:
  - `datos_work/`;
  - `datos_procesados/`;
  - `datos_error/`;
  - `logs/runs/`.
- Cuando se procesa un Excel y `usar_zona_trabajo: true`, se crea una copia en `datos_work/` y se procesa la copia.
- Los originales en `datos_entrada/` no se mueven ni se modifican por defecto.
- Si el procesamiento termina bien:
  - se registra estado `ok` en manifest;
  - si `mover_procesados: true`, se copia el archivo original a `datos_procesados/`;
  - si `mover_procesados: false`, no se copia a procesados.
- Si el procesamiento falla:
  - se registra `logging.exception`;
  - se copia el archivo de trabajo u original a `datos_error/`;
  - se registra `status: error`, `message` y `error_type` en manifest;
  - no se agrega ningun bloque parcial al CSV consolidado.
- Se genera manifest JSON por corrida en:

```text
logs/runs/run_YYYYMMDD_HHMMSS.json
```

**Validaciones realizadas**

- Sintaxis validada con `py_compile`.
- `main.py` ejecutado completo.
- ETL sin archivos Excel en `datos_entrada/` mantiene compatibilidad.
- PostgreSQL sincronizo correctamente.
- Visualizaciones y PDF se generaron correctamente.
- Manifest generado: `logs/runs/run_20260609_153835.json`.
- Validacion manual con Excel real nuevo completada:
  - archivo: `datos_entrada/SII_2013.xlsx`;
  - manifest: `logs/runs/run_20260609_173357.json`;
  - resultado: `status: ok`;
  - se creo copia de trabajo en `datos_work/`;
  - el archivo original permanecio en `datos_entrada/`;
  - `destination: null` correcto con `etl.mover_procesados: false`.
- Validacion automatizada con Excel sintetico valido completada:
  - test: `test_valid_excel_uses_work_zone_and_manifest_ok`;
  - crea un `.xlsx` minimo en `tmp_path`;
  - valida copia a `datos_work/`;
  - valida manifest con `status: ok`;
  - valida que no haya copia a `datos_procesados/` cuando `mover_procesados: false`;
  - valida que no haya archivo en `datos_error/`.

**Pendientes**

- Validar comportamiento `error` con fixture controlado de Excel invalido.
- Evaluar si los manifests JSON deben ignorarse en Git junto con logs operativos.
- Pendiente opcional: ampliar el fixture sintetico para cubrir multiples meses/productos.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado parcialmente

### Etapa 6 - Limpieza controlada de estructura y documentacion

**Objetivo**

Ordenar artefactos y documentacion sin realizar una reorganizacion amplia.

**Hallazgos relacionados**

- Existia un CSV consolidado grande versionado en la raiz.
- Habia codificacion danada/mojibake en README.
- Existia `viz.py.bak` versionado.

**Acciones propuestas**

- Retirar CSV consolidado grande del versionamiento sin borrar el archivo local.
- Mantener el CSV consolidado como artefacto local ignorado por Git mientras no se implemente una nueva ruta controlada.
- Revisar `viz.py.bak` y definir si se elimina, se archiva o se ignora.
- Corregir README y documentacion danada en UTF-8/ASCII.
- No hacer reorganizacion amplia todavia.

**Entregables**

- Politica de versionamiento para CSV consolidado.
- Decision documentada sobre `viz.py.bak`.
- README corregido en UTF-8/ASCII.
- Estructura actualizada en documentacion.

**Criterios de aceptacion**

- No se rompe ninguna ruta del pipeline.
- La documentacion se lee correctamente.
- Los datos generados tienen ubicacion definida.
- No se eliminan archivos sin confirmacion.

**Riesgos**

- Mover datos antes de controlar rutas puede romper ejecucion.
- Corregir codificacion sin revisar literales usados por codigo puede cambiar comparaciones.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado

**Avance ejecutado**

- README actualizado con instrucciones operativas vigentes.
- README corregido para eliminar mojibake y documentar el estado actual del pipeline.
- `.gitignore` actualizado con politica profesional para:
  - secretos;
  - entornos locales;
  - datos productivos;
  - logs;
  - manifests;
  - zonas ETL;
  - salidas PNG/PDF;
  - respaldos locales.
- Se crearon `.gitkeep` para conservar estructura vacia:
  - `logs/.gitkeep`;
  - `logs/runs/.gitkeep`;
  - `datos_work/.gitkeep`;
  - `datos_error/.gitkeep`;
  - `datos_procesados/.gitkeep`.
- Se retiro del versionamiento sin borrar archivos locales:
  - `SII_concentrado_v3.csv`;
  - `viz.py.bak`;
  - `salidas_viz_final/.gitkeep`.
- Se elimino `docs/project_state.md` por no ser relevante para el proyecto.
- Se valido que `git status --short -uall` quedara limpio despues de los commits correspondientes.

**Pendientes**

- Definir si se requiere README especifico dentro de `datos_entrada/` con convencion de nombres de archivos.
- Definir politica de retencion para logs/manifests y zonas ETL en operacion productiva.

### Etapa 7 - Pruebas automatizadas minimas

**Objetivo**

Agregar una suite minima que permita detectar fallas basicas en contrato de datos, ETL y visualizaciones principales.

**Hallazgos relacionados**

- Inicialmente no se observaban pruebas automatizadas.
- El ETL y la migracion dependen de supuestos de datos.
- Las visualizaciones pueden romperse por cambios en columnas o tipos.
- Las graficas comparativas pueden producir conclusiones incorrectas si comparan anios completos contra anios parciales.

**Acciones propuestas**

- Proponer suite minima con `pytest`.
- Tests iniciales:
  - `test_required_columns`
  - `test_id_reporte_not_null`
  - `test_id_reporte_unique`
  - `test_mes_range`
  - `test_years_config_exist_in_dataset`
  - `test_yoy_uses_comparable_month_window`
  - `test_datamanager_builds_basic_dataset`
  - smoke test de una grafica principal
  - prueba opcional de integracion PostgreSQL
- Separar pruebas unitarias de pruebas de integracion.
- Usar datasets pequenos controlados.

**Entregables**

- Estructura propuesta de pruebas.
- Lista de pruebas minimas.
- Dataset fixture pequeno.
- Separacion entre unitarias e integracion.

**Criterios de aceptacion**

- Las pruebas unitarias corren sin PostgreSQL.
- La prueba de integracion PostgreSQL es opcional.
- Una grafica principal puede generarse en smoke test.
- Las validaciones criticas tienen cobertura minima.
- Existe una prueba que evita comparar anios con ventanas temporales no equivalentes sin alerta.

**Riesgos**

- Crear pruebas sin estabilizar entorno puede duplicar problemas.
- Smoke tests graficos pueden ser fragiles si dependen de estilos o fuentes.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [x] Completado
- [x] Validado

**Avance ejecutado**

- Se agrego `pytest` como dependencia directa en `requirements.txt`.
- Se creo suite minima en `tests/`.
- Cobertura inicial:
  - columnas obligatorias;
  - `id_reporte` no nulo;
  - `id_reporte` unico cuando se requiere;
  - rango valido de `mes`;
  - anios configurados existentes;
  - advertencia por ventana temporal parcial;
  - formato de mensajes de validacion;
  - Excel invalido enviado a `datos_error/` y manifest;
  - CSV en carpeta de entrada marcado como `skipped`.
- Pruebas ejecutadas:

```text
python -m pytest -q
14 passed, 1 warning
```

- Commit relacionado: `afb8b6b test: add validator and ETL operational coverage`.
- Warning conocido: pandas 2.2.0 emite aviso de que `pyarrow` sera dependencia requerida en pandas 3.0. No bloquea pruebas ni ejecucion. Decision actual: no agregar `pyarrow` mientras el proyecto no lo use directamente.
- Se agrego smoke test de visualizacion principal:
  - test: `test_plot_09_carrera_anual_smoke`;
  - usa dataset temporal pequeno;
  - escribe PNG en `tmp_path`;
  - no toca salidas reales ni PDF.
- Se agregaron pruebas de politica de retencion:
  - modo deshabilitado no borra;
  - `dry_run` no borra;
  - limpieza real controlada elimina solo vencidos y conserva `.gitkeep`.

**Pendientes**

- Ampliar fixture de Excel valido para multiples meses/productos si se requiere mayor cobertura.
- Agregar prueba opcional de integracion PostgreSQL.

### Etapa 8 - Mejoras operativas posteriores

**Objetivo**

Registrar mejoras utiles como backlog, sin ejecutarlas como trabajo inmediato.

**Hallazgos relacionados**

- La ejecucion actual depende principalmente de `python main.py`.
- Existe configuracion global mutable.
- La secuencia de graficas esta declarada de forma extensa en el orquestador.
- Hay oportunidad de reorganizacion mayor, pero no es prioritaria para estabilizar.

**Acciones propuestas**

- Backlog posterior:
  - CLI con argumentos `--skip-db`, `--only-etl`, `--only-report`.
  - Front operativo para facilitar la ejecucion del ETL y reducir errores de configuracion para usuarios no tecnicos.
  - Reducir configuracion global mutable.
  - Declarar secuencia de graficas.
  - Reorganizacion mayor de carpetas.
  - Refactor amplio de visualizaciones.

**Entregables**

- Backlog tecnico priorizado.
- Criterios para iniciar refactor mayor.
- Lista de dependencias entre mejoras.
- Requerimiento futuro documentado para front operativo del ETL.

**Criterios de aceptacion**

- Las mejoras quedan registradas.
- No se mezclan con estabilizacion inmediata.
- El backlog no bloquea las etapas 1 a 4.

**Riesgos**

- Iniciar refactors antes de estabilizar puede aumentar incertidumbre.
- Cambios amplios en visualizaciones pueden afectar entregables ejecutivos.

**Estado**

- [ ] Pendiente
- [ ] En proceso
- [ ] Completado
- [ ] Validado

## 5. Checklist maestro de entregables

### Entorno y dependencias

- [x] Version Python objetivo definida
- [x] `.venv` reconstruido o validado
- [x] `requirements.txt` limpio
- [x] `.env.example` creado o actualizado
- [x] `.gitignore` validado
- [x] Ejecucion basica validada

### Reporte y PostgreSQL

- [x] Confirmado si `main.py` esta acoplado a PostgreSQL
- [x] Config `database.enabled` propuesta o implementable
- [x] Config `database.fail_on_error` propuesta o implementable
- [x] Config `database.health_check` propuesta o implementable
- [x] Health check PostgreSQL definido
- [x] Modo reporte sin DB documentado
- [x] Politica productiva local/Supabase/Cloud Run documentada
- [x] Falla DB no bloqueante definida para `fail_on_error: false`

### ETL e insumos

- [x] Movimiento de archivos fuente revisado
- [x] Copia de trabajo propuesta
- [x] Carpeta `datos_error` propuesta
- [x] `except: pass` identificado para correccion
- [x] Validacion previa de Excel definida
- [x] Alerta por carpeta sin `.xls` o `.xlsx` definida
- [x] Mensaje para CSV directo vs carpeta de Excels definido
- [x] `datos_work/` creado como zona temporal de trabajo
- [x] `datos_procesados/` creado como destino opcional por configuracion
- [x] Manifest JSON por corrida definido
- [x] Validacion con Excel real nuevo
- [x] Validacion con Excel invalido controlado
- [x] Validacion automatizada con Excel sintetico valido

### Contrato de datos

- [x] Validador CSV definido
- [x] `id_reporte` validado
- [x] Tipos y rangos definidos
- [x] Catalogo de estados validado
- [x] Validador reutilizable para ETL y migracion
- [x] Validacion de anios de `config.yaml` contra dataset definida
- [x] Validacion de ventanas temporales comparables definida
- [x] Graficas 22, 24 y 40 revisadas para comparacion YTD/anio completo/proyeccion
- [x] Grafica 41 revisada para CAGR YTD comparable
- [x] Grafica 09 revisada para rango historico configurable
- [x] Escala visual de graficas en PDF configurada
- [x] Portada PDF actualizada con rango, autor y fuente

### Logging

- [x] logging estandar definido
- [x] Archivo de log por corrida propuesto
- [x] prints operativos a sustituir identificados
- [x] errores criticos clasificados
- [x] Emojis y simbolos Unicode retirados de mensajes operativos

### Pruebas

- [x] pytest propuesto
- [x] pruebas minimas listadas
- [x] pruebas unitarias separadas de integracion
- [x] smoke test de visualizaciones definido
- [x] prueba de ventana temporal comparable definida
- [x] pruebas de ETL operativo con error/skipped definidas
- [x] warning pandas/pyarrow documentado como no bloqueante
- [x] politica de retencion/limpieza definida en modo seguro

### Documentacion

- [x] README UTF-8/ASCII limpio
- [x] instrucciones de ejecucion actualizadas
- [x] estructura del proyecto documentada
- [x] riesgos conocidos documentados
- [x] politica Git documentada

## 6. Orden recomendado de ejecucion

No ejecutar las 8 etapas de golpe. El orden recomendado es incremental y verificable.

### Bloque 1

- Entorno
- Dependencias
- Ejecucion base

Objetivo: comprobar que el proyecto puede instalarse y ejecutar comandos basicos en un entorno limpio.

### Bloque 2

- Separar reporte y PostgreSQL
- Confirmar acoplamiento real antes de modificar `main.py`
- Agregar bloque `database` en `config.yaml`
- Ajustar `main.py` para aplicar `enabled`, `fail_on_error` y `health_check`
- Agregar health check sencillo de PostgreSQL
- Permitir que fallas DB no bloqueen PDF con `fail_on_error: false`
- Documentar modo local/productivo

Objetivo: permitir que la generacion del PDF no dependa obligatoriamente de PostgreSQL cuando asi se configure.

### Bloque 3

- Proteger insumos
- Validar Excel
- Eliminar errores silenciosos
- Alertar si no existen archivos `.xls` o `.xlsx` cuando la entrada configurada sea carpeta

Objetivo: evitar perdida de archivos fuente y detectar entradas invalidas antes de procesarlas.

### Bloque 4

- Validador de contrato de datos
- Validacion de anios configurados contra anios disponibles en el dataset
- Validacion de ventanas temporales comparables para graficas de desempeno

Objetivo: validar el CSV consolidado o dataset base antes del ETL analitico y antes de migrar a PostgreSQL.

### Bloque 5

- Logging
- Limpieza
- Pruebas minimas
- Retiro de emojis/simbolos Unicode de mensajes operativos

Objetivo: mejorar trazabilidad, documentacion y confianza en cambios futuros sin abrir un refactor grande.

## Capa de metricas para mini reporte e IA

Se agrega una capa inicial en `report_metrics.py` para separar calculos estrategicos de las visualizaciones actuales y preparar una futura generacion de mini reporte ejecutivo con insights IA.

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

## 7. Criterios para congelar version en GitHub

Antes de congelar una version estable en GitHub, deben cumplirse estos criterios:

- Proyecto ejecuta desde entorno limpio.
- `requirements.txt` no tiene duplicados.
- Se puede generar PDF.
- PostgreSQL es opcional o su falla esta controlada.
- La politica `database.enabled` / `database.fail_on_error` esta implementada o documentada para operar en productivo.
- El proyecto esta preparado para conectar con PostgreSQL administrado mediante variables de entorno.
- No se alteran insumos originales sin configuracion explicita.
- Existe checklist actualizado.
- Existen validaciones minimas de contrato de datos.
- Se alerta cuando los anios configurados no existen en los datos.
- Se alerta cuando la carpeta de entrada no contiene archivos Excel procesables.
- Las graficas comparativas no mezclan anio completo contra anio parcial sin advertencia o criterio explicito.
- README explica instalacion y ejecucion.
- `.env.example` describe variables necesarias sin secretos reales.
- `.gitignore` excluye `.venv`, salidas generadas y archivos sensibles.
- Los riesgos conocidos estan documentados.

## 8. Pendientes y decisiones abiertas

Registrar aqui las decisiones que deben cerrarse antes o durante la estabilizacion:

### Decisiones cerradas

- Version final de Python elegida: Python 3.11.
- PostgreSQL es importante, pero no debe bloquear el PDF si `fail_on_error: false`.
- `DATABASE_URL` ya quedo agregado como compatibilidad para servicios administrados.
- Quitar emojis y simbolos Unicode de mensajes operativos.
- Agregar alerta cuando la entrada configurada sea carpeta y no existan `.xls` o `.xlsx`.
- Validar anios definidos en `config.yaml` contra los anios disponibles en el dataset.
- El CSV consolidado `SII_concentrado_v3.csv` permanece como artefacto local de trabajo y queda fuera de Git.
- Datos productivos, Excels, salidas PNG/PDF, logs, manifests, respaldos y zonas ETL quedan fuera de Git por `.gitignore`.
- Los archivos originales en `datos_entrada/` no se mueven ni modifican por defecto.
- El ETL usa copia de trabajo en `datos_work/` cuando `etl.usar_zona_trabajo: true`.
- `datos_error/` se usa para copias de archivos fallidos o rechazados.
- README operativo actualizado y documento obsoleto `docs/project_state.md` eliminado.
- Se adopto YTD comparable como criterio base para graficas YoY/CAGR con anio parcial.
- Nivel minimo inicial de pruebas definido e implementado con `pytest`; estado actual: `21 passed, 1 warning`.

### Pendientes reales

- Definir si el primer despliegue productivo usara PostgreSQL local, Supabase, Cloud SQL u otro servicio administrado.
- Definir politica de manejo de errores: detener, advertir o continuar segun severidad.
- Mantener monitoreado el warning de pandas/pyarrow; agregar `pyarrow` solo si se adopta pandas 3.x o formatos Arrow/Parquet.
- Definir si la ausencia de archivos `.xls` o `.xlsx` debe detener el proceso o solo advertir cuando ya existe CSV consolidado.
- Definir comportamiento cuando `anio_objetivo` no existe pero se usa para graficas de proyeccion.
- Definir alcance del front operativo futuro: solo ejecutar ETL, ejecutar reporte completo o administrar configuracion.
- Validar politica de retencion en ambiente real antes de activar `enabled: true`.
- Ampliar fixture de Excel valido para multiples meses/productos si se requiere mayor cobertura.
- Agregar prueba opcional de integracion PostgreSQL.
- Evaluar CI basico para ejecutar `pytest` en cada cambio.

## 9. Restricciones vigentes

- No implementar CLI todavia.
- No reorganizar toda la estructura sin una etapa especifica.
- No cambiar logica analitica sin requerimiento explicito.
- No eliminar archivos locales sin confirmacion.
- No versionar datos productivos, secretos, logs, manifests ni salidas generadas.
- Mantener PostgreSQL opcional/no bloqueante cuando `database.fail_on_error: false`.
- Mantener pruebas minimas verdes antes de nuevos commits relevantes.

## 10. Siguientes pasos recomendados

### Prioridad inmediata

1. Validar politica de retencion en ambiente real con `enabled: true` y `dry_run: true`.
2. Ampliar fixture sintetico de ETL para multiples meses/productos si se requiere mayor cobertura.

### Preparacion productiva

4. Definir destino productivo PostgreSQL:
   - local;
   - Supabase;
   - Cloud SQL;
   - otro servicio administrado.
5. Evaluar CI basico para ejecutar:

```text
python -m pytest -q
```

6. Documentar convencion de nombres para archivos SII en `datos_entrada/README.md`.

### Backlog controlado

7. Evaluar prueba opcional de integracion PostgreSQL.
8. Evaluar runner/CLI/frontend operativo para usuarios no tecnicos.
9. Evaluar politica de almacenamiento externo para PDFs y PNGs generados.
