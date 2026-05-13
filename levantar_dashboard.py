import boto3
import json
import time

REGION = 'us-east-1'
KEY_NAME = 'vockey'
IAM_PROFILE = 'LabInstanceProfile'
INSTANCE_TYPE = 't2.micro'  # Igual que las máquinas Hadoop

# User Data para la máquina WEB (FastAPI)
USER_DATA_WEB = """#!/bin/bash
apt-get update -y
apt-get install python3-pip wget -y
pip3 install fastapi uvicorn psycopg2-binary

cd /home/ubuntu

# Descargar el código de la API y el dashboard desde GitHub
wget https://gist.githubusercontent.com/dnda14/0579a85aff94147a2b3ae0aa3433cdc3/raw/e7c3eb83188115906ebcbb6f93b4684a4bad58d3/main.py -O main.py
wget https://gist.githubusercontent.com/dnda14/14847dfef5a5bdfcd3c1879a2ae6c3f5/raw/c0de8d57597eb7109231b236e27ee5c32f44a448/dashboard.html -O dashboard.html

chown ubuntu:ubuntu main.py dashboard.html
sudo -u ubuntu nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /home/ubuntu/uvicorn.log 2>&1 &
"""

# User Data para la máquina BASE DE DATOS (PostgreSQL)
USER_DATA_DB = """#!/bin/bash
apt-get update -y
apt-get install postgresql postgresql-contrib -y

# Permitir conexiones desde la red interna de AWS (172.31.x.x)
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/*/main/postgresql.conf
echo "host all all 172.31.0.0/16 md5" >> /etc/postgresql/*/main/pg_hba.conf

# Crear usuario y base de datos
sudo -u postgres psql -c "CREATE USER admin WITH PASSWORD 'admin123';"
sudo -u postgres psql -c "CREATE DATABASE elecciones OWNER admin;"

systemctl restart postgresql
"""

def crear_sg(ec2_client, nombre, descripcion, reglas_ingress):
    """Crea un Security Group o lo reutiliza si ya existe."""
    try:
        print(f"Creando Security Group: '{nombre}'...")
        response = ec2_client.create_security_group(
            GroupName=nombre,
            Description=descripcion
        )
        sg_id = response['GroupId']
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=reglas_ingress
        )
        print(f"  ✅ '{nombre}' creado con ID: {sg_id}")
        return sg_id
    except ec2_client.exceptions.ClientError as e:
        if 'InvalidGroup.Duplicate' in str(e):
            print(f"  ⚠️ El SG '{nombre}' ya existe. Reutilizándolo...")
            sgs = ec2_client.describe_security_groups(GroupNames=[nombre])
            return sgs['SecurityGroups'][0]['GroupId']
        raise e

def lanzar_instancia(ec2_resource, ami_id, sg_id, nombre_tag, user_data):
    """Lanza una sola instancia EC2 y espera a que esté lista."""
    print(f"\nLanzando instancia: '{nombre_tag}'...")
    instances = ec2_resource.create_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': IAM_PROFILE},
        UserData=user_data,
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'VolumeSize': 15,
                    'VolumeType': 'gp2',
                    'DeleteOnTermination': True
                }
            }
        ],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': nombre_tag},
                    {'Key': 'Proyecto', 'Value': 'Dashboard-ONPE'}
                ]
            }
        ]
    )
    instance = instances[0]
    print(f"  ⏳ Esperando a que '{nombre_tag}' esté en estado 'running'...")
    try:
        instance.wait_until_running()
    except Exception as e:
        print(f"  ❌ La instancia '{nombre_tag}' terminó en estado anómalo.")
        print(f"     Causa: {e}")
        print(f"  💡 Probable causa: Límite de instancias de AWS Academy alcanzado.")
        print(f"     Espera unos minutos o termina otras instancias y vuelve a ejecutar.")
        raise
    instance.reload()
    print(f"  ✅ '{nombre_tag}' lista | IP Pública: {instance.public_ip_address} | IP Privada: {instance.private_ip_address}")
    return instance

