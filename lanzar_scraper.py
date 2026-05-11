import json
import paramiko
import time
import sys

KEY_PATH = 'labsuser.pem'
# 88064 (rango 1) + 5001 (rango 2) = 93065 tareas exactas
TOTAL_TAREAS = 93065  
SCRIPT_NAME = 'scraper_distribuido.py'
SSH_USER = 'ubuntu'

def lanzar_scraping():
    print("Leyendo configuración del clúster...")
    try:
        with open('cluster_ips.json', 'r') as f:
            ips = json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró 'cluster_ips.json'.")
        return

    maquinas = [ips['master']['ip_publica']] + [e['ip_publica'] for e in ips['esclavos']]
    num_nodos = len(maquinas)
    
    # Dividimos la cantidad total de elementos de la lista entre los nodos
    chunk_size = TOTAL_TAREAS // num_nodos
    
    llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)

    for i, ip in enumerate(maquinas):
        # Calculamos los ÍNDICES de la lista que le tocará a cada nodo
        inicio_idx = i * chunk_size
        fin_idx = (i + 1) * chunk_size if i != (num_nodos - 1) else TOTAL_TAREAS
        
        rol = "Master" if i == 0 else f"Esclavo-{i}"
        print(f"\n[ {rol} ] Configurando {ip} | Índices asignados: {inicio_idx} a {fin_idx}")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username=SSH_USER, pkey=llave, timeout=15)
            
            print(f"  Subiendo {SCRIPT_NAME}...")
            sftp = ssh.open_sftp()
            sftp.put(SCRIPT_NAME, f'/home/ubuntu/{SCRIPT_NAME}')
            sftp.close()
            
            print(f"  Instalando dependencias...")
            cmd_deps = "export DEBIAN_FRONTEND=noninteractive && sudo -E apt-get update -y > /dev/null && sudo -E apt-get install python3-pip -y > /dev/null && pip3 install requests > /dev/null"
            ssh.exec_command(cmd_deps)
            
            print(f"  Lanzando scraper en segundo plano...")
            log_file = f"scraper_idx_{inicio_idx}_a_{fin_idx}.log"
            
            # Lanzamos el script pasándole los índices, no los códigos de mesa
            comando = f"nohup python3 {SCRIPT_NAME} {inicio_idx} {fin_idx} > {log_file} 2>&1 &"
            ssh.exec_command(comando)
            
            print(f"  Nodo {i} en marcha. Log: {log_file}")
            ssh.close()
            
        except Exception as e:
            print(f"  Error conectando a {ip}: {e}")

if __name__ == '__main__':
    lanzar_scraping()
    print("\nTodos los nodos han sido orquestados.")
