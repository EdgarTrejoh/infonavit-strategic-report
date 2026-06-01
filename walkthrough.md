# Walkthrough: Refactorización de viz.py

¡La refactorización se ha completado con éxito! Hemos transformado un archivo monolítico de más de 3,000 líneas en un paquete estructurado y mantenible, sin alterar la lógica de negocio ni el reporte final.

## 🗂️ Nueva Estructura del Código

Se eliminó el archivo original `viz.py` y en su lugar se creó la carpeta estructurada `viz/` que contiene:

1. [**`viz/helpers.py`**](file:///c:/proyectos/02_etl_process/03_infonavit/001_reporte_2026_gpt/viz/helpers.py): Concentra utilidades de formato (`human_format`), cálculos comunes (`calcular_crecimiento_yoy`), posicionamiento inteligente de etiquetas y constructores de ejes.
2. [**`viz/macro.py`**](file:///c:/proyectos/02_etl_process/03_infonavit/001_reporte_2026_gpt/viz/macro.py): Contiene las visualizaciones de alto nivel (Monto Nacional, Volumen, Evolución YoY, Carreras Anuales).
3. [**`viz/lineas.py`**](file:///c:/proyectos/02_etl_process/03_infonavit/001_reporte_2026_gpt/viz/lineas.py): Maneja todo el desglose por líneas de negocio (Línea II, Línea III, Vivienda vs Terreno) y métricas derivadas de productos.
4. [**`viz/geo.py`**](file:///c:/proyectos/02_etl_process/03_infonavit/001_reporte_2026_gpt/viz/geo.py): Aisla la lógica de visualización geográfica, mapas de calor por estado y pareto de regiones (incluyendo la radiografía de CDMX).
5. [**`viz/estrategia.py`**](file:///c:/proyectos/02_etl_process/03_infonavit/001_reporte_2026_gpt/viz/estrategia.py): Agrupa los componentes ejecutivos más densos como la Matriz BCG, análisis de volatilidad, scorecards y mapas de calor (heatmaps).
6. [**`viz/__init__.py`**](file:///c:/proyectos/02_etl_process/03_infonavit/001_reporte_2026_gpt/viz/__init__.py): El archivo puente. Permite que `main.py` importe todas estas funciones transparentemente como si `viz` siguiera siendo un solo archivo.

> [!TIP]
> **Beneficio Inmediato**
> Si necesitas cambiar el color del ticket promedio o ajustar una gráfica de estado, ahora sabes exactamente en qué archivo buscar (`viz/geo.py` o `viz/macro.py`) sin tener que hacer scroll por 123 KB de código.

## 🧪 Validación

Se corrió el proceso completo (`python main.py`) en tu ambiente:
- **ETL:** Carga de >53,000 registros procesada exitosamente.
- **Gráficas:** Se generaron y anexaron +40 gráficas individuales sin un solo error de importación.
- **Salida:** El reporte final [Reporte_Estrategico_INFONAVIT_2024.pdf](file:///c:/proyectos/02_etl_process/03_infonavit/001_reporte_2026_gpt/salidas_viz_final/Reporte_Estrategico_INFONAVIT_2024.pdf) se compiló exitosamente.

## 🐞 Bug Fix Menor Incluido
Durante las pruebas en consola de Windows detectamos un problema de `UnicodeEncodeError` causado por un emoji de un "check verde" (`✅`) en los prints del archivo original. Esto se arregló limpiando los mensajes de consola en `helpers.py` para asegurar que el pipeline pueda automatizarse o integrarse con herramientas de integración continua (CI/CD) sin fallar por problemas de formato de terminal.

---
El proyecto ahora es mucho más robusto a nivel de arquitectura. ¡Listo para los siguientes pasos!


El cálculo del crecimiento interanual (YoY - Year over Year) se realiza matemáticamente en tres lugares distintos, dependiendo del nivel de detalle que requiera la gráfica:

A Nivel Global (Mes a Mes vs Año Anterior): Se calcula en el archivo viz/helpers.py dentro de la función calcular_crecimiento_yoy. Utiliza una tabla dinámica (pivot_table) y hace la fórmula clásica:

python


((pivot[year_curr] - pivot[year_prev]) / pivot[year_prev]) * 100
(Esta función alimenta la gráfica 06 del semáforo).

A Nivel de Línea de Negocio (Acumulado Anual): Se calcula directamente en viz/lineas.py dentro de la función plot_24_yoy_por_linea. Agrupa los montos del año actual ("Curr") y el año previo ("Prev") para cada línea y calcula:

python


grp["YoY"] = ((grp["Curr"] / grp["Prev"]) - 1) * 100
(Alimenta la gráfica 24 de barras divergentes horizontales).

Para la Volatilidad y Distribución (Boxplots): Se calcula en viz/macro.py dentro de plot_29_distribucion_volatilidad_yoy. Aquí se usa la función nativa de series de tiempo de Pandas para ser más eficientes, calculando el cambio porcentual con un desfase de 12 meses:

python


df_yoy = (grp.pct_change(periods=12) * 100)
