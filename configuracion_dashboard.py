import json
import paramiko
import time
import io

KEY_PATH = 'labsuser.pem'
SSH_USER = 'ubuntu'

def ejecutar_comando(ssh, rol, descripcion, comando, ignorar_errores=False):
    """Ejecuta un comando SSH e imprime el resultado."""
    print(f"  [{rol}] {descripcion}...")
    stdin, stdout, stderr = ssh.exec_command(comando)
    exit_status = stdout.channel.recv_exit_status()
    salida = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    if exit_status != 0 and not ignorar_errores:
        print(f"  ❌ Error en '{descripcion}':\n     {error}")
    return salida

def subir_texto(ssh, contenido, ruta_remota):
    """Sube un string de texto directamente a una ruta remota."""
    sftp = ssh.open_sftp()
    archivo_memoria = io.BytesIO(contenido.encode('utf-8'))
    sftp.putfo(archivo_memoria, ruta_remota)
    sftp.close()

def conectar_con_reintentos(ip, reintentos=6, espera=15):
    """Intenta conectarse por SSH con varios reintentos."""
    llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(reintentos):
        try:
            ssh.connect(hostname=ip, username=SSH_USER, pkey=llave, timeout=20)
            return ssh
        except Exception as e:
            print(f"  ⏳ Reintentando conexión ({i+1}/{reintentos}) en {espera}s... ({e})")
            time.sleep(espera)
    raise Exception(f"No se pudo conectar a {ip} después de {reintentos} intentos.")

# =============================================
#  FASE 1: CONFIGURAR LA BASE DE DATOS (PostgreSQL)
# =============================================
def configurar_base_datos(ip_db, ip_privada_db):
    print("\n" + "=" * 50)
    print("  CONFIGURANDO MÁQUINA DE BASE DE DATOS")
    print("=" * 50)

    ssh = conectar_con_reintentos(ip_db)

    # 1. Instalar PostgreSQL
    ejecutar_comando(ssh, 'DB', 'Actualizando paquetes',
        'export DEBIAN_FRONTEND=noninteractive && sudo -E apt-get update -y')
    ejecutar_comando(ssh, 'DB', 'Instalando PostgreSQL',
        'export DEBIAN_FRONTEND=noninteractive && sudo -E apt-get install -y postgresql postgresql-contrib')

    # 2. Configurar acceso remoto desde la red interna de AWS
    ejecutar_comando(ssh, 'DB', 'Permitiendo conexiones remotas (listen_addresses)',
        "sudo sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/g\" /etc/postgresql/*/main/postgresql.conf")
    ejecutar_comando(ssh, 'DB', 'Añadiendo regla de acceso en pg_hba.conf',
        "echo 'host all all 172.31.0.0/16 md5' | sudo tee -a /etc/postgresql/*/main/pg_hba.conf")

    # 3. Crear el usuario y la base de datos
    ejecutar_comando(ssh, 'DB', "Creando usuario 'admin' en PostgreSQL",
        "sudo -u postgres psql -c \"CREATE USER admin WITH PASSWORD 'admin123';\"", ignorar_errores=True)
    ejecutar_comando(ssh, 'DB', "Creando base de datos 'elecciones'",
        "sudo -u postgres psql -c \"CREATE DATABASE elecciones OWNER admin;\"", ignorar_errores=True)

    # 4. Crear las tablas para los resultados de cada Job
    print("  [DB] Creando tablas para los resultados de MapReduce...")
    sql_crear_tablas = """
    sudo -u postgres psql -d elecciones -c "
        CREATE TABLE IF NOT EXISTS resultado_nacional (
            id_eleccion TEXT,
            id_ambito   TEXT,
            partido     TEXT,
            votos       BIGINT,
            PRIMARY KEY (id_eleccion, id_ambito, partido)
        );
        CREATE TABLE IF NOT EXISTS resultado_regional (
            id_eleccion   TEXT,
            id_ambito     TEXT,
            departamento  TEXT,
            partido       TEXT,
            votos         BIGINT,
            PRIMARY KEY (id_eleccion, id_ambito, departamento, partido)
        );
        CREATE TABLE IF NOT EXISTS resultado_provincias (
            id_eleccion TEXT,
            provincia   TEXT,
            actas_n     BIGINT,
            total_actas BIGINT,
            PRIMARY KEY (id_eleccion, provincia)
        );
        CREATE TABLE IF NOT EXISTS resultado_metricas (
            id_eleccion   TEXT,
            provincia     TEXT,
            total_electores   BIGINT,
            total_asistentes  BIGINT,
            total_validos     BIGINT,
            PRIMARY KEY (id_eleccion, provincia)
        );
    "
    """
    ejecutar_comando(ssh, 'DB', 'Creando esquema de tablas', sql_crear_tablas, ignorar_errores=True)

    # 5. Reiniciar PostgreSQL para aplicar cambios
    ejecutar_comando(ssh, 'DB', 'Reiniciando PostgreSQL',
        'sudo systemctl restart postgresql')

    # 6. Verificar que el servicio está activo
    estado = ejecutar_comando(ssh, 'DB', 'Verificando servicio',
        'sudo systemctl is-active postgresql')
    print(f"  [DB] PostgreSQL: {estado.upper()}")

    ssh.close()
    print("  ✅ Base de datos configurada correctamente.")


