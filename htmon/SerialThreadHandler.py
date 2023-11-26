from PyQt5.QtCore import QObject, pyqtSignal
from copy import deepcopy
class SerialThreadHandler(QObject):
    """
    This class is used to handle the serial communication with the Arduino.
    Once response is received, it emits a signal (in a thread), which can be detected by the main thread.
    """
    received = pyqtSignal()
    def __init__(self, parent = None):
        super().__init__(parent = parent)
        self.status = "idle"
    def ListenForRepsonce(self, serial):
        self.status = "measuring"
        serial.write(b'r')
        self.newlines = serial.readlines()
        self.status = "received"
        self.received.emit()
    def GetStatus(self):
        return self.status
    def GetResponce(self):
        responce = deepcopy(self.newlines)
        self.newlines = []
        self.status = "idle"
        return responce