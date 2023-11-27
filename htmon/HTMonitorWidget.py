from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QGridLayout, 
    QMessageBox, QFileDialog, QDateTimeEdit, QTableWidgetItem, QTableWidget
)
import os, sys 
import re
import numpy as np
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QDateTime
import serial
import threading
from time import time
from copy import copy 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class PlotWidget(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=6, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_axes([0.12, 0.12, 0.85, 0.85])
        self.axes.xaxis.set_tick_params(labelsize=8)
        self.axes.yaxis.set_tick_params(labelsize=8)
        self.xlabel=None
        self.ylabel=None
        super(PlotWidget, self).__init__(fig)
    def SetXYLabels(self, xlabel=None, ylabel=None):
        if not xlabel is None:self.xlabel = xlabel
        if not ylabel is None:self.ylabel = ylabel
        self.axes.set_xlabel(self.xlabel, fontsize=9)
        self.axes.set_ylabel(self.ylabel, fontsize=9)


from htmon.ManualEventWidget import ManualEventWidget
from htmon.SerialThreadHandler import SerialThreadHandler
from htmon.DummySerial import DummySerial

class HTMonitorWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.timer=None
        self.sensor_data = {}
        self.manual_events = None 
        self.outfiles = {}
        self.outdir = None
        self.lines_written = {}
        self.serial_thread_handler = SerialThreadHandler(self)
        self.serial_thread_handler.received.connect(self.UpdateData)
        self.setWindowTitle("Humidity/Temperature Monitor")
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.CreateSerialControls() ) 
        self.layout.addLayout(self.CreatePlots() )
        self.layout.addLayout(self.CreateControls() )
        self.setLayout(self.layout)
        self.SetRegExp()
        self.connected = False
        self.active= False
        self.serial = None
        self.manualEventsWidget = ManualEventWidget(self)
        self.manualEventsWidget.events_updated.connect(self.GetEventList)
        self.autosave_timer = None
    def CreateSerialControls(self):
        self.label_addr = QLabel("Serial device:")
        self.input_addr = QLineEdit('/dev/ttyACM0')
        self.label_baud = QLabel("Baud rate:")
        self.input_baud = QLineEdit('115200')
        self.input_baud.setValidator(QIntValidator())
        self.input_baud.setFixedWidth(100)
        

        self.button_connect = QPushButton("Connect")
        self.button_connect.clicked.connect(self.Connect)
        self.button_disconnect = QPushButton("Disconnect")
        self.button_disconnect.clicked.connect(self.Disconnect)
        self.button_disconnect.setEnabled(False)
        self.input_addr.returnPressed.connect(self.Connect)
        self.input_baud.returnPressed.connect(self.Connect)
        self.setup_layout = QHBoxLayout()
        self.setup_layout.addWidget(self.label_addr)
        self.setup_layout.addWidget(self.input_addr)
        self.setup_layout.addWidget(self.label_baud)
        self.setup_layout.addWidget(self.input_baud)
        self.setup_layout.addWidget(self.button_connect)
        self.setup_layout.addWidget(self.button_disconnect)
        return self.setup_layout
    def CreatePlots(self):
        self.plot_layout = QHBoxLayout()
        self.temperaturePlot = PlotWidget()
        self.temperaturePlot.SetXYLabels("Time", "Temperature [C]")
        self.humidityPlot = PlotWidget()
        self.humidityPlot.SetXYLabels("Time", "Relative humidity [%]")
        self.plot_layout.addWidget(self.temperaturePlot)
        self.plot_layout.addWidget(self.humidityPlot)
        return self.plot_layout
    def SetRegExp(self, regexp=None):
        if regexp is None:
            self.regexp = re.compile('(?P<sensor>[0-9]*):T=(?P<T>[0-9]*.[0-9]*)C,RH=(?P<RH>[0-9]*.[0-9]*)%', re.IGNORECASE)
        else:
            self.regexp = re.compile(regexp, re.IGNORECASE)
    def CreateControls(self):
        self.controls_layout = QGridLayout()
        layout_interval = QHBoxLayout()
        self.updIntervalLabel = QLabel("Update interval [s]:")
        self.updIntervalInput = QLineEdit('10')
        self.updIntervalInput.setValidator(QIntValidator())
        self.updIntervalInput.setFixedWidth(100)
        self.updIntervalButton = QPushButton("Set")
        self.updIntervalButton.clicked.connect(self.SetUpdateInterval)
        layout_interval.addWidget(self.updIntervalLabel)
        layout_interval.addWidget(self.updIntervalInput)
        layout_interval.addWidget(self.updIntervalButton)
        self.controls_layout.addLayout(layout_interval, 0,0)
        right_layout = QHBoxLayout()
        self.buttonUpdate = QPushButton("Update now")
        self.buttonUpdate.clicked.connect(self.RequestMeasurement)
        right_layout.addWidget(self.buttonUpdate)
        self.controls_layout.setColumnStretch( 0, 1 )
        self.controls_layout.setColumnStretch( 1, 1 )
        self.eventButton = QPushButton("Manual events")
        self.eventButton.clicked.connect(self.ShowManualEvents)
        right_layout.addWidget(self.eventButton)
        self.controls_layout.addLayout(right_layout, 0,1)

        self.fileNameLabel = QLabel("Output:")
        self.fileNameField = QLineEdit("<no file selected>")
        self.fileNameField.setEnabled(False)
        self.fileNameButton = QPushButton("Select output")
        self.fileNameButton.clicked.connect(self.SelectOutdir)
        self.writeOutputButton = QPushButton("Save now")
        self.writeOutputButton.clicked.connect(self.CloseAndOpenIntermediate)
        save_layout = QHBoxLayout()
        save_layout.addWidget(self.fileNameLabel)
        save_layout.addWidget(self.fileNameField)
        save_layout.addWidget(self.fileNameButton)
        save_layout.addWidget(self.writeOutputButton)
        self.controls_layout.addLayout(save_layout, 1,0, 1,2)
        ###
        return self.controls_layout
    def SetUpdateInterval(self):
        interval = int(self.updIntervalInput.text())
        if not self.connected:
            self.WarnUser(text = "Not connected to serial device", title = "ERROR!")
            self.updIntervalInput.setText("10")
            return
        if interval < 5:
            interval=5
            self.WarnUser(text = "Update interval is too small", title = "ERROR!")
            self.updIntervalInput.setText("5")
            return
        self.timer.setInterval(interval*1000)

    def Connect(self):
        address = self.input_addr.text()
        baud = self.input_baud.text()
        if address == "dummy":
            self.serial = DummySerial()
        elif not os.path.exists(address):
            self.WarnUser(text = "Serial device does not exist", title = "ERROR!")
            return
        else:
            try:
                self.serial = serial.Serial(address, baud, timeout = 5)
            except Exception as error:
                print("An exception occurred:", error) # An exception occurred: division by zero:
                self.button_connect.setEnabled(True)
                self.button_disconnect.setEnabled(False)
                self.WarnUser(text = "Could not connect to serial device", title = "ERROR!")
                return
        self.button_connect.setEnabled(False)
        self.button_disconnect.setEnabled(True)
        self.connected = True
        self.active = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.RequestMeasurement)
        self.timer.start(int(self.updIntervalInput.text())*1000)
        #self.update_timer = QTimer()
        #self.update_timer.timeout.connect(self.UpdateData)

    def RequestMeasurement(self):
        #print("RequestMeasurement called")
        if self.active: 
            print("WARNING: UpdateData called while active")
            return 
        if not self.connected: 
            print("WARNING: UpdateData called while not connected")
            return
        if not self.serial_thread_handler.GetStatus() == "idle":
            print("WARNING: UpdateData called while serial thread is busy")
            return
        self.active = True
        self.buttonUpdate.setEnabled(False)
        self.measure_time = time()
        threading.Thread(target=self.serial_thread_handler.ListenForRepsonce, args=(self.serial,)).start()
        #self.update_timer.start(100)
        #self.UpdateData()
        self.active = False
    def UpdateData(self):
        #print ("UpdateData called")
        if not self.serial_thread_handler.GetStatus() == "received":
            return
        #self.update_timer.stop()
        response = self.serial_thread_handler.GetResponce()
        print("Serial response: ", response)
        self.buttonUpdate.setEnabled(True)
        if len(response) == 0:
            print("WARNING: No responce received")
            return
        self.active = False
        for l_ in response:
            for iter in self.regexp.finditer(l_.decode('utf-8')):
                sensor = iter.group('sensor')
                if sensor not in self.sensor_data:
                    self.sensor_data[sensor] = {'T':[], 'RH':[], 'time':[]}
                self.sensor_data[sensor]['T'].append(float(iter.group('T')))
                self.sensor_data[sensor]['RH'].append(float(iter.group('RH')))
                self.sensor_data[sensor]['time'].append(self.measure_time)
            l_.decode('utf-8')
        #print(self.sensor_data)
        self.UpdatePlots()
        #print(self.outdir)
        if not (self.outdir is None):
            self.WriteData()

    def UpdatePlots(self):
        if len(self.sensor_data) == 0:
            return
        self.temperaturePlot.axes.clear()
        self.humidityPlot.axes.clear()
        unit = 's'
        mult = 1.
        times = {sensor:np.array(self.sensor_data[sensor]['time']) for sensor in self.sensor_data}
        st_time = min([min(times[sensor]) for sensor in times])
        max_dur = max([max(times[sensor]) for sensor in times]) - st_time
        if max_dur > 180:
            unit = 'min'
            mult = 1./60.
        elif max_dur > 10800:
            unit = 'h'
            mult = 1./3600.
        for sensor in self.sensor_data:
            self.temperaturePlot.axes.plot( (times[sensor] - st_time)*mult, self.sensor_data[sensor]['T'], label = f"Sensor {sensor}")
            self.humidityPlot.axes.plot( (times[sensor]- st_time)*mult, self.sensor_data[sensor]['RH'], label = f"Sensor {sensor}")
        
        if not (self.manual_events is None):
            color_cycle = plt.rcParams['axes.prop_cycle']()
            for i in range(len(self.manual_events["time"])):
                l_ = self.temperaturePlot.axes.axvline((self.manual_events["time"][i] - st_time)*mult, linestyle = '--', 
                        label = f"{self.manual_events['name'][i]}", **(next(color_cycle)))
                self.humidityPlot.axes.axvline((self.manual_events["time"][i] - st_time)*mult, linestyle = '--',
                        label = f"{self.manual_events['name'][i]}", color = l_.get_color())
                pass
        self.temperaturePlot.axes.legend(fontsize=8)
        self.humidityPlot.axes.legend(fontsize=8)
        self.temperaturePlot.SetXYLabels(xlabel = f"Time [{unit}]", ylabel = "Temperature [C]")
        self.humidityPlot.SetXYLabels(xlabel = f"Time [{unit}]", ylabel = "Relative humidity [%]")
        self.temperaturePlot.draw()
        self.humidityPlot.draw()
    def SelectOutdir(self):
        outdir = QFileDialog.getExistingDirectory(self, "Select output folder", os.getcwd())
        if outdir == "":
            return
        self.outdir=outdir
        print(self.outdir)
        self.fileNameField.setText(self.outdir)
        self.outfiles = {}
        for sensor in self.sensor_data:
            self.lines_written[sensor] = 0
        self.WriteData()
        self.CloseAndOpenIntermediate()
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.CloseAndOpenIntermediate)
        self.autosave_timer.start(600*1000)# every 10 minutes
    def WriteData(self):
        #print("Writing data")
        if self.outdir is None:
            self.WarnUser(text = "No output directory selected", title = "ERROR!")
            if not (self.autosave_timer is None):
                self.autosave_timer.stop()
                return
        for sensor in self.sensor_data:
            if not sensor in self.outfiles:
                self.outfiles[sensor] = open(f"{self.outdir}/sensor_{sensor}.csv", "w")
                self.outfiles[sensor].writelines("time,T,RH\n")
                self.lines_written[sensor] = 0 
            for i in range(self.lines_written[sensor], len(self.sensor_data[sensor]['T'])):
                self.outfiles[sensor].writelines(f"{self.sensor_data[sensor]['time'][i]:0.2f},{self.sensor_data[sensor]['T'][i]:0.2f},{self.sensor_data[sensor]['RH'][i]:0.2f}\n")
            self.lines_written[sensor] = len(self.sensor_data[sensor]['T'])
        ## Writing events
        if not 'events' in self.outfiles:
            self.outfiles['events'] = open(f"{self.outdir}/events.csv", "w")
        self.outfiles['events'].writelines("time,name,description\n")
        if not (self.manual_events is None):
            for i in range(len(self.manual_events["time"])):
                self.outfiles['events'].write(f"{self.manual_events['time'][i]:0.2f},{self.manual_events['name'][i]},{self.manual_events['description'][i]}\n")
            self.lines_written['events'] = len(self.manual_events["time"])
    def ShowManualEvents(self):
        self.manualEventsWidget.show()

    def GetEventList(self):
        self.manual_events = self.manualEventsWidget.GetEvents()        
        for i in range(len(self.manual_events["time"])):
            self.manual_events['time'][i] = QDateTime.fromString(
                    self.manual_events['time'][i], 
                    "yyyy-MM-dd HH:mm:ss").toSecsSinceEpoch() 
        self.UpdatePlots()
    def CloseAndOpenIntermediate(self):
        #print("Autosaving files")
        for sensor in self.sensor_data:
            self.outfiles[sensor].close()
            self.outfiles[sensor] = open(f"{self.outdir}/sensor_{sensor}.csv", "a")
        self.outfiles['events'].close()
        self.outfiles['events'] = open(f"{self.outdir}/events.csv", "a")
        ## And saving plots
        self.temperaturePlot.figure.savefig(f"{self.outdir}/plot_temperature.png", dpi=300)
        self.humidityPlot.figure.savefig(f"{self.outdir}/plot_humidity.png", dpi=300)
        self.temperaturePlot.figure.savefig(f"{self.outdir}/plot_temperature.pdf", dpi=300)
        self.humidityPlot.figure.savefig(f"{self.outdir}/plot_humidity.pdf", dpi=300)
    def Disconnect(self):
        self.connected = False
        self.button_connect.setEnabled(True)
        self.button_disconnect.setEnabled(False)
        self.serial.close()
        self.serial = None
        self.timer.stop()
    def WarnUser(self, text = "Warning", title="WARNING! "):
        alert = QMessageBox(self)
        alert.setWindowTitle(title)
        alert.setText(text)
        alert.exec()