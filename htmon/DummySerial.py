import numpy as np
from copy import deepcopy

class DummySerial:
    """
    This is dummy serial class, which is used for testing the GUI without the Arduino.
    """
    def __init__(self, dev = 'dummy', baud = '0'):
        self.n_sens = np.random.randint(2,6)
        self.mean_t = np.random.uniform(20,30, size = self.n_sens)
        self.mean_h = np.random.uniform(35,55, size = self.n_sens)
        self.std_t = np.random.uniform(0.3,3, size = self.n_sens) 
        self.std_h = np.random.uniform(0.5,3, size = self.n_sens) 
        self.lines = []
    def write(self, message=''):
        if message == b'r':
            outline = ';'.join([f'{i:d}:T={np.random.normal(self.mean_t[i],self.std_t[i]):0.2f}C,RH={np.random.normal(self.mean_h[i],self.std_h[i]):0.2f}%' for i in range(self.n_sens)])
            outline+="\n"
            self.lines.append(outline.encode())
    def readlines(self):
        output=deepcopy(self.lines)
        self.lines = []
        return output
    def close(self):
        pass
            