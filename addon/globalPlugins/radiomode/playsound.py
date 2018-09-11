from ctypes import c_buffer, windll
from random import random
from time import sleep
from sys import getfilesystemencoding
import threading

class PlaysoundException(Exception):
    pass
class Player(threading.Thread):
    playing = False
    position = 0
    alias = None
    
    
    def __init__(self, sound):
        super(Player, self).__init__()
        self.load(sound)
    
    def winCommand(self, *command):
        """Sends a Command to the WinMM interface."""
        buf = c_buffer(255)
        command = ' '.join(command).encode(getfilesystemencoding())
        errorCode = int(windll.winmm.mciSendStringA(command, buf, 254, 0))
        if errorCode:
            errorBuffer = c_buffer(255)
            windll.winmm.mciGetErrorStringA(errorCode, errorBuffer, 254)
            exceptionMessage = ('\n    Error ' + str(errorCode) + ' for command:'
                                '\n        ' + command.decode() +
                                '\n    ' + errorBuffer.value.decode())
            raise PlaysoundException(exceptionMessage)
        return buf.value

    def load(self, sound):
        if self.playing is True:
            self.stop()
        if self.alias is not None:
            self.winCommand('close', self.alias)
            self.alias = None
        self.alias = 'playsound_' + str(random())
        self.winCommand('open "' + sound + '" alias', self.alias)
        self.winCommand('set', self.alias, 'time format milliseconds')
        self.durationInMS = self.winCommand('status', self.alias, 'length')
        return True
    def play(self, deviceId=-1, fromStart=True):
        if self.isPlaying is True:
            self.stop()
        if fromStart is True:
            position = 0
        else:
            position = self.curPosition
        self.winCommand('set', self.alias, 'output', str(deviceId))
        self.winCommand('play', self.alias, 'from ', str(position), 'to', self.durationInMS.decode())
        self.playing = True

    def stop(self):
        self.winCommand('stop', self.alias)
        self.curPosition = 0
        self.playing = False
    def pause(self):
        if self.playing:
            self.winCommand('pause', self.alias)
            self.playing = False
    
        
    def run(self):
        while self.shouldQuit is False:
            time.sleep(0.1)
            position = self.winCommand('status', self.alias, 'position')
            if position == self.curPosition:
                self.playing = False
            self.curPosition = position
        self.stop()
        self.winCommand('close', self.alias)
        self.position = 0
        self.alias = None

    def isPlaying(self):
        return self.playing

    def isStopped(self):
        return True if self.playing is False and self.position == 0 else False
    
    


