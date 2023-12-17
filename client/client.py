import json
import struct
import socket
import threading
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from pyaudio import PyAudio, paInt32
import sys

CHUNK = 2 ** 12


def getInputDevices():
    for i in range(pyaudio.get_host_api_info_by_index(0).get('deviceCount')):
        if (pyaudio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            yield pyaudio.get_device_info_by_host_api_device_index(0, i)


def getOutputDevices():
    for i in range(pyaudio.get_host_api_info_by_index(0).get('deviceCount')):
        if (pyaudio.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            yield pyaudio.get_device_info_by_host_api_device_index(0, i)


def encodeString(s):
    s = bytes(s, 'utf-8')
    return struct.pack("I%ds" % (len(s),), len(s), s)


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('window.ui', self)

        self.turnmicro.clicked.connect(self.pressed_turnmicro)
        self.confirmCode.clicked.connect(self.pressed_confirmCode)
        self.confirmDevice.clicked.connect(self.pressed_confirmDevice)
        self.updateDevices.clicked.connect(self.pressed_updateDevices)
        self.connect.clicked.connect(self.pressed_connect)

        self.streamInput = pyaudio.open(format=paInt32, channels=1, rate=16000, input=True, start=True)
        # self.streamOutput = pyaudio.open(format=paInt16, channels=1, rate=16000, output=True, start=True)

        self.pressed_updateDevices()

        self.selected_device = 0
        self.socket = None
        self.codeValue = ""
        self.microEnabled = False

        with open('settings.json', 'r') as file:
            data = json.load(file)
            self.codeValue = data['SecureCode']
            self.code.setText(self.codeValue)
            self.address.setText(data['ServerAddress'])

        self.show()
        self.upp = None

        self.updateLoop()

    def closeEvent(self, a0):
        a0.accept()
        self.upp.setDaemon()

    def pressed_turnmicro(self):
        self.microEnabled = not self.microEnabled

    def pressed_confirmCode(self):
        self.codeValue = self.code.text()
        with open('settings.json', 'r') as file:
            serverAddr = json.load(file)['ServerAddress']
        with open('settings.json', 'w') as file:
            data = {'SecureCode': self.codeValue, 'ServerAddress': serverAddr}
            json.dump(data, file)

    def pressed_confirmDevice(self):
        selected_device_id = int(self.DevicesComboBox.currentText().split(' ')[0])
        self.streamInput = pyaudio.open(format=paInt32, channels=1, rate=80000, input=True,
                                        start=self.streamInput.is_active(),
                                        input_device_index=selected_device_id)

    def pressed_updateDevices(self):
        self.DevicesComboBox.clear()
        self.DevicesComboBox.addItems(
            list(map(lambda x: f'{x["index"]} {x["name"].encode("cp1251").decode("utf-8")}', getInputDevices()))
        )

    def pressed_connect(self):
        address = self.address.text()
        with open('settings.json', 'r') as file:
            secureCode = json.load(file)['SecureCode']
        with open('settings.json', 'w') as file:
            data = {'SecureCode': secureCode, 'ServerAddress': address}
            json.dump(data, file)

        try:
            self.socket = socket.create_connection(address.split(':'))
            self.socket.send(encodeString(self.codeValue))
            if self.socket.recv(1) == b'1':
                QMessageBox.warning(self, 'Ошибка', 'Неверно введён код доступа')
            else:
                QMessageBox.about(self, "Успешно", "Поключено успешно")
        except Exception as exc:
            QMessageBox.warning(self, "Что-то пошло не так...",
                                "Неверно введён адрес, отсутствует подключение к интернету")

    def updateLoop(self):
        def sendInfo():
            while True:
                try:
                    if self.socket and self.microEnabled:
                        self.socket.send(self.streamInput.read(CHUNK))
                except Exception:
                    pass

        self.upp = threading.Thread(target=sendInfo)
        self.upp.start()


if __name__ == '__main__':
    pyaudio = PyAudio()
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    app.exec_()
    pyaudio.terminate()
