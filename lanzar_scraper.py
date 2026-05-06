import json
import paramiko
import time
import sys

KEY_PATH = 'labsuser.pem'
TOTAL_ACTAS = 91000  
SCRIPT_NAME = 'scraper_distribuido.py'
SSH_USER = 'ubuntu'

def lanzar_scraping():
    print(" Leyendo configuración del clúster...")
    try:
        with open('cluster_ips.json', 'r') as f:
            ips = json.load(f)
    except FileNotFoundError:
        print(" Error: No se encontró 'cluster_ips.json'.")
        return

    maquinas = [ips['master']['ip_publica']] + [e['ip_publica'] for e in ips['esclavos']]
    num_nodos = len(maquinas)
    
    # Calculamos el tamaño del bloque (aprox 16,000 por máquina)
    chunk_size = TOTAL_ACTAS // num_nodos
    
    llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)

    for i, ip in enumerate(maquinas):
        inicio = (i * chunk_size) + 1
        fin = (i + 1) * chunk_size if i != (num_nodos - 1) else TOTAL_ACTAS
        
        rol = "Master" if i == 0 else f"Esclavo-{i}"
        print(f"\n [ {rol} ] Configurando {ip} | Rango: {inicio} a {fin}")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username=SSH_USER, pkey=llave, timeout=15)
            
            # 1. Subir el script de scraping
            print(f"    Subiendo {SCRIPT_NAME}...")
            sftp = ssh.open_sftp()
            sftp.put(SCRIPT_NAME, f'/home/ubuntu/{SCRIPT_NAME}')
            sftp.close()
            
            # 2. Instalar dependencias (Sin bloqueos de terminal)
            print(f"    Instalando dependencias...")
            # Usamos -E y DEBIAN_FRONTEND para evitar prompts interactivos
            cmd_deps = "export DEBIAN_FRONTEND=noninteractive && sudo -E apt-get update -y > /dev/null && sudo -E apt-get install python3-pip -y > /dev/null && pip3 install requests > /dev/null"
            ssh.exec_command(cmd_deps)
            
            # 3. Lanzar el proceso en segundo plano con nohup
            print(f"    Lanzando scraper en segundo plano...")
            log_file = f"scraper_{inicio}_{fin}.log"
            comando = f"nohup python3 {SCRIPT_NAME} {inicio} {fin} > {log_file} 2>&1 &"
            ssh.exec_command(comando)
            
            print(f"    Nodo {i} en marcha. Log: {log_file}")
            ssh.close()
            
        except Exception as e:
            print(f"    Error conectando a {ip}: {e}")

if __name__ == '__main__':
    lanzar_scraping()
    print("\n Todos los nodos han sido orquestados.")
