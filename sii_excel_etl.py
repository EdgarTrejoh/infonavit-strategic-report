#======================================
# Archivo infonavit_etl.py 
#======================================

"""
Módulo que recibe un archivo excel para su transformación en csv
El archivo csv resultante se convierte en insumo de un sistema para generar visualizacioens / reportes
Todos los módulos se desarrollan en python
"""

import pandas as pd
import os
import re
import hashlib
import shutil
from datetime import datetime

# 1. Catálogo oficial
ESTADOS_MX = {
    "Aguascalientes": 1, "Baja California": 2, "Baja California Sur": 3, "Campeche": 4,
    "Coahuila": 5, "Colima": 6, "Chiapas": 7, "Chihuahua": 8, "Ciudad de México": 9,
    "Durango": 10, "Guanajuato": 11, "Guerrero": 12, "Hidalgo": 13, "Jalisco": 14,
    "Estado de México": 15, "Michoacán": 16, "Morelos": 17, "Nayarit": 18,
    "Nuevo León": 19, "Oaxaca": 20, "Puebla": 21, "Querétaro": 22, "Quintana Roo": 23,
    "San Luis Potosí": 24, "Sinaloa": 25, "Sonora": 26, "Tabasco": 27, "Tamaulipas": 28,
    "Tlaxcala": 29, "Veracruz": 30, "Yucatán": 31, "Zacatecas": 32
}

# 2. Mapa de limpieza para variantes de nombres
MAPA_LIMPIEZA = {
    "CDMX": "Ciudad de México",
    "México": "Estado de México",
    "Edo. de México": "Estado de México",
    "Distrito Federal": "Ciudad de México"
}

MESES_MAP = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
    "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
}

def normalizar_estado(nombre):
    """Limpia el nombre del estado y aplica el mapa de sinónimos."""
    if pd.isna(nombre):
        return None
    nombre_limpio = str(nombre).strip()
    if nombre_limpio in MAPA_LIMPIEZA:
        nombre_limpio = MAPA_LIMPIEZA[nombre_limpio]
    return nombre_limpio

def generar_id_reporte(row):
    """Crea una llave única para PostgreSQL."""
    cadena = f"{row['anio']}_{row['mes']}_{row['estado']}_{row['linea']}_{row['producto']}_{row['metrica']}"
    return hashlib.md5(cadena.encode()).hexdigest()

def procesar_archivo_sii(ruta_archivo):
    nombre_archivo = os.path.basename(ruta_archivo)
    
    # CORRECCIÓN 1: Regex del año (buscamos 4 dígitos)
    anio_match = re.search(r'SII_(\d{4})', nombre_archivo)
    anio = int(anio_match.group(1)) if anio_match else 0
    
    # CORRECCIÓN 2: Uso de read_excel en lugar de read_csv
    df_raw = pd.read_excel(ruta_archivo, header=None)
    
    # Procesar encabezados jerárquicos
    header_rows = df_raw.iloc[0:3].copy()
    header_rows.iloc[0] = header_rows.iloc[0].ffill()
    header_rows.iloc[1] = header_rows.iloc[1].ffill()
    
    # Datos (de la fila 3 en adelante)
    data = df_raw.iloc[3:].copy()
    
    # Rellenar estados y aplicar normalización (CDMX -> Ciudad de México, etc.)
    data[0] = data[0].ffill().apply(normalizar_estado)
    
    registros_largos = []
    
    # Iterar sobre las columnas de datos (empezando en la 3)
    for col_idx in range(3, df_raw.shape[1]):
        linea = header_rows.iloc[0, col_idx]
        producto = header_rows.iloc[1, col_idx]
        metrica = header_rows.iloc[2, col_idx]
        
        if "Totales" in str(linea) or pd.isna(metrica):
            continue
            
        # Extraer Estado (col 0), Mes (col 1) y Valor (col actual)
        temp_df = data[[0, 1, col_idx]].copy()
        temp_df.columns = ['estado_nombre', 'mes_nombre', 'valor']
        
        temp_df['linea'] = linea
        temp_df['producto'] = producto
        temp_df['metrica'] = metrica
        
        registros_largos.append(temp_df)
    
    df_final = pd.concat(registros_largos, ignore_index=True)
    
    # Mapeos finales
    df_final['anio'] = anio
    df_final['estado'] = df_final['estado_nombre'].map(ESTADOS_MX)
    df_final['mes'] = df_final['mes_nombre'].map(MESES_MAP)
    df_final['periodicidad'] = "mensual"
    df_final['fuente'] = "INFONAVIT_SII"
    df_final['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Limpieza de nulos
    df_final = df_final.dropna(subset=['estado', 'mes', 'valor'])
    df_final['valor'] = pd.to_numeric(df_final['valor'], errors='coerce').fillna(0)
    
    # Generar id_reporte
    df_final['id_reporte'] = df_final.apply(generar_id_reporte, axis=1)
    
    cols_orden = ['id_reporte', 'anio', 'estado', 'mes', 'linea', 'producto', 'metrica', 'valor', 'periodicidad', 'fuente', 'timestamp']
    return df_final[cols_orden]

def ejecutar_concentrado(path_origen, archivo_salida='SII_concentrado_v3.csv'):
    # Carpeta para archivos ya procesados
    carpeta_procesados = os.path.join(path_origen, 'datos_procesados')
    if not os.path.exists(carpeta_procesados):
        os.makedirs(carpeta_procesados)

    # Buscar archivos Excel
    archivos = [f for f in os.listdir(path_origen) 
                if (f.endswith('.xlsx') or f.endswith('.xls')) and not f.startswith('~$')]
    
    if os.path.exists(archivo_salida):
        historico = pd.read_csv(archivo_salida)
        periodos_procesados = set(zip(historico['anio'], historico['mes']))
    else:
        historico = pd.DataFrame()
        periodos_procesados = set()

    bloques_nuevos = []
    archivos_exitosos = []

    for f in archivos:
        ruta_completa = os.path.join(path_origen, f)
        print(f"Procesando: {f}...")
        
        try:
            df_temp = procesar_archivo_sii(ruta_completa)
            
            # Filtro incremental (por año y mes)
            df_nuevo = df_temp[~df_temp.apply(lambda x: (x['anio'], x['mes']) in periodos_procesados, axis=1)]
            
            if not df_nuevo.empty:
                bloques_nuevos.append(df_nuevo)
                print(f"-> {len(df_nuevo)} registros nuevos detectados.")
            else:
                print("-> Sin información nueva.")
            
            archivos_exitosos.append(f)

        except Exception as e:
            print(f"!!! Error procesando {f}: {e}")

    # Guardar resultados
    if bloques_nuevos:
        final = pd.concat([historico] + bloques_nuevos, ignore_index=True)
        final.to_csv(archivo_salida, index=False, encoding='utf-8-sig')
        print(f"\nArchivo '{archivo_salida}' actualizado exitosamente.")
    else:
        print("\nNo hubo datos nuevos para agregar.")

    # Mover archivos
    for f in archivos_exitosos:
        try:
            shutil.move(os.path.join(path_origen, f), os.path.join(carpeta_procesados, f))
            print(f"Movido a historial: {f}")
        except:
            pass

if __name__ == "__main__":
    carpeta_archivos = './datos_entrada' 
    archivo_salida = 'SII_concentrado_v3.csv'
    
    print("Iniciando proceso de consolidación...")
    ejecutar_concentrado(carpeta_archivos, archivo_salida)
    print("¡Proceso terminado!")