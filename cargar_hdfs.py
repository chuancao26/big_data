import json
import paramiko
import concurrent.futures

KEY_PATH = 'labsuser.pem'
SSH_USER = 'ubuntu'

def subir_a_hdfs(ip, i):
    rol = "Master" if i == 0 else f"Esclavo-{i}"
    try:
        llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username=SSH_USER, pkey=llave, timeout=15)
        
        # El comando que empuja los TSV locales al HDFS
        comando_hdfs = "/home/ubuntu/hadoop/bin/hdfs dfs -put /home/ubuntu/*.tsv /onpe_input/"
        print(f"[{rol}] Subiendo TSVs al HDFS...")
        stdin, stdout, stderr = ssh.exec_command(comando_hdfs)
        
        # Esperamos a que termine de subir
        errores = stderr.read().decode('utf-8').strip()
        
        # hdfs dfs -put lanza advertencias si el archivo ya existe, lo filtramos
        if errores and "File exists" not in errores:
            return f"[{rol}] ⚠️ Advertencia/Error: {errores}"
        
        ssh.close()
        return f"[{rol}] TSVs subidos exitosamente al HDFS."
        
    except Exception as e:
        return f"[{rol}] Error: {str(e)}"

def orquestar_carga():
    with open('cluster_ips.json', 'r') as f:
        ips = json.load(f)

    maquinas = [ips['master']['ip_publica']] + [e['ip_publica'] for e in ips['esclavos']]
    
    print("\nIniciando carga distribuida al HDFS")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(maquinas)) as executor:
        tareas = [executor.submit(subir_a_hdfs, ip, i) for i, ip in enumerate(maquinas)]
        
        for futuro in concurrent.futures.as_completed(tareas):
            print(futuro.result())

    print("\n ¡Listo todo en HDFS!")

if __name__ == '__main__':
    orquestar_carga()

