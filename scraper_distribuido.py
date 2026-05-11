import requests
import json
import time
import sys

if len(sys.argv) != 3:
    print("Uso correcto: python scraper_distribuido.py <indice_inicio> <indice_fin>")
    sys.exit(1)

INICIO_IDX = int(sys.argv[1])
FIN_IDX = int(sys.argv[2])

# Rango 1: de 000001 a 088064
mesas_rango_1 = [str(i).zfill(6) for i in range(1, 88065)]
# Rango 2: de 900000 a 905000
mesas_rango_2 = [str(i).zfill(6) for i in range(900000, 905001)]

lista_completa_mesas = mesas_rango_1 + mesas_rango_2

mesas_a_procesar = lista_completa_mesas[INICIO_IDX:FIN_IDX]

if not mesas_a_procesar:
    print("No hay mesas asignadas a este rango de índices. Saliendo...")
    sys.exit(0)

# Obtenemos la primera y última mesa real para nombrar los archivos
primera_mesa = mesas_a_procesar[0]
ultima_mesa = mesas_a_procesar[-1]

ARCHIVO_JSONL = f"onpe_mesas_{primera_mesa}_a_{ultima_mesa}.jsonl"
ARCHIVO_FALTANTES = f"mesas_no_existentes_{primera_mesa}_a_{ultima_mesa}.txt"

API_URL = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/actas/buscar/mesa"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://resultadoelectoral.onpe.gob.pe/",
    "Origin": "https://resultadoelectoral.onpe.gob.pe",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

DELAY_PETICION = 0.2 
session = requests.Session()
session.headers.update(HEADERS)
mesas_guardadas = 0

print(f" Iniciando extracción de {len(mesas_a_procesar)} mesas (Desde {primera_mesa} hasta {ultima_mesa})...")

with open(ARCHIVO_JSONL, mode='w', encoding='utf-8') as archivo, \
     open(ARCHIVO_FALTANTES, mode='w', encoding='utf-8') as faltantes:
    
    # 3. ITERAMOS DIRECTAMENTE SOBRE LOS CÓDIGOS DE MESA
    for codigo_mesa in mesas_a_procesar:
        params = {"codigoMesa": codigo_mesa}
        
        exito_red = False
        for intento in range(3):
            try:
                response = session.get(API_URL, params=params, timeout=10)
                exito_red = True
                break
            except requests.exceptions.RequestException:
                time.sleep(2)
                
        # Si falló la red o dio error HTTP, anotamos en faltantes
        if not exito_red or response.status_code != 200:
            print(f" Error en red o servidor para mesa {codigo_mesa}.")
            faltantes.write(codigo_mesa + '\n')
            faltantes.flush()
            continue

        try:
            json_data = response.json()
        except ValueError:
            # Si el JSON está corrupto o vacío
            faltantes.write(codigo_mesa + '\n')
            faltantes.flush()
            continue
            
        # 4. GUARDAMOS LOS DATOS SI EXISTEN
        if json_data.get('success') == True and len(json_data.get('data', [])) > 0:
            for acta_data in json_data['data']:
                linea_json = json.dumps(acta_data, ensure_ascii=False)
                archivo.write(linea_json + '\n')
            
            # Flush periódico para asegurar guardado en disco
            if mesas_guardadas % 50 == 0:
                archivo.flush() 
            
            mesas_guardadas += 1
            
            if mesas_guardadas % 500 == 0:
                print(f"Progreso: {mesas_guardadas} mesas guardadas...")
                
        else:
            faltantes.write(codigo_mesa + '\n')
            faltantes.flush()
            
        time.sleep(DELAY_PETICION)

print("\n ¡EXTRACCIÓN FINALIZADA PARA ESTE NODO!")
print(f" Se guardó información de {mesas_guardadas} mesas en {ARCHIVO_JSONL}")
print(f" Las mesas no encontradas se anotaron en {ARCHIVO_FALTANTES}")
