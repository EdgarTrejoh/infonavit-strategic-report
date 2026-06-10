import argparse
import pandas as pd
import logging
from sqlalchemy import inspect, text
from contract_validator import format_validation_messages, validate_consolidated_dataframe
from database import engine

logger = logging.getLogger(__name__)


def migrate(csv_path="SII_concentrado_v3.csv"):
    logger.info("Iniciando migracion de CSV a PostgreSQL...")
    if engine is None:
        logger.error("No se pudo conectar a la base de datos.")
        return False

    table_name = "infonavit_historico"

    try:
        logger.info("Leyendo archivo %s (puede tardar un momento)...", csv_path)
        df = pd.read_csv(csv_path)
        total_filas_csv = len(df)
        logger.info("Total de filas leidas del CSV: %s", total_filas_csv)

        validation = validate_consolidated_dataframe(df, require_unique_id=False)
        for message in format_validation_messages(validation):
            if message.startswith("ERROR"):
                logger.error(message)
            else:
                logger.warning(message)
        if not validation.ok:
            return False

        duplicados_csv = df.duplicated(subset=["id_reporte"], keep="last").sum()
        total_ids_unicos = df["id_reporte"].nunique()
        logger.info("Total de 'id_reporte' unicos: %s", total_ids_unicos)
        logger.info("Total de duplicados detectados en el CSV: %s", duplicados_csv)
        if duplicados_csv:
            logger.warning(
                "Se detectaron %s registros duplicados en el CSV. "
                "Se conservara la version mas reciente de cada 'id_reporte'.",
                duplicados_csv,
            )
            df = df.drop_duplicates(subset=["id_reporte"], keep="last").copy()

        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"])

        logger.info("Total de registros unicos a sincronizar: %s", len(df))

        quote = engine.dialect.identifier_preparer.quote
        quoted_table = quote(table_name)
        staging_table = "infonavit_historico_staging"
        quoted_staging = quote(staging_table)
        quoted_id = quote("id_reporte")
        index_name = "uq_infonavit_historico_id_reporte"
        quoted_index = quote(index_name)

        with engine.begin() as connection:
            table_exists = inspect(connection).has_table(table_name)

            if not table_exists:
                logger.info("La tabla destino '%s' no existe. Creando su estructura inicial...", table_name)
                df.head(0).to_sql(table_name, connection, if_exists="fail", index=False)
            else:
                logger.info(
                    "La tabla destino '%s' ya existe. Se conservara sin eliminarla ni recrearla.",
                    table_name,
                )
                columnas_tabla = {col["name"] for col in inspect(connection).get_columns(table_name)}
                columnas_faltantes = set(df.columns) - columnas_tabla
                if columnas_faltantes:
                    raise ValueError(
                        "La tabla destino no contiene estas columnas del CSV: "
                        f"{sorted(columnas_faltantes)}"
                    )

            # Si existen duplicados historicos, PostgreSQL detendra aqui la carga
            # sin borrar registros para que puedan revisarse de forma explicita.
            connection.execute(
                text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS {quoted_index} "
                    f"ON {quoted_table} ({quoted_id})"
                )
            )

            connection.execute(
                text(
                    f"CREATE TEMP TABLE {quoted_staging} "
                    f"(LIKE {quoted_table} INCLUDING DEFAULTS) ON COMMIT DROP"
                )
            )
            df.to_sql(staging_table, connection, if_exists="append", index=False)

            quoted_columns = [quote(col) for col in df.columns]
            columns_sql = ", ".join(quoted_columns)
            update_columns = [col for col in quoted_columns if col != quoted_id]
            update_sql = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_columns)

            connection.execute(
                text(
                    f"INSERT INTO {quoted_table} ({columns_sql}) "
                    f"SELECT {columns_sql} FROM {quoted_staging} "
                    f"ON CONFLICT ({quoted_id}) DO UPDATE SET {update_sql}"
                )
            )

        logger.info(
            "OK: Sincronizacion exitosa. %s registros procesados en la tabla '%s' sin reemplazarla.",
            len(df),
            table_name,
        )
        logger.info("OK: Proceso completado dentro de una transaccion.")
        logger.info("OK: La tabla final no fue eliminada ni recreada durante la sincronizacion.")
        logger.info("Validacion recomendada en PostgreSQL:")
        logger.info(
            "SELECT COUNT(*) AS filas_totales, COUNT(DISTINCT id_reporte) AS ids_unicos FROM %s;",
            table_name,
        )
        logger.info(
            "SELECT id_reporte, COUNT(*) FROM %s GROUP BY id_reporte HAVING COUNT(*) > 1;",
            table_name,
        )
        return True
    except FileNotFoundError:
        logger.error("El archivo %s no fue encontrado.", csv_path)
        return False
    except Exception as e:
        logger.exception("Error durante la migracion: %s", e)
        return False


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Sincroniza el CSV consolidado con PostgreSQL. "
            "Por seguridad, no ejecuta cambios sin --run --yes."
        )
    )
    parser.add_argument(
        "--csv-path",
        default="SII_concentrado_v3.csv",
        help="Ruta del CSV consolidado a sincronizar.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Solicita ejecutar la migracion real.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma explicitamente que se autorizan cambios en la base configurada.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.run:
        parser.print_help()
        logger.warning("Migracion no ejecutada. Usa --run --yes para sincronizar PostgreSQL.")
        return 2

    if not args.yes:
        logger.error("Migracion no ejecutada. Falta confirmacion explicita --yes.")
        return 2

    return 0 if migrate(csv_path=args.csv_path) else 1


if __name__ == "__main__":
    raise SystemExit(main())
