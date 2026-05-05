# 🚀 Clúster Efímero de Hadoop en AWS (Vocareum)

Este proyecto automatiza la creación, configuración y destrucción de un clúster distribuido de Apache Hadoop (1 Nodo Master, 3 Nodos Esclavos) utilizando instancias EC2 en AWS Academy. Está diseñado con Python (`boto3` y `paramiko`) para optimizar recursos en sesiones de laboratorio efímeras, permitiendo levantar y apagar la infraestructura en cuestión de minutos.

---

## 🛠️ Requisitos Previos

1. **Cuenta de AWS Academy (Vocareum):** Sesión de laboratorio activa.
2. **Python 3.x:** Instalado en tu máquina local.
3. **Llave SSH:** Archivo `labsuser.pem` (o `vockey.pem`) descargado desde el panel de Vocareum.

---

## 📂 Estructura del Proyecto

| Archivo | Descripción |
|---|---|
| `levantar_aws.py` | Despliega el Security Group y las instancias EC2 (`t2.medium`), asignándoles etiquetas para identificar Master y Esclavos. |
| `configurar_hadoop.py` | Se conecta vía SSH, instala Java 8, descarga Hadoop 3.3.6, inyecta archivos XML dinámicos y configura la red interna sin contraseñas. |
| `destruir_aws.py` | Termina las instancias y borra el Security Group para no consumir créditos innecesarios. |

---

## 🚀 Guía de Uso Paso a Paso

### Fase 1: Preparación del Entorno Local

**1. Clona el repositorio y entra a la carpeta del proyecto.**

**2. Crea y activa un entorno virtual de Python:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Instala las dependencias necesarias:**
```bash
pip install boto3 paramiko
```

**4. Pega tus credenciales temporales de AWS CLI en la terminal:**
```bash
export AWS_ACCESS_KEY_ID="TU_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="TU_SECRET_KEY"
export AWS_SESSION_TOKEN="TU_SESSION_TOKEN"
```

**5. Coloca tu llave `labsuser.pem` en la raíz del proyecto y asígnale los permisos de seguridad adecuados:**
```bash
chmod 400 labsuser.pem
```

---

### Fase 2: Levantar la Infraestructura

Ejecuta el script de creación. Este proceso solicitará 4 máquinas a AWS, configurará la red y guardará las direcciones en un archivo local.

```bash
python3 levantar_aws.py
```

> 📌 **Resultado esperado:** Se generará un archivo `cluster_ips.json` con las IPs públicas y privadas del clúster.

---

### Fase 3: Configurar Apache Hadoop

Una vez que las máquinas estén corriendo, ejecuta el script de configuración. Este paso toma alrededor de 3–5 minutos mientras se descarga e instala el software en los 4 nodos simultáneamente.

```bash
python3 configurar_hadoop.py
```

> 📌 **Resultado esperado:** El sistema de archivos HDFS será formateado y los demonios de YARN se iniciarán automáticamente.

---

### Fase 4: Probar el Clúster

Conéctate por SSH al nodo Master utilizando la IP pública generada (disponible en `cluster_ips.json` o en la salida de la terminal):

```bash
ssh -i labsuser.pem ubuntu@<IP_PUBLICA_DEL_MASTER>
```

Una vez dentro del Master, ejecuta un trabajo de MapReduce de prueba (cálculo de Pi) para verificar el procesamiento distribuido:

```bash
yarn jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 10 1000
```

---

### Fase 5: Destruir la Infraestructura ⚠️ IMPORTANTE

Para evitar agotar el presupuesto o tiempo de sesión en AWS Academy, asegúrate de destruir el clúster cuando termines de trabajar:

```bash
python3 destruir_aws.py
```

> 📌 **Resultado esperado:** Todas las instancias con la etiqueta `Proyecto: Hadoop` serán terminadas, el Security Group eliminado y el archivo JSON local borrado.

---

## ⚙️ Notas de Configuración (Tuning)

El código está optimizado para instancias `t2.medium` (4 GB de RAM). Si necesitas procesar datos más grandes o cambias el tipo de instancia a `t3.large`, recuerda ajustar los valores de memoria en `configurar_hadoop.py` — específicamente en las variables de entorno para `yarn_site` y `mapred_site` — para prevenir cuellos de botella.
