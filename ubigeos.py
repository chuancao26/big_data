import requests
import json
import time

# --- CONFIGURACIÓN ---
BASE_URL = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/ubigeos"
ID_ELECCION = 10
ARCHIVO_SALIDA = "diccionario_ubigeos.json"

# 1. TUS CABECERAS EXACTAS DEL SCRAPER DISTRIBUIDO
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

session = requests.Session()
session.headers.update(HEADERS)

diccionario_maestro = {}

def calentar_sesion():
    """Hace una petición a la página principal para obtener cookies de enrutamiento (AWS/Cloudflare)"""
    print("🔥 Calentando sesión y obteniendo cookies...")
    try:
        session.get("https://resultadoelectoral.onpe.gob.pe/", timeout=10)
        time.sleep(1)
    except:
        pass

def obtener_datos_api(endpoint, params):
    try:
        response = session.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success'):
                    return data.get('data', [])
            except ValueError:
                # Si falla, imprimimos los primeros 100 caracteres de la respuesta para ver qué nos está enviando la ONPE
                print(f"❌ La API no devolvió JSON para {endpoint}. Respuesta real del servidor:")
                print(f"--- INICIO RESPUESTA ---\n{response.text[:100]}...\n--- FIN RESPUESTA ---")
        else:
             print(f"Error HTTP {response.status_code} al consultar {endpoint}")
             
    except Exception as e:
        print(f"Error de red consultando {endpoint}: {e}")
    return []

def explorar_ubigeos():
    calentar_sesion()
    
    print("🌍 Iniciando exploración del árbol geográfico de la ONPE...")
    
    for ambito in [1, 2]:
        nombre_ambito = "PERÚ" if ambito == 1 else "EXTRANJERO"
        print(f"\n📍 Explorando Ámbito: {nombre_ambito}")
        
        params_dept = {"idEleccion": ID_ELECCION, "idAmbitoGeografico": ambito}
        departamentos = obtener_datos_api("departamentos", params_dept)
        
        if not departamentos:
            print("⚠️ No se obtuvieron departamentos. Abortando exploración de este ámbito.")
            continue
            
        for dept in departamentos:
            id_dept = dept['ubigeo']
            nom_dept = dept['nombre']
            
            params_prov = {
                "idEleccion": ID_ELECCION, 
                "idAmbitoGeografico": ambito,
                "idUbigeoDepartamento": id_dept
            }
            provincias = obtener_datos_api("provincias", params_prov)
            
            for prov in provincias:
                id_prov = prov['ubigeo']
                nom_prov = prov['nombre']
                
                params_dist = {
                    "idEleccion": ID_ELECCION, 
                    "idAmbitoGeografico": ambito,
                    "idUbigeoDepartamento": id_dept,
                    "idUbigeoProvincia": id_prov
                }
                distritos = obtener_datos_api("distritos", params_dist)
                
                for dist in distritos:
                    id_final = dist['ubigeo']
                    nom_dist = dist['nombre']
                    
                    ruta_completa = f"{nom_dept} - {nom_prov} - {nom_dist}"
                    
                    diccionario_maestro[id_final] = {
                        "ambito": nombre_ambito,
                        "departamento": nom_dept,
                        "provincia": nom_prov,
                        "distrito": nom_dist,
                        "ruta_completa": ruta_completa
                    }
                
                time.sleep(0.1) 
            
            print(f"   ✅ Mapeado: {nom_dept}")

    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(diccionario_maestro, f, ensure_ascii=False, indent=4)
        
    print(f"\n🎉 ¡Extracción completada! Se mapearon {len(diccionario_maestro)} distritos en '{ARCHIVO_SALIDA}'")

if __name__ == '__main__':
    explorar_ubigeos()
