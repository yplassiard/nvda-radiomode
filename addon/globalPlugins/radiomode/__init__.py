# *-* coding: utf8 *-*


import gui, wx, ui, braille
import addonHandler, globalPluginHandler, logHandler
import config
import synthDriverHandler
import nvwave
import sys, os, re, threading
sys.path.append(os.path.dirname(__file__))
import playsound
import vlc
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
            self.gp.carts[self.gp.category][self.cart] = dlg.GetPath()
        


        
        
        
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
    categories = []
    categoryIndex = None
    category = ""
    players = {}
    

    def generateKey(self, device, sound):
        return "_".join([device, sound])
    
    def __init__(self):
        super(globalPluginHandler.GlobalPlugin, self).__init__()
        logHandler.log.info("Loading radio mode")
        self.loadConfiguration()

    def terminate(self):
        self.saveConfiguration()
        
    def loadConfiguration(self):
        addonConfig = config.conf.get("radiomode", None)
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
        for k in addonConfig.iteritems():
            key,value = k
            if isinstance(value, dict):
                self.carts[key] = {}
                for i in xrange(1, 13):
                    cart = value.get("cart_%s" % i, None)
                    if cart is not None and os.access(cart, os.F_OK) == True:
                        self.carts[key][str(i)] = cart
                        logHandler.log.info("Loaded cart {i}: {cart}".format(i=i, cart=cart.decode('utf8', 'ignore')))

        if len(self.carts) == 0:
            self.carts[_("default")] = {}
        self.categoryIndex = 0
        self.categories = self.carts.keys()
        self.category = self.categories[self.categoryIndex]
        logHandler.log.info("Speech audio device: %s\nMonitor audio device: %s\nMusic audio device: %s\nCategory: %s" %(self.speechAudioDevice, self.monitorAudioDevice, self.musicAudioDevice, self.category))
        
    def saveConfiguration(self):
        config.conf["radiomode"] = {}
        for key in self.carts:
            config.conf["radiomode"][key] = {}
            for cart in self.carts[key]:
                config.conf["radiomode"][key]["cart_%s" % cart] = self.carts[key][cart] if isinstance(self.carts[key], dict) else None
        config.conf["radiomode"]["monitorAudioDevice"] = self.monitorAudioDevice
        config.conf["radiomode"]["musicAudioDevice"] = self.musicAudioDevice
        config.conf["radiomode"]["speechAudioDevice"] = self.speechAudioDevice    
                

    def bindRadioModeGestures(self):
        for key in self.fnKeys:
            self.bindGesture("kb:%s" % key, "playFile")
            self.bindGesture("kb:control+%s" % key, "loadFile")
            self.bindGesture("kb:shift+%s" % key, "sayFile")
            self.bindGesture("kb:alt+%s" % key, "previewFile")
        self.bindGesture("kb:downarrow", "nextCategory")
        self.bindGesture("kb:uparrow", "previousCategory")
        self.bindGesture("kb:control+n", "newCategory")
        self.bindGesture("kb:delete", "removeCategory")

    def clearRadioModeGestures(self):
        self.clearGestureBindings()
        self.bindGestures(self.__gestures)

    def joinDeadThreads(self):
        for key in self.players.keys():
            thread = self.players[key]
            if thread is not None and thread.isStarted() == True:
                thread.join()
                del self.players[key]
                thread = None
    
    def script_cycleSpeechDevice(self, gesture):
        self.joinDeadThreads()
        self.speechAudioDevice = self.selectDevice(self.speechAudioDevice, _("speech device"), skipSoundMapper=False, speak=False)
        config.conf["speech"]["outputDevice"] = self.speechAudioDevice
        synth = synthDriverHandler.setSynth(config.conf["speech"]["synth"])
        ui.message(_("Set output device to {device}".format(device=self.speechAudioDevice)))

    script_cycleSpeechDevice.__doc__ = _("Cycles through the available audio device outputs.")


    def script_cycleMusicDevice(self, gesture):
        self.joinDeadThreads()
        self.musicAudioDevice = self.selectDevice(self.musicAudioDevice, _("music device"), skipSoundMapper=True)
    script_cycleMusicDevice.__doc__ = _("Changes the music audio device.")


    def script_cycleMonitorDevice(self, gesture):
        self.joinDeadThreads()
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
        try:
            newIdx = (audioDevices.index(deviceName) + 1) % len(audioDevices)
        except ValueError:
            newIdx = 0
        if skipSoundMapper and newIdx == 0 and len(audioDevices) > 1:
            newIdx = 1
        if speak is True:
            ui.message(_("Set {title} to {device}".format(title=message, device=audioDevices[newIdx])))
        return audioDevices[newIdx]



    
    def script_toggleRadioMode(self, gesture):
        self.joinDeadThreads()
        if self.rmActive:
            self.clearRadioModeGestures()
            self.rmActive = False
            ui.message(_("Radio mode off"))
        else:
            self.bindRadioModeGestures()
            self.rmActive = True
            ui.message(_("Radio mode on"))

    def script_nextCategory(self, gesture):
        self.categoryIndex = (self.categoryIndex + 1) % len(self.categories)
        self.category = self.categories[self.categoryIndex]
        ui.message(self.category)
    def script_previousCategory(self, gesture):
        self.categoryIndex = (self.categoryIndex - 1) % len(self.categories)
        self.category = self.categories[self.categoryIndex]
        ui.message(self.category)

    def script_newCategory(self, gesture):
        pass

    def script_removeCategory(self, gesture):
        pass
    
    def script_loadFile(self, gesture):
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            OpenFile(self, cart)
    script_loadFile.__doc__ = _("Loads an audio file into the specified cart.")

    def script_playFile(self, gesture):
        self.joinDeadThreads()
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            file = self.carts[self.category].get(cart, None)
            if file is None:
                ui.message(_("No file associated to cart {cart}".format(cart=cart)))
                return
            playerKey = self.generateKey(self.musicAudioDevice, file)
            p = self.players.get(playerKey, None)
            if p is None:
                try:
                    p = playsound.Player(file)
                except Exception as e:                    
                    logHandler.log.exception("Failed to open %s: %s" % (file, e))
                    return
                self.players[playerKey] = p
            try:
                p.setOutputDevice(nvwave.outputDeviceNameToID(self.musicAudioDevice))
                p.start() if p.isStarted() == False else p.play()
            except Exception as e:
                logHandler.log.exception("Failed to play %s: %s" %(file, e))
                p.join()
                del p
                self.players[playerKey] = None
                p = None
            

    script_playFile.__doc__ = _("Plays the file associated to the specified cart on the selected music audio device.")
    
    def script_sayFile(self, gesture):
        self.joinDeadThreads()
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            ui.message(_("Cart {i} file: {file}".format(i=cart, file=self.carts[self.category].get(cart, None).decode('utf-8', 'replace'))))
    script_sayFile.__doc__ = _("Speaks the filename associated to this cart.")

    def script_previewFile(self, gesture):
        self.joinDeadThreads()
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            file = self.carts[self.category].get(cart, None)
            if file is None:
                ui.message(_("No file associated to cart {cart}".format(cart=cart)))
                return
            playerKey = self.generateKey(self.monitorAudioDevice, file)
            p = self.players.get(playerKey, None)
            if p is None:
                try:
                    p = playsound.Player(file)
                except Exception as e:                    
                    logHandler.log.exception("Failed to open %s: %s" % (file, e))
                    return
                self.players[playerKey] = p
            try:
                if p.isPlaying():
                    p.pause()
                p.setOutputDevice(nvwave.outputDeviceNameToID(self.monitorAudioDevice))
                p.start() if p.isStarted() == False else p.play()
            except Exception as e:
                logHandler.log.exception("Failed to preview %s: %s" %(file, e))
            
                
    script_previewFile.__doc__ = _("Plays the loaded file on the selected monitor audio device.")

    __gestures = {
        "kb:nvda+alt+s": "cycleSpeechDevice",
        "kb:nvda+alt+o": "cycleMonitorDevice",
        "kb:nvda+alt+u": "cycleMusicDevice",
        "kb:nvda+alt+space": "toggleRadioMode",
    }
    
        
                       
            
