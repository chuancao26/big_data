archivo_entrada = "credenciales"
archivo_salida = "aws_exports.sh"

try:
    with open(archivo_entrada, "r") as f_in, open(archivo_salida, "w") as f_out:
        for linea in f_in:
            linea = linea.strip()
            
            # Verificamos que la línea tenga un signo '=' para evitar errores
            if "=" in linea:
                # Separamos la clave del valor (solo en el primer '=')
                clave, valor = linea.split("=", 1)
                
                # Limpiamos espacios y quitamos comillas si ya existieran
                clave = clave.strip().upper()
                valor = valor.strip().strip('"').strip("'")
                
                # Escribimos el nuevo formato en el archivo de salida
                f_out.write(f'export {clave}="{valor}"\n')
                
    print(f"✅ Archivo '{archivo_salida}' generado con éxito.")

except FileNotFoundError:
    print("❌ Error: No se encontró el archivo 'credenciales'.")
