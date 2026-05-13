import json
import paramiko
import time
import concurrent.futures

KEY_PATH = 'labsuser.pem'
SCRIPT_ETL = 'etl_local.py'
SSH_USER = 'ubuntu'

def ejecutar_en_nodo(ip, rol, llave):
    """
    Esta función es ejecutada por cada hilo de forma independiente.
    En lugar de imprimir, retorna un diccionario con los resultados.
    """
    resultado = {
        'rol': rol,
        'ip': ip,
        'salida': '',
        'errores': '',
        'excepcion': None
    }
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, pkey=llave, timeout=15)
        
        # 1. Subir el script ETL al nodo
        sftp = ssh.open_sftp()
        sftp.put(SCRIPT_ETL, f'/home/ubuntu/{SCRIPT_ETL}')
        sftp.close()
        
        # 2. Ejecutar el script y esperar el resultado
        stdin, stdout, stderr = ssh.exec_command(f"python3 /home/ubuntu/{SCRIPT_ETL}")
        
        # Leer la salida
        resultado['salida'] = stdout.read().decode('utf-8').strip()
        resultado['errores'] = stderr.read().decode('utf-8').strip()
        
        ssh.close()
        
    except Exception as e:
        resultado['excepcion'] = str(e)
        
    return resultado

def orquestar_etl_paralelo():
    print("Leyendo configuración del clúster...")
    try:
        with open('cluster_ips.json', 'r') as f:
            ips = json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró 'cluster_ips.json'.")
        return

    # Juntamos la IP del master y las de los esclavos
    maquinas_ips = [ips['master']['ip_publica']] + [e['ip_publica'] for e in ips['esclavos']]
    llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)

    print(f"\nIniciando procesamiento ETL en paralelo en {len(maquinas_ips)} nodos...")
    inicio = time.time()

    # Usamos ThreadPoolExecutor para lanzar las tareas al mismo tiempo
    # max_workers le dice cuántos hilos abrir a la vez (uno por cada máquina)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(maquinas_ips)) as executor:
        
        # Preparamos las tareas enviando la IP, el Rol y la llave SSH a la función
        tareas = []
        for i, ip in enumerate(maquinas_ips):
            rol = "Master" if i == 0 else f"Esclavo-{i}"
            # submit() lanza el hilo en el fondo
            tareas.append(executor.submit(ejecutar_en_nodo, ip, rol, llave))
        
        # as_completed() va atrapando a los hilos en el instante en que terminan
        for futuro in concurrent.futures.as_completed(tareas):
            res = futuro.result()
            
            print(f"\n[ {res['rol']} ] ({res['ip']}) - Tarea finalizada:")
            
            if res['excepcion']:
                print(f"  Error conectando/ejecutando: {res['excepcion']}")
            else:
                if res['salida']:
                    print("   Log del nodo:\n      " + res['salida'].replace('\n', '\n      '))
                if res['errores']:
                    print("   Posibles advertencias:\n      " + res['errores'].replace('\n', '\n      '))

    fin = time.time()
    print(f"\n Proceso finalizado en todos los nodos en {fin - inicio:.2f} segundos. Archivos TSV creados.")

if __name__ == '__main__':
    orquestar_etl_paralelo()
