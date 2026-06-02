import pandas as pd
from sqlalchemy import inspect, text
from database import engine

def migrate(csv_path="SII_concentrado_v3.csv"):
    print("Iniciando migración de CSV a PostgreSQL...")
    if engine is None:
        print("❌ Error: No se pudo conectar a la base de datos.")
        return False

    table_name = "infonavit_historico"

    try:
        print(f"Leyendo archivo {csv_path} (puede tardar un momento)...")
        df = pd.read_csv(csv_path)
        total_filas_csv = len(df)
        print(f"Total de filas leídas del CSV: {total_filas_csv}")
        
        if "id_reporte" not in df.columns:
            print("❌ Error: El CSV no contiene la columna obligatoria 'id_reporte'.")
            return False

        ids_vacios = df["id_reporte"].isna() | (df["id_reporte"].astype(str).str.strip() == "")
        if ids_vacios.any():
            print(f"❌ Error: El CSV contiene {ids_vacios.sum()} registros sin 'id_reporte'.")
            return False

        duplicados_csv = df.duplicated(subset=["id_reporte"], keep="last").sum()
        total_ids_unicos = df["id_reporte"].nunique()
        print(f"Total de 'id_reporte' únicos: {total_ids_unicos}")
        print(f"Total de duplicados detectados en el CSV: {duplicados_csv}")
        if duplicados_csv:
            print(
                f"⚠️ Se detectaron {duplicados_csv} registros duplicados en el CSV. "
                "Se conservará la versión más reciente de cada 'id_reporte'."
            )
            df = df.drop_duplicates(subset=["id_reporte"], keep="last").copy()

        # Opcional: asegurarnos de que la columna fecha tenga formato datetime
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
            
        print(f"Total de registros únicos a sincronizar: {len(df)}")

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
                print(f"La tabla destino '{table_name}' no existe. Creando su estructura inicial...")
                df.head(0).to_sql(table_name, connection, if_exists="fail", index=False)
            else:
                print(
                    f"La tabla destino '{table_name}' ya existe. "
                    "Se conservará sin eliminarla ni recrearla."
                )
                columnas_tabla = {col["name"] for col in inspect(connection).get_columns(table_name)}
                columnas_faltantes = set(df.columns) - columnas_tabla
                if columnas_faltantes:
                    raise ValueError(
                        "La tabla destino no contiene estas columnas del CSV: "
                        f"{sorted(columnas_faltantes)}"
                    )

            # Si existen duplicados históricos, PostgreSQL detendrá aquí la carga
            # sin borrar registros para que puedan revisarse de forma explícita.
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

        print(
            f"✅ Sincronización exitosa. {len(df)} registros procesados en "
            f"la tabla '{table_name}' sin reemplazarla."
        )
        print("✅ Proceso completado dentro de una transacción.")
        print("✅ La tabla final no fue eliminada ni recreada durante la sincronización.")
        print("Validación recomendada en PostgreSQL:")
        print(
            f"SELECT COUNT(*) AS filas_totales, "
            f"COUNT(DISTINCT id_reporte) AS ids_unicos FROM {table_name};"
        )
        print(
            f"SELECT id_reporte, COUNT(*) FROM {table_name} "
            "GROUP BY id_reporte HAVING COUNT(*) > 1;"
        )
        return True
    except FileNotFoundError:
        print(f"❌ Error: El archivo {csv_path} no fue encontrado.")
        return False
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False

if __name__ == "__main__":
    migrate()