# =============================================
#  FASE 2: CONFIGURAR EL SERVIDOR WEB (FastAPI)
# =============================================
def configurar_servidor_web(ip_web, ip_privada_db):
    print("\n" + "=" * 50)
    print("  CONFIGURANDO SERVIDOR WEB (FastAPI)")
    print("=" * 50)

    ssh = conectar_con_reintentos(ip_web)

    # 1. Instalar Python y dependencias del sistema
    ejecutar_comando(ssh, 'WEB', 'Actualizando paquetes',
        'export DEBIAN_FRONTEND=noninteractive && sudo -E apt-get update -y')
    ejecutar_comando(ssh, 'WEB', 'Instalando Python3, pip y venv',
        'export DEBIAN_FRONTEND=noninteractive && sudo -E apt-get install -y python3 python3-pip python3-venv wget')

    # 2. Crear el entorno virtual e instalar dependencias Python
    ejecutar_comando(ssh, 'WEB', 'Creando entorno virtual en /home/ubuntu/venv',
        'python3 -m venv /home/ubuntu/venv')
    ejecutar_comando(ssh, 'WEB', 'Instalando FastAPI, Uvicorn y psycopg2',
        '/home/ubuntu/venv/bin/pip install fastapi uvicorn psycopg2-binary')

    # 3. Descargar el código de la API y el dashboard
    ejecutar_comando(ssh, 'WEB', 'Descargando main.py (API)',
        'wget -q https://gist.githubusercontent.com/dnda14/0579a85aff94147a2b3ae0aa3433cdc3/raw/e7c3eb83188115906ebcbb6f93b4684a4bad58d3/main.py -O /home/ubuntu/main.py')
    ejecutar_comando(ssh, 'WEB', 'Descargando dashboard.html',
        'wget -q https://gist.githubusercontent.com/dnda14/14847dfef5a5bdfcd3c1879a2ae6c3f5/raw/c0de8d57597eb7109231b236e27ee5c32f44a448/dashboard.html -O /home/ubuntu/dashboard.html')

    # 4. Inyectar la IP privada de la BD como variable de entorno persistente
    ejecutar_comando(ssh, 'WEB', f'Configurando DB_IP={ip_privada_db} en .bashrc',
        f'echo \'export DB_IP="{ip_privada_db}"\' >> /home/ubuntu/.bashrc')
    ejecutar_comando(ssh, 'WEB', 'Escribiendo DB_IP en /etc/environment (global)',
        f'echo \'DB_IP="{ip_privada_db}"\' | sudo tee -a /etc/environment')

    # 5. Crear el servicio systemd para que la API arranque sola al reiniciar
    servicio_systemd = f"""[Unit]
Description=FastAPI - Dashboard ONPE
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="DB_IP={ip_privada_db}"
ExecStart=/home/ubuntu/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    subir_texto(ssh, servicio_systemd, '/tmp/fastapi-onpe.service')
    ejecutar_comando(ssh, 'WEB', 'Instalando servicio systemd para FastAPI',
        'sudo mv /tmp/fastapi-onpe.service /etc/systemd/system/fastapi-onpe.service')
    ejecutar_comando(ssh, 'WEB', 'Habilitando e iniciando el servicio',
        'sudo systemctl daemon-reload && sudo systemctl enable fastapi-onpe && sudo systemctl start fastapi-onpe')

    # 6. Verificar que la API está corriendo
    time.sleep(3)
    estado = ejecutar_comando(ssh, 'WEB', 'Verificando servicio FastAPI',
        'sudo systemctl is-active fastapi-onpe')
    print(f"  [WEB] FastAPI: {estado.upper()}")

    ssh.close()
    print("  ✅ Servidor web configurado correctamente.")


# =============================================
#  FLUJO PRINCIPAL
# =============================================
def configurar_dashboard():
    print("Leyendo IPs del dashboard...")
    try:
        with open('dashboard_ips.json', 'r') as f:
            ips = json.load(f)
    except FileNotFoundError:
        print("❌ Error: No se encontró 'dashboard_ips.json'.")
        print("   Ejecuta primero: python3 levantar_dashboard.py")
        return

    ip_web_publica   = ips['web']['ip_publica']
    ip_db_publica    = ips['db']['ip_publica']
    ip_db_privada    = ips['db']['ip_privada']

    print(f"  🌐 Servidor Web : {ip_web_publica}")
    print(f"  🗄️  Base de Datos: {ip_db_publica} (interna: {ip_db_privada})")

    configurar_base_datos(ip_db_publica, ip_db_privada)
    configurar_servidor_web(ip_web_publica, ip_db_privada)

    print("\n" + "=" * 50)
    print("  ¡CONFIGURACIÓN COMPLETA!")
    print("=" * 50)
    print(f"\n  🚀 Tu API ya está disponible en:")
    print(f"     http://{ip_web_publica}:8000")
    print(f"\n  📊 Dashboard en:")
    print(f"     http://{ip_web_publica}:8000/dashboard")

if __name__ == '__main__':
    configurar_dashboard()
