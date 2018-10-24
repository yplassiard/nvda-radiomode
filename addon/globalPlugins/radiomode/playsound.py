import logHandler
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
    shouldQuit = False
    started = False
    loaded = False
    deviceId = 1
    
    
    def __init__(self, sound):
        super(Player, self).__init__()
        self.soundFile = sound
    
    def winCommand(self, *command):
        """Sends a Command to the WinMM interface."""
        buf = c_buffer(255)
        command = ' '.join(command).encode(getfilesystemencoding())
        errorCode = int(windll.winmm.mciSendStringA(command, buf, 254, 0))
        logHandler.log.info(u"Sending command: " + command)
        if errorCode:
            errorBuffer = c_buffer(255)
            windll.winmm.mciGetErrorStringA(errorCode, errorBuffer, 254)
            exceptionMessage = ('\n    Error ' + str(errorCode) + ' for command:'
                                '\n        ' + repr(command) +
                                '\n    ' + repr(errorBuffer.value))
            raise PlaysoundException(exceptionMessage)
        return buf.value

    def load(self, sound):
        if self.playing is True:
            self.stopPlayback()
        if self.alias is not None:
            self.closeDevice()
        try:
            self.alias = 'playsound_' + str(random())
            self.winCommand('open "' + sound + '" alias', self.alias)
            self.winCommand('set', self.alias, 'time format milliseconds')
            self.durationInMS = self.winCommand('status', self.alias, 'length')
            self.position = self.durationInMS
            self.loaded = True
            logHandler.log.info("Sound ready: %s" % sound)
            return True
        except Exception as e:
            logHandler.log.exception("Failed to initialize sound %s" % e)
            return False


    def closeDevice(self):
        try:
            self.winCommand('close', self.alias)
        except:
            pass
        self.position = 0
        self.alias = None
        self.isPlaying = False
        self.loaded = False

    def play(self, fromStart=True):
        if self.loaded is False:
            return False
        if self.isPlaying is True:
            self.stopPlayback()
        if fromStart is True:
            position = 0
        else:
            position = self.position
        try:
            self.winCommand('set', self.alias, 'output', str(self.deviceId))
            self.winCommand('play', self.alias, 'from ', str(position), 'to', self.durationInMS.decode())
        except Exception as e:
            logHandler.log.exception("Failed to start playback: %s" % e)
            return False
        self.playing = True

    def stopPlayback(self):
        try:
            self.winCommand('stop', self.alias)
        except Exception as e:
            logHandler.log.error("Failed to stop sound playback: %s" % e)
            pass
        self.playing = False
        
    def pause(self):
        if self.playing:
            try:
                self.winCommand('pause', self.alias, 'wait')
            except:
                pass
            self.playing = False

    def setOutputDevice(self, deviceId):
        self.deviceId = deviceId
    def isStarted(self):
        return self.started
    
        
    def run(self):
        self.started = True
        logHandler.log.info("Starting new playsound thread")
        self.load(self.soundFile) if self.loaded == False else None
        while self.loaded is False:
            sleep(0.01)
        try:
            self.play()
        except:
            logHandler.log.info("Failed to start playing sound")
            self.started = False
            return False
        while self.shouldQuit is False:
            sleep(0.01)
            try:
                position = self.winCommand('status', self.alias, 'position')
            except Exception as e:
                logHandler.log.exception("Thread exception: %s"%(e))
                position = -1
            logHandler.log.info("Curpos: %s, last=%s"%(position, self.durationInMS))
            if int(position) >= int(self.durationInMS):
                self.playing = False
                self.shouldQuit = True
            self.position = position

        self.started = False
        logHandler.log.info("Sound %s finished playback" % self.alias)
        self.stopPlayback()
        self.closeDevice()

        self.alias = None

    def isPlaying(self):
        return self.playing

    def isStopped(self):
        return True if self.playing is False and self.position == 0 else False
    
    


