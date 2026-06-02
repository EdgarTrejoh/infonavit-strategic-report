# 📊 Reporte Estratégico INFONAVIT 2026  
**ETL + Análisis + Visualización Automatizada**

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-green?logo=pandas)
![ETL](https://img.shields.io/badge/ETL-Pipeline-orange)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Visualization-informational)
![Status](https://img.shields.io/badge/Status-Stable-success)

Sistema integral en **Python** para:
- transformar información del **SII INFONAVIT** (Excel → CSV),
- consolidar y estandarizar datos,
- sincronizar el histórico consolidado con **PostgreSQL**,
- generar **análisis económico-financiero**,
- producir **visualizaciones ejecutivas** y un **PDF automatizado**.

Diseñado para entornos reales de análisis, no para demos.

---

## 🧠 Enfoque del proyecto

Este repositorio implementa un **pipeline completo**:

1. **Ingesta flexible**
   - Excel individual
   - Carpeta con múltiples Excels
   - CSV consolidado
2. **ETL robusto**
   - Normalización territorial y temporal
   - Métricas homogéneas
   - Llave única (`id_reporte`)
3. **Capa analítica**
   - Métricas globales, por línea, producto y estado
   - Identificación de patrones y “culpables”
4. **Capa de visualización**
   - +40 gráficas estratégicas
   - Exportación automática a PDF ejecutivo
5. **Persistencia PostgreSQL**
   - Sincronización incremental por `id_reporte`
   - Inserción de registros nuevos y actualización de correcciones
   - Sin eliminación ni recreación de la tabla histórica durante la sincronización

---

## 🗂️ Estructura del proyecto

```text
001_reporte_2026_gpt/
├── datos_entrada/          # Excels fuente (SII)
├── docs/                   # Documentación interna
│   └── project_state.md
├── respaldo/               # Backups / históricos
├── salidas_viz_final/      # PDFs y gráficos finales
│
├── config.yaml             # Configuración general del proyecto
├── config.py               # Variables globales inyectadas
├── .env.example            # Plantilla de conexión a PostgreSQL
├── database.py             # Configuración de conexión a PostgreSQL
├── migrate_csv_to_pg.py    # Sincronización incremental CSV → PostgreSQL
│
├── etl.py                  # DataManager (ETL + datasets analíticos)
├── viz/                    # Paquete de visualizaciones modularizadas
│   ├── macro.py            # Gráficas de nivel nacional y métricas globales
│   ├── lineas.py           # Análisis de líneas estratégicas y productos
│   ├── geo.py              # Visualizaciones geográficas (mapas, pareto)
│   ├── estrategia.py       # Matrices, scorecards y mapas de calor
│   ├── helpers.py          # Formateadores y utilidades compartidas
│   └── __init__.py         # Puente de compatibilidad
├── utils.py                # Utilidades comunes
├── main.py                 # Orquestador del pipeline completo
│
├── SII_concentrado_v3.csv  # CSV consolidado (autogenerado)
└── README.md
```

---

## 🔁 Flujo general del sistema

```text

Excel / Carpeta / CSV
        ↓
ETL Excel → CSV (si aplica)
        ↓
Carga estandarizada (DataManager)
        ↓
Amasado analítico (df_master, df_global, etc.)
        ↓
Validación de id_reporte
        ↓
Tabla temporal de staging
        ↓
Upsert PostgreSQL por id_reporte
        ↓
Tabla infonavit_historico actualizada
        ↓
Visualizaciones
        ↓
PDF Ejecutivo Final
```
---

## 🔄 Pipeline del sistema

```text
Fuentes (Excel / CSV)
        ↓
ETL Excel → CSV (normalización)
        ↓
CSV estándar consolidado
        ↓
DataManager (ETL analítico)
        ↓
Datasets derivados
        ↓
Sincronización PostgreSQL por id_reporte
        ↓
Visualizaciones estratégicas
        ↓
PDF Ejecutivo Final

```

---

## 📥 Insumos soportados

El sistema detecta automáticamente el tipo de entrada configurado en config.yaml:

```text
rutas:
  archivo_entrada: "datos_entrada"        # carpeta con Excels
  # archivo_entrada: "SII_2026_enero.xlsx" # Excel individual
  # archivo_entrada: "SII_concentrado_v3.csv" # CSV directo
```

No se requiere cambiar código.

---

## 📄 Estructura del CSV consolidado

El CSV generado (SII_concentrado_v3.csv) sigue un contrato de datos fijo:

|Columna | Descripción|Tipo de Dato (Sugerido)|
|--------|------------|-----------------------|
|id_reporte| Hash MD5 único por periodo, estado, línea, producto y métrica|String |
|anio|Año extraído del nombre del archivo|Integer|
|mes|Mes calendario (1–12)|Integer|
|estado|ID numérico que identifica a la entidad federativa|Integer / Categorical|
|linea|Clasificación de la línea de crédito|String|
|producto|Nombre del producto financiero|String|
|metrica|Tipo de medición (Monto o Número de créditos)|String / Categorical|
|valor|Magnitud numérica de la métrica|Float / Decimal|
|fuente|Origen de los datos (INFONAVIT_SII)|String (Constant)|
|periodicidad|Frecuencia de actualización (Mensual)|String (Constant)|
|timestamp|Registro exacto de la fecha y hora de carga|DateTime|

---

## ▶️ Ejecución del reporte

```bash
python main.py
```

El proceso:

1. Lee configuración (<mark style="background-color: #E0E0E0;"> config.yaml </mark>)
2. Ejecuta ETL (si aplica)
3. Construye datasets analíticos
4. Sincroniza PostgreSQL mediante upsert por `id_reporte`
5. Genera gráficas en secuencia definida
6. Exporta un PDF ejecutivo en <mark style="background-color: #E0E0E0;"> salidas_viz_final/ </mark>

Si la sincronización PostgreSQL falla, el reporte se detiene antes de generar el PDF.

---

## 🐘 Sincronización incremental con PostgreSQL

La carga a PostgreSQL forma parte de la ejecución de `main.py`. Después del ETL, el sistema sincroniza el CSV configurado directamente o `SII_concentrado_v3.csv` cuando la fuente es una carpeta o un archivo Excel.

### Configuración

1. Crea el archivo `.env` a partir de `.env.example`.
2. Completa las variables de conexión:

```text
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
DB_HOST=localhost
DB_PORT=5432
DB_NAME=infonavit
```

El archivo `.env` contiene credenciales locales y está excluido de Git.

### Ejecución manual de soporte

Normalmente no necesitas ejecutar el migrador por separado porque `main.py` ya lo invoca. Para sincronizar PostgreSQL sin regenerar visualizaciones ni PDF, puedes ejecutar:

```bash
python migrate_csv_to_pg.py
```

El proceso:

1. Lee `SII_concentrado_v3.csv`.
2. Valida que exista `id_reporte` y que no tenga valores vacíos.
3. Detecta duplicados dentro del CSV y conserva la última versión de cada `id_reporte`.
4. Crea `infonavit_historico` únicamente si todavía no existe.
5. Conserva la tabla existente sin eliminarla ni recrearla.
6. Carga los datos en una tabla temporal de staging.
7. Ejecuta un upsert transaccional:
   - inserta los `id_reporte` nuevos;
   - actualiza los registros existentes con la versión más reciente del CSV.

La tabla final utiliza un índice único sobre `id_reporte`. Si ya existen duplicados históricos en PostgreSQL, la sincronización se detiene sin borrar información para permitir una revisión explícita.

La cuenta PostgreSQL necesita permisos para crear la tabla inicial, crear el índice único y utilizar una tabla temporal. En cada ejecución, el script informa:

- total de filas leídas del CSV;
- total de `id_reporte` únicos;
- duplicados detectados en el CSV;
- regla aplicada a duplicados: conservar la última versión;
- confirmación de que la sincronización terminó dentro de una transacción;
- confirmación de que la tabla final no fue eliminada ni recreada durante la sincronización.

### Validación recomendada

Después de sincronizar, valida que no existan duplicados:

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

En la primera consulta, ambos conteos deben coincidir. La segunda consulta debe devolver cero filas.

---

## 📊 Datasets principales generados

Dentro de DataManager:

* <mark style="background-color: #E0E0E0;"> df_master </mark> → dataset base analítico 

* <mark style="background-color: #E0E0E0;"> df_global </mark> → agregados nacionales 

* <mark style="background-color: #E0E0E0;"> df_linea_mensual </mark> → evolución por línea 

* <mark style="background-color: #E0E0E0;"> df_raw_monto </mark> / <mark style="background-color: #E0E0E0;"> df_raw_num </mark> → insumos crudos 

* <mark style="background-color: #E0E0E0;"> df_analisis_global </mark> → métricas derivadas 

Estos datasets alimentan todas las visualizaciones.

---

## 🧩 Principios de diseño

❌ Sin lógica de ETL en visualizaciones

❌ Sin “scripts mágicos”

✅ Contrato de datos explícito

✅ Reproducibilidad

✅ Escalable a nuevas fuentes (SHF, CNBV, Banxico)

---

## 🚧 Roadmap natural

*  Integración de nuevas fuentes (SHF, Banxico)

*  Tests automáticos del ETL

* CLI con argumentos (--input, --force)

*  Publicación como paquete interno

*  API de consulta de indicadores

---

## 🧑‍💻 Autor

Proyecto desarrollado para análisis estratégico del mercado de crédito y vivienda en México, con enfoque en:

* análisis económico,

* toma de decisiones ejecutivas,

* automatización reproducible.

---

## 📄 Licencia

Uso interno / analítico.
Licencia abierta (MIT).

---
