import boto3
import json
import time

REGION = 'us-east-1'
KEY_NAME = 'vockey'
IAM_PROFILE = 'LabInstanceProfile'
INSTANCE_TYPE = 't2.medium'

def crear_infraestructura():
    print("Iniciando la creación del clúster de Hadoop...")
    
    # Conectamos con el servicio EC2 de AWS
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    # 1. CREAR EL SECURITY GROUP
    sg_name = 'hadoop-cluster-sg'
    
    try:
        print(f"Creando Security Group: {sg_name}...")
        response = ec2_client.create_security_group(
            GroupName=sg_name,
            Description='SG para el cluster efimero de Hadoop'
        )
        sg_id = response['GroupId']
        
        # Regla 1: Permitir SSH (Puerto 22) desde cualquier lugar (para conectarnos nosotros)
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )

        # Regla 2: Permitir tráfico web a las interfaces de Hadoop (9870 y 8088)
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 9870, 'ToPort': 9870, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 8088, 'ToPort': 8088, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        
        # Regla 3: Permitir TODO el tráfico interno entre las máquinas de este mismo Security Group
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': '-1', 'UserIdGroupPairs': [{'GroupId': sg_id}]}
            ]
        )
        print("Security Group configurado correctamente.")
        
    except ec2_client.exceptions.ClientError as e:
        if 'InvalidGroup.Duplicate' in str(e):
            print("El Security Group ya existe. Reutilizándolo...")
            # Buscamos el ID del grupo existente
            sgs = ec2_client.describe_security_groups(GroupNames=[sg_name])
            sg_id = sgs['SecurityGroups'][0]['GroupId']
        else:
            raise e

    # 2. OBTENER  UBUNTU 22.04
    ssm_client = boto3.client('ssm', region_name=REGION)
    ami_response = ssm_client.get_parameter(
        Name='/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id'
    )
    ami_id = ami_response['Parameter']['Value']

    # 3. LANZAR LAS INSTANCIAS (6 Máquinas )
    print("Lanzando 6 instancias EC2")
    instances = ec2_resource.create_instances(
        ImageId=ami_id,
        MinCount=6,  
        MaxCount=6, 
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': IAM_PROFILE},
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
                'Tags': [{'Key': 'Proyecto', 'Value': 'Hadoop'}]
            }
        ]
    )
    # 4. ESPERAR Y ETIQUETAR
    print("Esperando a que las instancias estén en estado 'running' (esto toma un minuto)...")
    
    # Creamos un diccionario para guardar las IPs
    cluster_ips = {'master': {}, 'esclavos': []}
    
    for i, instance in enumerate(instances):
        # El "waiter" pausa el script hasta que la máquina encienda
        instance.wait_until_running()
        instance.reload() # Refresca los datos para obtener la IP generada
        
        # La primera máquina será el Master, las demás Esclavos
        rol = 'Master' if i == 0 else f'Esclavo-{i}'
        
        # Le ponemos su etiqueta individual
        instance.create_tags(Tags=[{'Key': 'Rol', 'Value': rol}])
        
        datos_instancia = {
            'id': instance.id,
            'ip_publica': instance.public_ip_address,
            'ip_privada': instance.private_ip_address
        }
        
        if i == 0:
            cluster_ips['master'] = datos_instancia
            print(f"[MASTER]  IP Pública: {instance.public_ip_address} | IP Privada: {instance.private_ip_address}")
        else:
            cluster_ips['esclavos'].append(datos_instancia)
            print(f"[ESCLAVO] IP Pública: {instance.public_ip_address} | IP Privada: {instance.private_ip_address}")

    # 5. GUARDAR LAS IPS EN UN ARCHIVO JSON
    with open('cluster_ips.json', 'w') as f:
        json.dump(cluster_ips, f, indent=4)
        
    print("\n¡Infraestructura creada con éxito!")
    print("Las IPs se han guardado en 'cluster_ips.json'.")

if __name__ == '__main__':
    crear_infraestructura()
