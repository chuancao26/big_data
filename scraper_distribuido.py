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

# 1. NOMBRES DE ARCHIVOS DINÁMICOS
ARCHIVO_JSONL = f"onpe_rango_{INICIO}_a_{FIN}.jsonl"
ARCHIVO_FALTANTES = f"mesas_no_existentes_{INICIO}_a_{FIN}.txt"
DELAY_PETICION = 0.2 

session = requests.Session()
session.headers.update(HEADERS)
mesas_guardadas = 0

print(f"🚀 Iniciando rango desde {INICIO} hasta {FIN}...")

# 2. ABRIMOS AMBOS ARCHIVOS AL MISMO TIEMPO
with open(ARCHIVO_JSONL, mode='w', encoding='utf-8') as archivo, \
     open(ARCHIVO_FALTANTES, mode='w', encoding='utf-8') as faltantes:
    
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
                
        # Si falló la red o dio error 500/404, anotamos la mesa como no procesada/existente
        if not exito_red or response.status_code != 200:
            print(f"⚠️ Error en mesa {codigo_mesa}. Registrando como no existente...")
            faltantes.write(codigo_mesa + '\n')
            faltantes.flush()
            continue

        try:
            json_data = response.json()
        except ValueError:
            # Si la respuesta no es un JSON válido, también la mandamos a faltantes
            faltantes.write(codigo_mesa + '\n')
            faltantes.flush()
            continue
            
        # 3. GUARDAMOS TODAS LAS ELECCIONES DE LA MESA (Si success es True)
        if json_data.get('success') == True and len(json_data.get('data', [])) > 0:
            
            # Recorremos cada una de las opciones (Presidencial, Senadores, Diputados...)
            for acta_data in json_data['data']:
                linea_json = json.dumps(acta_data, ensure_ascii=False)
                archivo.write(linea_json + '\n')
            
            # Flush periódico
            if mesas_guardadas % 50 == 0:
                archivo.flush() 
            
            mesas_guardadas += 1
            
            if mesas_guardadas % 500 == 0:
                print(f"✅ Nodo actual: {mesas_guardadas} mesas procesadas exitosamente...")
                
        else:
            # 4. LA MESA NO EXISTE (Ej. success = False o data = [])
            faltantes.write(codigo_mesa + '\n')
            faltantes.flush()
            
        time.sleep(DELAY_PETICION)

print("\n🎉 ¡EXTRACCIÓN FINALIZADA PARA ESTE NODO!")
print(f"💾 Se procesaron {mesas_guardadas} mesas válidas en {ARCHIVO_JSONL}")
print(f"📋 Las mesas no encontradas se guardaron en {ARCHIVO_FALTANTES}")
