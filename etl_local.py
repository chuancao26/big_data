import json
import glob
import sys
import os

# 1. Buscar automáticamente el archivo JSONL en la máquina actual
archivos_jsonl = glob.glob("onpe_rango_*.jsonl")

if not archivos_jsonl:
    print("No se encontró ningún archivo .jsonl en este nodo.")
    sys.exit(1)

archivo_entrada = archivos_jsonl[0]
archivo_salida = archivo_entrada.replace(".jsonl", ".tsv")

print(f"Iniciando transformación a formato OLAP: {archivo_entrada} -> {archivo_salida}")

mesas_procesadas = 0
registros_tsv = 0

with open(archivo_entrada, 'r', encoding='utf-8') as f_in, \
     open(archivo_salida, 'w', encoding='utf-8') as f_out:
    
    for linea in f_in:
        linea = linea.strip()
        if not linea:
            continue
            
        try:
            acta = json.loads(linea)
            
            # 1. EXTRACCIÓN DE DATOS DE LA MESA 
            mesa = acta.get('codigoMesa', 'UNKNOWN')
            idEleccion = str(acta.get('idEleccion', ''))
            idAmbito = str(acta.get('idAmbitoGeografico', ''))
            idUbigeo = str(acta.get('idUbigeo', ''))
            
            # Limpiamos el estado del acta de posibles saltos de línea o tabuladores que romperían el TSV
            estadoActa = acta.get('descripcionEstadoActa', 'UNKNOWN')
            if estadoActa:
                estadoActa = str(estadoActa).replace('\t', ' ').replace('\n', ' ')
            else:
                estadoActa = 'UNKNOWN'
            
            # --- 2. EXTRACCIÓN DE TOTALES DE LA MESA (MÉTRICAS REPETITIVAS) ---
            # Si el valor es None, guardamos '0'
            electores = str(acta.get('totalElectoresHabiles') or '0')
            asistentes = str(acta.get('totalAsistentes') or '0')
            emitidos = str(acta.get('totalVotosEmitidos') or '0')
            validos = str(acta.get('totalVotosValidos') or '0')
            
            # --- 3. EXTRACCIÓN DE VOTOS POR PARTIDO/OPCIÓN (MÉTRICA PRINCIPAL) ---
            detalles = acta.get('detalle', [])
            
            for item in detalles:
                # Extraemos y limpiamos el nombre del partido
                partido = item.get('adDescripcion', '')
                if partido:
                    partido = str(partido).replace('\t', ' ').replace('\n', ' ')
                
                votos = item.get('adVotos')
                
                # Novedad: Si hay partido, procesamos la fila sí o sí
                if partido:
                    # Si los votos son nulos (None) o no son un número, forzamos un 0
                    votos_limpios = votos if isinstance(votos, int) else 0
                    
                    # FORMATO ESTRICTO: 11 columnas separadas por tabulador (\t)
                    fila_tsv = f"{mesa}\t{idEleccion}\t{idAmbito}\t{idUbigeo}\t{estadoActa}\t{electores}\t{asistentes}\t{emitidos}\t{validos}\t{partido}\t{votos_limpios}\n"
                    
                    f_out.write(fila_tsv)
                    registros_tsv += 1

            mesas_procesadas += 1
            if mesas_procesadas % 10000 == 0:
                print(f"Progreso: {mesas_procesadas} actas convertidas...")
                
        except Exception as e:
            # Si una línea está totalmente corrupta, la saltamos para que el ETL no se detenga
            pass

print(f"¡ETL completado! Se generaron {registros_tsv} filas en {archivo_salida}")
