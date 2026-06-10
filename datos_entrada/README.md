# datos_entrada

Esta carpeta contiene los archivos originales de entrada del Sistema de Informacion Infonavit (SII).

Los archivos reales o productivos no deben versionarse en Git. El contenido de esta carpeta esta ignorado por `.gitignore`, excepto este `README.md` y `.gitkeep`.

## Convencion de nombres

Los archivos Excel SII deben nombrarse con el siguiente patron:

```text
SII_YYYY.xlsx
```

Ejemplos validos:

```text
SII_2024.xlsx
SII_2025.xlsx
SII_2026.xlsx
```

## Comportamiento del ETL

Los archivos originales en `datos_entrada/` no se modifican ni se mueven por defecto.

Si en `config.yaml` esta configurado:

```yaml
etl:
  usar_zona_trabajo: true
```

el ETL crea una copia de trabajo en `datos_work/` y procesa esa copia, no el archivo original.

## Que no debe colocarse aqui

No colocar en `datos_entrada/`:

- CSV consolidados.
- PDFs generados.
- PNGs generados.
- Archivos temporales de Excel, por ejemplo `~$archivo.xlsx`.
- Datos de prueba o fixtures.

Los datos de prueba deben ubicarse en:

```text
data_samples/
tests/fixtures/
```
