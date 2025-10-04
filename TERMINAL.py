import socket
import threading
import os
import zipfile

# Configuración
HOST = "0.0.0.0"
PORT = 
BUFFER_SIZE = 

LOGIN_PASSWORD =
FILE_PASSWORD =

clientes = []

def listar_archivos_servidor():
    # Lista los archivos recibidos que empiezan por "recibido_"
    files = []
    for f in os.listdir("."):
        if f.startswith("recibido_"):
            files.append(f.replace("recibido_", "", 1))
    return files

def manejar_cliente(conn, addr):
    print(f"[+] Nueva conexión desde {addr}")

    try:
        # Autenticación inicial
        conn.sendall("Ingrese la contraseña de acceso:\n".encode("utf-8"))
        password = conn.recv(BUFFER_SIZE).decode("utf-8", errors="ignore").strip()
        if password != LOGIN_PASSWORD:
            conn.sendall("Contraseña incorrecta. Conexión cerrada.\n".encode("utf-8"))
            conn.close()
            print(f"[-] {addr} rechazado por contraseña")
            return

        conn.sendall("Acceso concedido. Bienvenido.\n".encode("utf-8"))
        clientes.append(conn)
        print(f"[+] {addr} autenticado")

        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            data = data.decode("utf-8", errors="ignore").strip()
            if not data:
                continue

            # Comando para listar archivos disponibles
            if data.lower().startswith("/listfiles"):
                files = listar_archivos_servidor()
                if not files:
                    conn.sendall("No hay archivos disponibles en el servidor.\n".encode("utf-8"))
                else:
                    resp = "Archivos disponibles:\n" + "\n".join(files) + "\n"
                    conn.sendall(resp.encode("utf-8"))
                continue

            # /sendfile::name::size  (robusto)
            if data.startswith("/sendfile"):
                try:
                    partes = data.split("::")
                    if len(partes) != 3:
                        conn.sendall("Formato incorrecto. Uso: /sendfile::<archivo>::<tamaño>\n".encode("utf-8"))
                        continue
                    _, filename, filesize = partes
                    filename = os.path.basename(filename.strip())
                    filesize = int(filesize)
                except Exception:
                    conn.sendall("Error en parámetros de /sendfile.\n".encode("utf-8"))
                    continue

                ruta_guardado = "recibido_" + filename
                try:
                    with open(ruta_guardado, "wb") as f:
                        restante = filesize
                        while restante > 0:
                            chunk = conn.recv(min(BUFFER_SIZE, restante))
                            if not chunk:
                                break
                            f.write(chunk)
                            restante -= len(chunk)
                    print(f"[ARCHIVO] Recibido {filename} ({filesize} bytes) -> {ruta_guardado}")
                except Exception as e:
                    print(f"[ERROR] al guardar archivo: {e}")
                    conn.sendall("Error al guardar archivo en servidor.\n".encode("utf-8"))
                    continue

                # Si es zip, intentar extraer
                if filename.lower().endswith(".zip"):
                    try:
                        carpeta_destino = "extraido_" + filename[:-4]
                        with zipfile.ZipFile(ruta_guardado, 'r') as zip_ref:
                            zip_ref.extractall(carpeta_destino)
                        print(f"[EXTRAÍDO] {filename} → {carpeta_destino}/")
                    except Exception as e:
                        print(f"[ERROR] al extraer zip: {e}")

                # Notificar a otros clientes
                for c in clientes:
                    if c is not conn:
                        try:
                            c.sendall(f"[Servidor] Archivo {filename} recibido.\n".encode("utf-8"))
                        except:
                            pass
                continue

            # /getfile  (acepta "::" o espacios)
            if data.startswith("/getfile"):
                # intentar formato con "::"
                filename = None
                filepass = None

                if "::" in data:
                    partes = data.split("::")
                    if len(partes) >= 3:
                        filename = partes[1].strip()
                        filepass = partes[2].strip()
                else:
                    partes = data.split(" ", 2)
                    if len(partes) >= 3:
                        filename = partes[1].strip()
                        filepass = partes[2].strip()

                if not filename or not filepass:
                    conn.sendall("Uso: /getfile <archivo> <contraseña>  o /getfile::<archivo>::<contraseña>\n".encode("utf-8"))
                    continue

                # verificar contraseña (strip y case-sensitive)
                if filepass.strip() != FILE_PASSWORD:
                    conn.sendall("Contraseña de descarga incorrecta.\n".encode("utf-8"))
                    continue

                # buscar archivo en servidor (acepta "archivo" o "recibido_archivo")
                candidatos = [filename, "recibido_" + filename]
                ruta_archivo = None
                for c in candidatos:
                    if os.path.exists(c):
                        ruta_archivo = c
                        break

                if not ruta_archivo:
                    conn.sendall(f"El archivo {filename} no existe en el servidor.\n".encode("utf-8"))
                    continue

                filesize = os.path.getsize(ruta_archivo)
                # avisar al cliente
                conn.sendall(f"/fileinfo::{os.path.basename(ruta_archivo)}::{filesize}".encode("utf-8"))
                # enviar archivo
                with open(ruta_archivo, "rb") as f:
                    while True:
                        chunk = f.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                print(f"[ENVIADO] {ruta_archivo} -> {addr}")
                continue

            # Mensaje normal -> reenvío
            # (no imprimimos contraseñas ni datos sensibles)
            print(f"[{addr}] {data}")
            for c in clientes:
                if c is not conn:
                    try:
                        c.sendall(f"[{addr}] {data}\n".encode("utf-8"))
                    except:
                        pass

    except Exception as e:
        print(f"[ERROR] con {addr}: {e}")

    finally:
        try:
            if conn in clientes:
                clientes.remove(conn)
        except:
            pass
        try:
            conn.close()
        except:
            pass
        print(f"[-] Cliente desconectado: {addr}")

def iniciar_servidor():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Servidor escuchando en {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    iniciar_servidor()
