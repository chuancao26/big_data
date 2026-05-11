import boto3

REGION = 'us-east-1'

def apagar_instancias():
    print("🔍 Buscando las instancias del clúster Hadoop...")
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    # Buscamos las máquinas que tengan nuestra etiqueta y que estén encendidas
    filtros = [
        {'Name': 'tag:Proyecto', 'Values': ['Hadoop']},
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]

    instancias_a_apagar = list(ec2_resource.instances.filter(Filters=filtros))

    if not instancias_a_apagar:
        print("No se encontraron instancias encendidas. ¡Parece que ya están apagadas!")
        return

    ids = [instancia.id for instancia in instancias_a_apagar]
    print(f"⚡ Se encontraron {len(ids)} instancias encendidas. Iniciando apagado...")

    # Usamos .stop() para detenerlas (NO .terminate() que las borraría)
    ec2_resource.instances.filter(InstanceIds=ids).stop()

    print("⏳ Esperando a que las máquinas se apaguen por completo (esto toma aproximadamente 1 minuto)...")
    
    # El script se pausa aquí hasta confirmar que AWS las apagó físicamente
    for instancia in instancias_a_apagar:
        instancia.wait_until_stopped()
        print(f"✅ Instancia {instancia.id} apagada de forma segura.")

    print("\n🎉 ¡Todas las máquinas están detenidas de forma segura!")
    print("Tus datos en HDFS y tus TSVs están a salvo en los discos. Puedes cerrar Vocareum tranquilo.")

if __name__ == '__main__':
    apagar_instancias()
