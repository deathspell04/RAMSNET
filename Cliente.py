import socket
import threading
import os

# Configuración
SERVER_IP = ""   # Cambia por la IP del servidor
PORT = 
BUFFER_SIZE = 
LOGIN_PASSWORD = ""   # Contraseña inicial del servidor

def enviar_mensajes(sock):
    while True:
        try:
            msg = input("> ")
            sock.sendall(msg.encode("utf-8"))
        except:
            print("Conexión cerrada.")
            break

def recibir_mensajes(sock):
    while True:
        try:
            data = sock.recv(BUFFER_SIZE).decode("utf-8", errors="ignore")
            if not data:
                break

            # Descarga de archivos
            if data.startswith("/fileinfo::"):
                _, filename, filesize = data.split("::")
                filesize = int(filesize)

                carpeta = "descargas"
                os.makedirs(carpeta, exist_ok=True)
                ruta_archivo = os.path.join(carpeta, "descargado_" + filename)

                with open(ruta_archivo, "wb") as f:
                    restante = filesize
                    while restante > 0:
                        chunk = sock.recv(min(BUFFER_SIZE, restante))
                        if not chunk:
                            break
                        f.write(chunk)
                        restante -= len(chunk)

                print(f"Archivo descargado en: {ruta_archivo}")
            else:
                print(data)
        except:
            print(" Error recibiendo datos.")
            break

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, PORT))

    prompt = sock.recv(BUFFER_SIZE).decode("utf-8")
    print(prompt, end="")
    password = input().strip()
    sock.sendall(password.encode("utf-8"))

    confirm = sock.recv(BUFFER_SIZE).decode("utf-8")
    print(confirm.strip())

    if "incorrecta" in confirm.lower():
        sock.close()
    else:
        threading.Thread(target=recibir_mensajes, args=(sock,), daemon=True).start()
        enviar_mensajes(sock)
