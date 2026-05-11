import boto3

REGION = 'us-east-1'

def prender_instancias():
    print("🔍 Buscando las instancias apagadas del clúster Hadoop...")
    ec2_resource = boto3.resource('ec2', region_name=REGION)

    # Buscamos las máquinas de nuestro proyecto que estén detenidas (stopped)
    filtros = [
        {'Name': 'tag:Proyecto', 'Values': ['Hadoop']},
        {'Name': 'instance-state-name', 'Values': ['stopped']}
    ]

    instancias_a_prender = list(ec2_resource.instances.filter(Filters=filtros))

    if not instancias_a_prender:
        print("❌ No se encontraron instancias apagadas. ¡Quizás ya están encendidas!")
        return

    ids = [instancia.id for instancia in instancias_a_prender]
    print(f"⚡ Se encontraron {len(ids)} instancias apagadas. Iniciando encendido...")

    # Usamos .start() para encenderlas
    ec2_resource.instances.filter(InstanceIds=ids).start()

    print("⏳ Esperando a que las máquinas arranquen (esto toma unos segundos)...")
    
    for instancia in instancias_a_prender:
        instancia.wait_until_running()
        print(f"✅ Instancia {instancia.id} encendida y operativa.")

    print("\n🎉 ¡Todas las máquinas están encendidas!")

if __name__ == '__main__':
    prender_instancias()
