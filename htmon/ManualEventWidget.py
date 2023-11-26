from PyQt5.QtWidgets import (
            QWidget, QTableWidget, QTableWidgetItem, 
            QVBoxLayout, QHBoxLayout, QPushButton, 
            QLabel, QLineEdit, QDateTimeEdit
            )
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QDateTime
from copy import copy, deepcopy

class ManualEventWidget(QWidget):
    events_updated = pyqtSignal()
    window_shown = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Manual events")
        self.layout = QVBoxLayout()
        self.events = {"time":[], "name":[], "description":[]}
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(["Time", "Event", "Description"])
        self.layout.addWidget(self.table)
        self.datetimeedit = QDateTimeEdit(self)
        self.datetimeedit.setDateTime(QDateTime.currentDateTime())
        self.datetimeedit.setCalendarPopup(True)
        self.datetimeedit.setMinimumWidth(165)
        self.datetimeedit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.eventTextLabel = QLabel("Name:")
        self.eventNameEdit = QLineEdit()
        self.eventNameEdit.setPlaceholderText("")
        self.eventDescriptionLabel = QLabel("Description:")
        self.eventDescriptionEdit = QLineEdit()
        self.addEventButton = QPushButton("Add event")
        self.removeSelectedButton = QPushButton("Remove selected")
        self.removeSelectedButton.setEnabled(False)
        self.removeSelectedButton.clicked.connect(self.RemoveSelected)
        self.table.itemSelectionChanged.connect(lambda: self.removeSelectedButton.setEnabled(True) if len(self.table.selectedIndexes()) > 0 else self.removeSelectedButton.setEnabled(False))
        addeventlayout = QHBoxLayout()
        addeventlayout.addWidget(self.datetimeedit)
        addeventlayout.addWidget(self.eventTextLabel)
        addeventlayout.addWidget(self.eventNameEdit)
        addeventlayout.addWidget(self.eventDescriptionLabel)
        addeventlayout.addWidget(self.eventDescriptionEdit)
        addeventlayout.addWidget(self.addEventButton)
        addeventlayout.addWidget(self.removeSelectedButton)
        self.addEventButton.clicked.connect(self.AddEventButtonAction)
        self.layout.addLayout(addeventlayout)
        self.setLayout(self.layout)
        self.window_shown.connect(self.UpdateCurrentTime)
    def AddEventButtonAction(self):
        time = self.datetimeedit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        text = self.eventNameEdit.text()
        description = self.eventDescriptionEdit.text()
        self.AddEvent(time, text, description)
        self.UpdateCurrentTime()

    def RemoveSelected(self):
        selected = self.table.selectedIndexes()
        if len(selected) == 0:
            return
        rows = sorted(set([selected[i].row() for i in range(len(selected))]))
        for r_ in rows[::-1]:
            self.events["time"].pop(r_)
            self.events["name"].pop(r_)
            self.events["description"].pop(r_)
        self.events_updated.emit()
        self.UpdateTable()
        self.UpdateCurrentTime()
    def AddEvent(self, time, name, description = ""):
        self.events["time"].append(time)
        self.events["name"].append(name)
        self.events["description"].append(description)
        self.events_updated.emit()
        self.UpdateTable()
    def UpdateTable(self):
        self.table.setRowCount(len(self.events["time"]))
        for i in range(len(self.events["time"])):
            self.table.setItem(i, 0, QTableWidgetItem(self.events["time"][i]))
            self.table.setItem(i, 1, QTableWidgetItem(self.events["name"][i]))
            self.table.setItem(i, 2, QTableWidgetItem(self.events["description"][i]))
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
    def UpdateCurrentTime(self):
        self.datetimeedit.setDateTime(QDateTime.currentDateTime())
    def show(self):
        super().show()
        self.window_shown.emit()
    def GetEvents(self):
        return deepcopy(self.events)
