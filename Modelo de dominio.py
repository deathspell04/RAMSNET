from enum import Enum
from typing import List, Optional


# ----- ENUMS -----
class Type(Enum):
    UNKNOWN = 0
    CONNECTION = 1
    ADMIN = 2
    CMD = 3
    UPLOAD = 4
    DOWNLOAD = 5
    SCREENSHOT = 6
    SHUTDOWN = 7
    DELETE = 8


class Status(Enum):
    MISSING = 0
    OK = 1
    ERROR = 2
    WAITING = 3


class StatusBot(Enum):
    CONNECTED = 0
    DISCONNECTED = 1
    

# ----- DATATYPES -----
class Response:
    def __init__(self, status: Status, type_: Type):
        self.status = status
        self.type = type_


class Geo:
    def __init__(self, ip: str, hostname: str, city: str, region: str, country: str, loc: str):
        self.ip = ip
        self.hostname = hostname
        self.city = city
        self.region = region
        self.country = country
        self.loc = loc


# ----- CLASSES -----
class Bot:
    def __init__(self, bot_id: str, status: StatusBot, system: str, node: str, release: str,
                 version: str, machine: str, processor: str, geo: Optional[Geo] = None):
        self.bot_id = bot_id
        self.status = status
        self.system = system
        self.node = node
        self.release = release
        self.version = version
        self.machine = machine
        self.processor = processor
        self.geo = geo

    # Métodos
    def GetBots(self) -> List['Bot']:
        return []

    def GetActiveBots(self) -> List['Bot']:
        return []

    def GetBot(self, bot_id: str) -> Optional['Bot']:
        return None

    def SetConnection(self, bot: 'Bot') -> Response:
        return Response(Status.OK, Type.CONNECTION)

    def GetTasks(self, bot_id: str) -> List['Task']:
        return []

    def GetCompletedBot(self, bot_id: str) -> List['Task']:
        return []

    def GetGlobalBots(self) -> List[Geo]:
        return []


class Task:
    def __init__(self, task_id: str, type_: Type, status: Status,
                 date_start: str, date_finish: str,
                 command: Optional[str] = None,
                 file: Optional[str] = None,
                 response: Optional[str] = None):
        self.task_id = task_id
        self.type = type_
        self.status = status
        self.date_start = date_start
        self.date_finish = date_finish
        self.command = command
        self.file = file
        self.response = response

    # Métodos
    def GetTasks(self) -> List['Task']:
        return []

    def GetCompleted(self) -> List['Task']:
        return []

    def GetTask(self, task_id: str) -> Optional['Task']:
        return None

    def AddTask(self, task: 'Task') -> Response:
        return Response(Status.OK, task.type)

    def SendStreamCompletedTask(self, tasks: List['Task']) -> Response:
        return Response(Status.OK, Type.UNKNOWN)


class Chunk:
    def __init__(self, status: Status, filename: str, data: bytes):
        self.status = status
        self.filename = filename
        self.data = data

    # Métodos
    def SendFileChunk(self, chunks: List['Chunk']) -> Response:
        return Response(Status.OK, Type.UPLOAD)

    def GetFile(self, file: str) -> List['Chunk']:
        return []