def crear_infraestructura_dashboard():
    print("=" * 55)
    print("  Creando infraestructura del Dashboard ONPE...")
    print("=" * 55)

    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    # 1. Obtener AMI de Ubuntu 22.04
    ssm_client = boto3.client('ssm', region_name=REGION)
    ami_response = ssm_client.get_parameter(
        Name='/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id'
    )
    ami_id = ami_response['Parameter']['Value']
    print(f"\nUsando AMI Ubuntu 22.04: {ami_id}\n")

    # 2. Crear Security Groups
    sg_web_id = crear_sg(
        ec2_client,
        nombre='web-sg-dashboard-onpe',
        descripcion='SG para el servidor web FastAPI del Dashboard ONPE',
        reglas_ingress=[
            {'IpProtocol': 'tcp', 'FromPort': 22,   'ToPort': 22,   'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        ]
    )

    sg_db_id = crear_sg(
        ec2_client,
        nombre='db-sg-postgres-onpe',
        descripcion='SG para la base de datos PostgreSQL del Dashboard ONPE',
        reglas_ingress=[
            {'IpProtocol': 'tcp', 'FromPort': 22,   'ToPort': 22,   'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 5432, 'ToPort': 5432, 'IpRanges': [{'CidrIp': '172.31.0.0/16'}]},
        ]
    )

    # 3. Verificar si ya existe un dashboard_ips.json con la DB creada
    dashboard_ips = {}
    try:
        with open('dashboard_ips.json', 'r') as f:
            dashboard_ips = json.load(f)
            if 'db' in dashboard_ips:
                print(f"\n  ♻️  La Máquina-Postgres ya existe en dashboard_ips.json, reutilizando...")
                instancia_db = None
    except FileNotFoundError:
        pass

    # 4. Lanzar la BD (si no existe ya)
    if 'db' not in dashboard_ips:
        instancia_db = lanzar_instancia(ec2_resource, ami_id, sg_db_id, 'Maquina-Postgres', USER_DATA_DB)
        dashboard_ips['db'] = {
            'id': instancia_db.id,
            'ip_publica':  instancia_db.public_ip_address,
            'ip_privada':  instancia_db.private_ip_address,
        }
        # Guardamos inmediatamente para no perder la IP si la Web falla
        with open('dashboard_ips.json', 'w') as f:
            json.dump(dashboard_ips, f, indent=4)
        print(f"  💾 IP de la BD guardada en dashboard_ips.json (por seguridad)")

    ip_db_privada = dashboard_ips['db']['ip_privada']

    # 5. Lanzar la Web (si no existe ya)
    if 'web' not in dashboard_ips:
        instancia_web = lanzar_instancia(ec2_resource, ami_id, sg_web_id, 'Maquina-Web-FastAPI', USER_DATA_WEB)
        dashboard_ips['web'] = {
            'id': instancia_web.id,
            'ip_publica':  instancia_web.public_ip_address,
            'ip_privada':  instancia_web.private_ip_address,
        }
    else:
        print(f"\n  ♻️  La Máquina-Web ya existe en dashboard_ips.json, reutilizando...")

    # 6. Guardar el archivo final completo
    with open('dashboard_ips.json', 'w') as f:
        json.dump(dashboard_ips, f, indent=4)

    print("\n" + "=" * 55)
    print("  ¡Infraestructura del Dashboard lista!")
    print("=" * 55)
    print(f"\n  🌐 API FastAPI → http://{instancia_web.public_ip_address}:8000")
    print(f"  🗄️  PostgreSQL  → {instancia_db.private_ip_address}:5432")
    print(f"\n  ⚠️  Nota: Las instalaciones dentro de las máquinas")
    print(f"     corren en background. Espera ~3 minutos antes")
    print(f"     de conectarte para que todo termine de instalarse.")
    print(f"\n  IPs guardadas en: dashboard_ips.json")

if __name__ == '__main__':
    crear_infraestructura_dashboard()
