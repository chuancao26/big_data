import json
import paramiko
import time

KEY_PATH = 'labsuser.pem'
SCRIPT_ETL = 'etl_local.py'
SSH_USER = 'ubuntu'

def orquestar_etl():
    print("📖 Leyendo configuración del clúster...")
    try:
        with open('cluster_ips.json', 'r') as f:
            ips = json.load(f)
    except FileNotFoundError:
        print("❌ Error: No se encontró 'cluster_ips.json'.")
        return

    # Juntamos la IP del master y las de los esclavos
    maquinas = [ips['master']['ip_publica']] + [e['ip_publica'] for e in ips['esclavos']]
    llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)

    for i, ip in enumerate(maquinas):
        rol = "Master" if i == 0 else f"Esclavo-{i}"
        print(f"\n🚀 [ {rol} ] Conectando a {ip} para iniciar ETL...")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username=SSH_USER, pkey=llave, timeout=15)
            
            # 1. Subir el script ETL al nodo
            print(f"   ⬆️ Subiendo {SCRIPT_ETL}...")
            sftp = ssh.open_sftp()
            sftp.put(SCRIPT_ETL, f'/home/ubuntu/{SCRIPT_ETL}')
            sftp.close()
            
            # 2. Ejecutar el script y esperar el resultado
            print(f"   ⚙️ Transformando datos de JSONL a TSV (esto tomará unos segundos)...")
            stdin, stdout, stderr = ssh.exec_command(f"python3 /home/ubuntu/{SCRIPT_ETL}")
            
            # Leer la salida del comando (esto hace que el script espere a que termine)
            salida = stdout.read().decode('utf-8').strip()
            errores = stderr.read().decode('utf-8').strip()
            
            if salida:
                # Imprimimos la salida con una pequeña indentación para que se vea ordenado
                print("   📄 Log del nodo:\n      " + salida.replace('\n', '\n      '))
            
            if errores:
                print("   ⚠️ Posibles advertencias:\n      " + errores.replace('\n', '\n      '))
            
            ssh.close()
            
        except Exception as e:
            print(f"   ❌ Error conectando a {ip}: {e}")

if __name__ == '__main__':
    orquestar_etl()
    print("\n🎉 ¡Todos los nodos han finalizado la transformación a TSV!")
