import boto3
import os

# Configuración base
REGION = 'us-east-1'

def destruir_infraestructura():
    print("Iniciando la destrucción del clúster de Hadoop...")
    
    ec2_client = boto3.client('ec2', region_name=REGION)
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    # ---------------------------------------------------------
    # 1. BUSCAR Y TERMINAR LAS INSTANCIAS EC2
    # ---------------------------------------------------------
    # Filtramos para asegurarnos de no borrar otras cosas de tu laboratorio por accidente
    filtros = [
        {'Name': 'tag:Proyecto', 'Values': ['Hadoop']},
        {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'stopping', 'stopped']}
    ]
    
    instancias = list(ec2_resource.instances.filter(Filters=filtros))
    
    if not instancias:
        print("No se encontraron instancias del clúster para destruir.")
    else:
        ids_instancias = [instancia.id for instancia in instancias]
        print(f"Se encontraron {len(ids_instancias)} máquinas. Enviando orden de destrucción...")
        
        # Enviamos la orden fatal
        ec2_client.terminate_instances(InstanceIds=ids_instancias)
        
        # IMPORTANTE: Debemos esperar a que estén 100% destruidas (Terminated)
        # Si intentamos borrar el Security Group mientras las máquinas se están apagando, AWS dará un error.
        print("Esperando a que las instancias se destruyan por completo (esto toma entre 1 y 3 minutos)...")
        waiter = ec2_client.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=ids_instancias)
        print("✅ Instancias terminadas y eliminadas con éxito.")

    # ---------------------------------------------------------
    # 2. ELIMINAR EL SECURITY GROUP
    # ---------------------------------------------------------
    sg_name = 'hadoop-cluster-sg'
    try:
        print(f"Buscando el Security Group '{sg_name}'...")
        sgs = ec2_client.describe_security_groups(GroupNames=[sg_name])
        sg_id = sgs['SecurityGroups'][0]['GroupId']
        
        print(f"Eliminando Security Group ({sg_id})...")
        ec2_client.delete_security_group(GroupId=sg_id)
        print("✅ Security Group eliminado.")
        
    except ec2_client.exceptions.ClientError as e:
        if 'InvalidGroup.NotFound' in str(e):
            print(f"El Security Group '{sg_name}' ya no existe.")
        else:
            print(f"⚠️ Aviso al borrar el SG (puede que lo estés usando en otro lado): {e}")

    # ---------------------------------------------------------
    # 3. LIMPIEZA LOCAL
    # ---------------------------------------------------------
    if os.path.exists('cluster_ips.json'):
        os.remove('cluster_ips.json')
        print("✅ Archivo local 'cluster_ips.json' eliminado.")

    print("\n=======================================================")
    print("¡INFRAESTRUCTURA DESTRUIDA EXITOSAMENTE!")
    print("=======================================================")

if __name__ == '__main__':
    destruir_infraestructura()
