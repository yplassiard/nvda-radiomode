# *-* coding: utf8 *-*


import gui, wx, ui, braille
import addonHandler, globalPluginHandler, logHandler
import config
import synthDriverHandler
import nvwave
import sys, os, re, threading
sys.path.append(os.path.dirname(__file__))
import playsound
del sys.path[-1]
addonHandler.initTranslation()

class FileChooserDialog(threading.Thread):
    def __init__(self, gp, cart):
        self.gp = gp
        self.cart = cart
        super(FileChooserDialog, self).__init__()
    def run(self):
        dlg = wx.FileDialog(parent=gui.mainFrame)
        if dlg.ShowModal() == wx.ID_OK:
            self.gp.carts[self.cart] = dlg.GetPath()
        


        
        
        
def OpenFile(gp, cart):
    fileDlg = FileChooserDialog(gp, cart)
    gui.mainFrame.prePopup()
    fileDlg.start()
    gui.mainFrame.postPopup()
    
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("RadioMode")
    rmActive = False
    fnKeys = ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]
    musicAudioDevice = None
    monitorAudioDevice = None
    speechAudioDevice = None
    carts = {}
    players = {}
    

    def __init__(self):
        super(globalPluginHandler.GlobalPlugin, self).__init__()
        logHandler.log.info("Loading radio mode")
        self.loadConfiguration()

    def terminate(self):
        self.saveConfiguration()
        
    def loadConfiguration(self):
        addonConfig = config.conf.get("radiomode")
        if addonConfig is None:
            addonConfig = {}
        self.audioDevices = nvwave.getOutputDeviceNames()
        self.speechAudioDevice = addonConfig.get("speechAudioDevice", None)
        if self.speechAudioDevice is None or self.speechAudioDevice not in self.audioDevices:
            self.speechAudioDevice = self.audioDevices[0]
        self.musicAudioDevice = addonConfig.get("musicAudioDevice", None)
        if self.musicAudioDevice is None or self.musicAudioDevice not in self.audioDevices:
            self.musicAudioDevice = self.audioDevices[0]
        self.monitorAudioDevice = addonConfig.get("monitorAudioDevice", None)
        if self.monitorAudioDevice is None or self.monitorAudioDevice not in self.audioDevices:
            self.monitorAudioDevice = self.audioDevices[0]
        for i in xrange(1, 13):
            cart = addonConfig.get("cart_%s" % i, None)
            if cart is not None and os.access(cart, os.F_OK) == True:
                self.carts[str(i)] = cart
                logHandler.log.info("Loaded cart {i}: {cart}".format(i=i, cart=cart))

        logHandler.log.info("Speech audio device: %s\nMonitor audio device: %s\nMusic audio device: %s" %(self.speechAudioDevice, self.monitorAudioDevice, self.musicAudioDevice))
        
    def saveConfiguration(self):
        config.conf["radiomode"] = {}
        for key in self.carts:
            config.conf["radiomode"]["cart_%s" % key] = self.carts[key]
        config.conf["radiomode"]["monitorAudioDevice"] = self.monitorAudioDevice
        config.conf["radiomode"]["musicAudioDevice"] = self.musicAudioDevice
        config.conf["radiomode"]["speechAudioDevice"] = self.speechAudioDevice    
                
    def bindRadioModeGestures(self):
        for key in self.fnKeys:
            self.bindGesture("kb:%s" % key, "playFile")
            self.bindGesture("kb:control+%s" % key, "loadFile")
            self.bindGesture("kb:shift+%s" % key, "sayFile")
            self.bindGesture("kb:alt+%s" % key, "previewFile")
    def clearRadioModeGestures(self):
        self.clearGestureBindings()
        self.bindGestures(self.__gestures)
        
    def script_cycleSpeechDevice(self, gesture):
        self.speechAudioDevice = self.selectDevice(self.speechAudioDevice, _("speech device"), skipSoundMapper=False, speak=False)
        config.conf["speech"]["outputDevice"] = self.speechAudioDevice
        synth = synthDriverHandler.setSynth(config.conf["speech"]["synth"])
        ui.message(_("Set output device to {device}".format(device=self.speechAudioDevice)))

    script_cycleSpeechDevice.__doc__ = _("Cycles through the available audio device outputs.")


    def script_cycleMusicDevice(self, gesture):
        self.musicAudioDevice = self.selectDevice(self.musicAudioDevice, _("music device"), skipSoundMapper=True)
    script_cycleMusicDevice.__doc__ = _("Changes the music audio device.")


    def script_cycleMonitorDevice(self, gesture):
        self.monitorAudioDevice = self.selectDevice(self.monitorAudioDevice, _("Monitor device"), skipSoundMapper=True)
    script_cycleMonitorDevice.__doc__ = _("Changes the monitor audio device.")

    def selectDevice(self, deviceName, message, skipSoundMapper=False, speak=True):
        try:
            audioDevices = nvwave.getOutputDeviceNames()
        except:
            ui.message(_("Unable to get device's list."))
            return
        if len(audioDevices) <= 1:
            ui.message(_("Current and only output device {name}".format(audioDevices[0])))
            return audioDevices[0]
        newIdx = (audioDevices.index(deviceName) + 1) % len(audioDevices)
        if skipSoundMapper and newIdx == 0 and len(audioDevices) > 1:
            newIdx = 1
        if speak is True:
            ui.message(_("Set {title} to {device}".format(title=message, device=audioDevices[newIdx])))
        return audioDevices[newIdx]



    
    def script_toggleRadioMode(self, gesture):
        if self.rmActive:
            self.clearRadioModeGestures()
            self.rmActive = False
            ui.message(_("Radio mode off"))
        else:
            self.bindRadioModeGestures()
            self.rmActive = True
            ui.message(_("Radio mode on"))

    def script_loadFile(self, gesture):
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            OpenFile(self, cart)
    script_loadFile.__doc__ = _("Loads an audio file into the specified cart.")

    def script_playFile(self, gesture):
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            file = self.carts.get(cart, None)
            if file is None:
                ui.message(_("No file associated to cart {cart}".format(cart=cart)))
                return
            p = self.players.get(cart, None)
            if p is None:
                try:
                    p = playsound.Player(file)
                except Exception as e:                    
                    logHandler.log.exception("Failed to open %s: %s" % (file, e))
                    return
                self.players[cart] = p
            try:
                p.play(nvwave.outputDeviceNameToID(self.musicAudioDevice))
            except Exception as e:
                logHandler.log.exception("Failed to play %s: %s" %(file, e))
                del p
                self.players[cart] = None
                p = None
            

    script_playFile.__doc__ = _("Plays the file associated to the specified cart on the selected music audio device.")
    
    def script_sayFile(self, gesture):
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            ui.message(_("Cart {i} file: {file}".format(i=cart, file=self.carts.get(cart, None))))
    script_sayFile.__doc__ = _("Speaks the filename associated to this cart.")

    def script_previewFile(self, gesture):
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            file = self.carts.get(cart, None)
            if file is None:
                ui.message(_("No file associated to cart {cart}".format(cart=cart)))
                return
            p = self.players.get(cart, None)
            if p is None:
                try:
                    p = playsound.Player(file)
                except Exception as e:                    
                    logHandler.log.exception("Failed to open %s: %s" % (file, e))
                    return
                self.players[cart] = p
            try:
                p.play(nvwave.outputDeviceNameToID(self.monitorAudioDevice))
            except Exception as e:
                logHandler.log.exception("Failed to play %s: %s" %(file, e))
                del p
                self.players[cart] = None
                p = None
            
                
    script_previewFile.__doc__ = _("Plays the loaded file on the selected monitor audio device.")
    __gestures = {
        "kb:nvda+alt+s": "cycleSpeechDevice",
        "kb:nvda+alt+o": "cycleMonitorDevice",
        "kb:nvda+alt+u": "cycleMusicDevice",
        "kb:nvda+alt+space": "toggleRadioMode",
    }
    
        
                       
            
