import boto3
import json

REGION = 'us-east-1'

def actualizar_ips():
    print("🔍 Buscando las nuevas IPs del clúster Hadoop...")
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    # Buscamos las máquinas encendidas que pertenezcan a nuestro proyecto
    filtros = [
        {'Name': 'tag:Proyecto', 'Values': ['Hadoop']},
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]

    instancias = list(ec2_resource.instances.filter(Filters=filtros))

    if not instancias:
        print("❌ No se encontraron instancias encendidas. Asegúrate de prenderlas en la consola de AWS primero.")
        return

    cluster_ips = {'master': {}, 'esclavos': []}

    for instance in instancias:
        # Extraemos el rol (Master o Esclavo) de las etiquetas
        rol = "Desconocido"
        for tag in instance.tags:
            if tag['Key'] == 'Rol':
                rol = tag['Value']
                break
        
        datos_instancia = {
            'id': instance.id,
            'ip_publica': instance.public_ip_address,
            'ip_privada': instance.private_ip_address
        }

        if rol == 'Master':
            cluster_ips['master'] = datos_instancia
            print(f"👑 [{rol}] Nueva IP Pública: {instance.public_ip_address}")
        elif rol.startswith('Esclavo'):
            cluster_ips['esclavos'].append(datos_instancia)
            print(f"🖥️ [{rol}] Nueva IP Pública: {instance.public_ip_address}")

    # Sobrescribimos el archivo antiguo con las nuevas IPs
    with open('cluster_ips.json', 'w') as f:
        json.dump(cluster_ips, f, indent=4)
        
    print("\n✅ ¡Archivo 'cluster_ips.json' actualizado con éxito!")
    print("Tus scripts de automatización ya saben a dónde conectarse.")

if __name__ == '__main__':
    actualizar_ips()
