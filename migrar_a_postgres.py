import json
import paramiko
import io

KEY_PATH = 'labsuser.pem'
SSH_USER = 'ubuntu'

# Script que se sube y ejecuta DENTRO del Master de Hadoop.
# El Master puede hablar con HDFS (localmente) y con PostgreSQL (red interna AWS).
SCRIPT_MIGRACION = '''
import subprocess
import psycopg2

DB_HOST = "{db_ip_privada}"
DB_NAME = "elecciones"
DB_USER = "admin"
DB_PASS = "admin123"
DB_PORT = 5432
HADOOP  = "/home/ubuntu/hadoop/bin/hdfs"

JOBS = {{
    "resultado_nacional":   ("/onpe/salida_nacional/part-00000",   ["id_eleccion", "id_ambito", "partido", "votos"]),
    "resultado_regional":   ("/onpe/salida_regional/part-00000",   ["id_eleccion", "id_ambito", "departamento", "partido", "votos"]),
    "resultado_provincias": ("/onpe/salida_provincias/part-00000", ["clave_provincia", "actas_n", "total_actas"]),
    "resultado_metricas":   ("/onpe/salida_metricas/part-00000",   ["clave_provincia", "total_electores", "total_asistentes", "total_validos"]),
}}

conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
cur  = conn.cursor()

for tabla, (ruta_hdfs, columnas) in JOBS.items():
    print(f"\\n--- Procesando: {{tabla}} ---")

    resultado = subprocess.run([HADOOP, "dfs", "-cat", ruta_hdfs], capture_output=True, text=True)
    if resultado.returncode != 0:
        print(f"  ERROR leyendo HDFS: {{resultado.stderr}}")
        continue

    lineas = [l for l in resultado.stdout.strip().split("\\n") if l.strip()]
    print(f"  {{len(lineas)}} filas leidas desde HDFS.")

    cur.execute(f"TRUNCATE TABLE {{tabla}};")
    cols_str     = ", ".join(columnas)
    placeholders = ", ".join(["%s"] * len(columnas))
    sql = f"INSERT INTO {{tabla}} ({{cols_str}}) VALUES ({{placeholders}}) ON CONFLICT DO NOTHING;"

    ok = err = 0
    for linea in lineas:
        partes = linea.split("\\t")
        
        # Para provincias y metricas, la primera columna es una clave compuesta
        # con formato "ELECCION | DEPARTAMENTO - PROVINCIA" que debemos separar
        if tabla in ("resultado_provincias", "resultado_metricas"):
            if len(partes) == len(columnas):
                # Primera columna ya está separada correctamente
                pass
            elif len(partes) == len(columnas) - 1:
                # La clave compuesta viene en una sola columna, la separamos
                clave_compuesta = partes[0]
                if " | " in clave_compuesta:
                    id_eleccion, lugar = clave_compuesta.split(" | ", 1)
                else:
                    id_eleccion = clave_compuesta
                    lugar = ""
                partes = [id_eleccion, lugar] + partes[1:]
        
        if len(partes) != len(columnas):
            err += 1
            continue
        try:
            cur.execute(sql, partes)
            ok += 1
        except Exception:
            err += 1

    conn.commit()
    print(f"  OK: {{ok}} filas insertadas | Errores ignorados: {{err}}")

cur.close()
conn.close()
print("\\n¡Migracion completada exitosamente!")
'''


def migrar_resultados():
    print("Leyendo IPs del cluster y del dashboard...")

    with open('cluster_ips.json', 'r') as f:
        cluster_ips = json.load(f)
    with open('dashboard_ips.json', 'r') as f:
        dashboard_ips = json.load(f)

    ip_master     = cluster_ips['master']['ip_publica']
    ip_db_privada = dashboard_ips['db']['ip_privada']
    ip_web        = dashboard_ips['web']['ip_publica']

    print(f"  Master Hadoop            : {ip_master}")
    print(f"  PostgreSQL (red interna) : {ip_db_privada}")

    # 1. Conectar al Master por SSH
    print("\nConectando al Master por SSH...")
    llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    ssh   = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip_master, username=SSH_USER, pkey=llave, timeout=20)

    # 2. Instalar psycopg2 en el Master
    print("Instalando psycopg2 en el Master (si no existe)...")
    stdin, stdout, stderr = ssh.exec_command("pip3 install psycopg2-binary -q")
    stdout.channel.recv_exit_status()

    # 3. Subir el script de migración al Master
    script_final = SCRIPT_MIGRACION.format(db_ip_privada=ip_db_privada)
    sftp = ssh.open_sftp()
    sftp.putfo(io.BytesIO(script_final.encode('utf-8')), '/home/ubuntu/migrar.py')
    sftp.close()
    print("Script 'migrar.py' subido al Master.")

    # 4. Ejecutar el script en el Master
    print("\nEjecutando migracion en el Master (puede tardar ~30s)...")
    stdin, stdout, stderr = ssh.exec_command("python3 /home/ubuntu/migrar.py")
    exit_status = stdout.channel.recv_exit_status()
    salida = stdout.read().decode('utf-8')
    errores = stderr.read().decode('utf-8')

    print(salida)
    if errores:
        print(f"Advertencias:\n{errores}")

    ssh.close()

    print("\n" + "=" * 50)
    if exit_status == 0:
        print("  Datos cargados en PostgreSQL correctamente!")
        print(f"\n  Tu API con los resultados:")
        print(f"  http://{ip_web}:8000")
    else:
        print("  La migracion termino con errores. Revisa la salida de arriba.")
    print("=" * 50)


if __name__ == '__main__':
    migrar_resultados()
