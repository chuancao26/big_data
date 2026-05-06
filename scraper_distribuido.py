import requests
import json
import time
import sys

if len(sys.argv) != 3:
    print("Uso correcto: python scraper_distribuido.py <inicio> <fin>")
    print("Ejemplo: python scraper_distribuido.py 1 22500")
    sys.exit(1)

INICIO = int(sys.argv[1])
FIN = int(sys.argv[2])

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

# Nombre del archivo dinámico según el rango
ARCHIVO_JSONL = f"onpe_rango_{INICIO}_a_{FIN}.jsonl"
DELAY_PETICION = 0.2 

session = requests.Session()
session.headers.update(HEADERS)
mesas_guardadas = 0

print(f"🚀 Iniciando rango desde {INICIO} hasta {FIN}...")

with open(ARCHIVO_JSONL, mode='w', encoding='utf-8') as archivo:
    
    for mesa_actual in range(INICIO, FIN + 1):
        codigo_mesa = str(mesa_actual).zfill(6)
        params = {"codigoMesa": codigo_mesa}
        
        exito_red = False
        for intento in range(3):
            try:
                response = session.get(API_URL, params=params, timeout=10)
                exito_red = True
                break
            except requests.exceptions.RequestException:
                time.sleep(2)
                
        if not exito_red or response.status_code != 200:
            print(f"⚠️ Error en mesa {codigo_mesa}. Saltando...")
            continue

        try:
            json_data = response.json()
        except ValueError:
            continue
            
        if json_data.get('success') == True and len(json_data.get('data', [])) > 0:
            acta_data = json_data['data'][0] 
            linea_json = json.dumps(acta_data, ensure_ascii=False)
            archivo.write(linea_json + '\n')
            
            # Flush periódico para no desgastar el disco
            if mesas_guardadas % 50 == 0:
                archivo.flush() 
            
            mesas_guardadas += 1
            
            if mesas_guardadas % 500 == 0:
                print(f"✅ Nodo actual: {mesas_guardadas} actas procesadas...")
                
        time.sleep(DELAY_PETICION)

print("\n🎉 ¡EXTRACCIÓN FINALIZADA PARA ESTE NODO!")
print(f"💾 Se guardaron {mesas_guardadas} actas en {ARCHIVO_JSONL}")
