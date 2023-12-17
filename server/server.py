import socket
import sys
from pyaudio import PyAudio, paInt32
import struct
from PyQt5 import QtWidgets, uic
import threading
import json


def getInputDevices():
    for i in range(pyaudio.get_host_api_info_by_index(0).get('deviceCount')):
        if (pyaudio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            yield pyaudio.get_device_info_by_host_api_device_index(0, i)


def getOutputDevices():
    for i in range(pyaudio.get_host_api_info_by_index(0).get('deviceCount')):
        if (pyaudio.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            yield pyaudio.get_device_info_by_host_api_device_index(0, i)


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('window.ui', self)

        self.label.setText(f"Адрес сервера: {HOST}:{PORT}")
        self.pressed_updateDevices()

        self.confirmCode.clicked.connect(self.pressed_confirmCode)
        self.confirmDevice.clicked.connect(self.pressed_confirmDevice)
        self.updateDevices.clicked.connect(self.pressed_updateDevices)

        self.streamOutput = pyaudio.open(format=paInt32, channels=1, rate=80000, output=True)
        self.codeValue = ""

        with open('settings.json', 'rb') as file:
            self.codeValue = json.load(file)['SecureCode']
            self.code.setText(self.codeValue)

        self.show()
        self.upp = None

        self.updateLoop()

    def pressed_confirmDevice(self):
        selected_device_id = int(self.DevicesComboBox.currentText().split(' ')[0])
        self.streamOutput = pyaudio.open(format=paInt32, channels=1, rate=80000, output=True,
                                         input_device_index=selected_device_id)

    def pressed_updateDevices(self):
        self.DevicesComboBox.clear()
        self.DevicesComboBox.addItems(
            list(map(lambda x: f'{x["index"]} {x["name"].encode("cp1251").decode("utf-8")}', getOutputDevices()))
        )

    def pressed_confirmCode(self):
        self.codeValue = self.code.text()
        with open('settings.json', 'w') as file:
            json.dump({'SecureCode': self.codeValue}, file)

    def closeEvent(self, a0):
        a0.accept()
        self.upp.setDaemon()

    def updateLoop(self):
        def loop():
            while True:
                conn, addr = server.accept()
                if self.codeValue.encode('utf-8') != conn.recv(*struct.unpack("I", conn.recv(4))):
                    conn.send(b'1')
                    conn.close()
                else:
                    try:
                        while True:
                            conn.send(b'0')
                            data = conn.recv(CHUNK)
                            stream.write(data)
                    except ConnectionResetError as exc:
                        pass

        self.upp = threading.Thread(target=loop)
        self.upp.start()


if __name__ == '__main__':
    HOST = socket.gethostbyname(socket.gethostname())
    PORT = 62455

    # Audio
    pyaudio = PyAudio()
    CHUNK = 2 ** 12 + 4096

    stream = pyaudio.open(format=paInt32, channels=1, rate=80000, output=True)

    server = socket.create_server((HOST, PORT))
    server.listen(1)

    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    app.exec_()
    pyaudio.terminate()