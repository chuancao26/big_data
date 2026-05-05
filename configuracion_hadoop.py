import json
import paramiko
import time
import io

# --- CONFIGURACIÓN BASE ---
KEY_PATH = 'labsuser.pem' 
SSH_USER = 'ubuntu'
HADOOP_URL = 'https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz'
HADOOP_HOME = '/home/ubuntu/hadoop'
JAVA_HOME = '/usr/lib/jvm/java-8-openjdk-amd64' # Ruta por defecto de Java 8 en Ubuntu

def ejecutar_comando(ssh, comando, ignorar_errores=False):
    stdin, stdout, stderr = ssh.exec_command(comando)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0 and not ignorar_errores:
        print(f"Error ejecutando: {comando}")
        print(stderr.read().decode())
    return stdout.read().decode()

def subir_archivo(ssh, contenido, ruta_remota):
    sftp = ssh.open_sftp()
    # Creamos un archivo temporal en memoria y lo subimos
    archivo_memoria = io.BytesIO(contenido.encode('utf-8'))
    sftp.putfo(archivo_memoria, ruta_remota)
    sftp.close()

def configurar_cluster():
    print("Leyendo IPs del cluster...")
    try:
        with open('cluster_ips.json', 'r') as f:
            ips = json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró 'cluster_ips.json'. Ejecuta la Fase 2 primero.")
        return

    master_pub = ips['master']['ip_publica']
    master_priv = ips['master']['ip_privada']
    esclavos = ips['esclavos']
    
    todas_las_maquinas = [{'ip': master_pub, 'rol': 'Master'}] + [{'ip': e['ip_publica'], 'rol': 'Esclavo'} for e in esclavos]

    # --- 1. INSTALACIÓN BASE EN TODAS LAS MÁQUINAS ---
    clientes_ssh = {}
    llave = paramiko.RSAKey.from_private_key_file(KEY_PATH)

    for maquina in todas_las_maquinas:
        ip = maquina['ip']
        print(f"\n--- Conectando a {maquina['rol']} ({ip}) ---")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Intentamos conectar (con reintentos por si la máquina recién encendió)
        for reintento in range(3):
            try:
                ssh.connect(hostname=ip, username=SSH_USER, pkey=llave)
                break
            except Exception as e:
                print(f"Reintentando conexión en 10s... ({e})")
                time.sleep(10)
        
        clientes_ssh[ip] = ssh

        print("Instalando Java 8 y descargando Hadoop (Esto tomará un par de minutos)...")
        cmds_base = f"""
        sudo apt-get update -y > /dev/null
        sudo apt-get install openjdk-8-jdk -y > /dev/null
        if [ ! -d "{HADOOP_HOME}" ]; then
            wget -q {HADOOP_URL} -O hadoop.tar.gz
            tar -xzf hadoop.tar.gz
            mv hadoop-3.3.6 {HADOOP_HOME}
            rm hadoop.tar.gz
        fi
        """
        ejecutar_comando(ssh, cmds_base)

        print("Configurando variables de entorno (.bashrc y hadoop-env.sh)...")
        vars_entorno = f"""
        echo 'export JAVA_HOME={JAVA_HOME}' >> ~/.bashrc
        echo 'export HADOOP_HOME={HADOOP_HOME}' >> ~/.bashrc
        echo 'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin' >> ~/.bashrc
        sed -i 's|# export JAVA_HOME=.*|export JAVA_HOME={JAVA_HOME}|' {HADOOP_HOME}/etc/hadoop/hadoop-env.sh
        """
        ejecutar_comando(ssh, vars_entorno)

    # --- 2. CONFIGURACIÓN DE LOS ARCHIVOS XML DE HADOOP ---
    print("\n--- Generando e inyectando archivos XML de configuración ---")
    
    core_site = f"""<?xml version="1.0"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://{master_priv}:9000</value>
    </property>
</configuration>"""

    hdfs_site = """<?xml version="1.0"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>3</value>
    </property>
</configuration>"""

    yarn_site = f"""<?xml version="1.0"?>
    <configuration>
        <property>
            <name>yarn.resourcemanager.hostname</name>
            <value>{master_priv}</value>
        </property>
        <property>
            <name>yarn.nodemanager.aux-services</name>
            <value>mapreduce_shuffle</value>
        </property>
        <!-- Configuraciones para aprovechar la RAM de t2.medium -->
        <property>
            <name>yarn.nodemanager.resource.memory-mb</name>
            <value>3072</value> <!-- Dejamos 1GB para el SO y asignamos 3GB a YARN -->
        </property>
        <property>
            <name>yarn.scheduler.maximum-allocation-mb</name>
            <value>3072</value>
        </property>
        <property>
            <name>yarn.scheduler.minimum-allocation-mb</name>
            <value>512</value>
        </property>
    </configuration>"""

    mapred_site = f"""<?xml version="1.0"?>
    <configuration>
        <property>
            <name>mapreduce.framework.name</name>
            <value>yarn</value>
        </property>
        <!-- Ajustes de memoria por tarea -->
        <property>
            <name>mapreduce.map.memory.mb</name>
            <value>1024</value>
        </property>
        <property>
            <name>mapreduce.reduce.memory.mb</name>
            <value>2048</value>
        </property>
        <property>
            <name>yarn.app.mapreduce.am.env</name>
            <value>HADOOP_MAPRED_HOME={HADOOP_HOME}</value>
        </property>
        <property>
            <name>mapreduce.map.env</name>
            <value>HADOOP_MAPRED_HOME={HADOOP_HOME}</value>
        </property>
        <property>
            <name>mapreduce.reduce.env</name>
            <value>HADOOP_MAPRED_HOME={HADOOP_HOME}</value>
        </property>
    </configuration>"""
    # Crear lista de workers para el Master
    workers_list = "\n".join([e['ip_privada'] for e in esclavos])

    # Enviar los archivos a TODAS las máquinas
    for ip, ssh in clientes_ssh.items():
        base_xml_path = f"{HADOOP_HOME}/etc/hadoop/"
        subir_archivo(ssh, core_site, base_xml_path + 'core-site.xml')
        subir_archivo(ssh, hdfs_site, base_xml_path + 'hdfs-site.xml')
        subir_archivo(ssh, yarn_site, base_xml_path + 'yarn-site.xml')
        subir_archivo(ssh, mapred_site, base_xml_path + 'mapred-site.xml')
        subir_archivo(ssh, workers_list, base_xml_path + 'workers')

    # --- 3. EL PUENTE SSH (MASTER -> ESCLAVOS) ---
    print("\n--- Configurando SSH sin contraseña desde el Master a los Esclavos ---")
    ssh_master = clientes_ssh[master_pub]
    
    # Generar llave pública en el Master usando el algoritmo ed25519
    ejecutar_comando(ssh_master, 'ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519', ignorar_errores=True)
    llave_pub_master = ejecutar_comando(ssh_master, 'cat ~/.ssh/id_ed25519.pub')

    # Copiar la llave a todos los nodos (incluido el mismo Master)
    # y desactivar la validación estricta de host para evitar el prompt (yes/no)
    for ip, ssh in clientes_ssh.items():
        subir_archivo(ssh, llave_pub_master, '/tmp/master_key.pub')
        ejecutar_comando(ssh, 'cat /tmp/master_key.pub >> ~/.ssh/authorized_keys')
        ejecutar_comando(ssh, 'echo "StrictHostKeyChecking no" >> ~/.ssh/config')
        ejecutar_comando(ssh, 'chmod 600 ~/.ssh/config')

    # --- 4. FORMATEO Y ARRANQUE (SÓLO EN EL MASTER) ---
    print("\n--- Iniciando el Clúster de Hadoop ---")
    print("Formateando el NameNode...")
    ejecutar_comando(ssh_master, f'source ~/.bashrc && {HADOOP_HOME}/bin/hdfs namenode -format -force')
    
    print("Levantando servicios DFS y YARN...")
    ejecutar_comando(ssh_master, f'source ~/.bashrc && {HADOOP_HOME}/sbin/start-dfs.sh')
    ejecutar_comando(ssh_master, f'source ~/.bashrc && {HADOOP_HOME}/sbin/start-yarn.sh')

    # Cerrar conexiones
    for ssh in clientes_ssh.values():
        ssh.close()

    print("\n=======================================================")
    print("¡CLÚSTER CONFIGURADO Y CORRIENDO EXITOSAMENTE!")
    print(f"IP Pública del Master para que te conectes: {master_pub}")
    print("Para ver el estado, conéctate por SSH al master y ejecuta: jps")
    print("=======================================================")

if __name__ == '__main__':
    configurar_cluster()
