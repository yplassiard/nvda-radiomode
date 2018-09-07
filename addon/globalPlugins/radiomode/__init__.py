# *-* coding: utf8 *-*


import ui, braille
import addonHandler, globalPluginHandler, logHandler
import config
import synthDriverHandler
import nvwave
import sys, os, re
sys.path.append(os.path.dirname(__file__))
import playsound
del sys.path[-1]

addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("radiomode")
    rmActive = False
    fnKeys = ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]
    musicAudioDevice = None
    monitorAudioDevice = None
    speechAudioDevice = None
    carts = {}
    

    def __init__(self):
        super(globalPluginHandler.GlobalPlugin, self).__init__()
        logHandler.log.info("Loading radio mode")
        self.loadConfiguration()

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
            if cart is not None and os.access(cart, F_OK | R_OK) == True:
                self.carts[i] = cart
                logHandler.log.info("Loaded cart {i}: {cart}".format(i=i, cart=cart))

        logHandler.log.info("Speech audio device:%s\nMonitor audio device: %s\nMusic audio device: %s" %(self.speechAudioDevice, self.monitorAudioDevice, self.musicAudioDevice))
        
    def saveConfiguration(self):
        config.conf["radiomode"] = addonConfig
    
                
    def bindRadioModeGestures(self):
        for key in self.fnKeys:
            self.bindGesture("kb:%s" % key, "playFile")
            self.bindGesture("kb:control+%s" % key, "loadFile")
            self.bindGesture("kb:shift+%s" % key, "sayFile")
            self.bindGesture("kb:alt+%s" % key, "previewFile")
    def clearRadioModeGestures(self):
        self.clearGestureBindings()
        self.bindGestures(self.__gestures)
        
    def script_cycleAudioOutput(self, gesture):
        try:
            audioDevices = nvwave.getOutputDeviceNames()
        except:
            ui.message(_("Unable to get device's list."))
            return
        if len(audioDevices) <= 1:
            ui.message(_("Current and only output device {name}".format(audioDevices[0])))
            return
        newIdx = (audioDevices.index(config.conf["speech"]["outputDevice"]) + 1) % len(audioDevices)
        self.speechAudioDevice = audioDevices[newIdx]
        config.conf["speech"]["outputDevice"] = self.speechAudioDevice
        synth = synthDriverHandler.setSynth(config.conf["speech"]["synth"])
        ui.message(_("Set output device to {device}".format(device=self.speechAudioDevice)))

    script_cycleAudioOutput.__doc__ = _("Cycles through the available audio device outputs.")

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
        logHandler.log.info("Gesture  %s" % (gesture.identifiers[0]))
    script_loadFile.__doc__ = _("Loads an audio file into the specified cart.")

    def script_playFile(self, gesture):
        logHandler.log.info("Gesture  %s" % (gesture.identifiers[0]))
    script_playFile.__doc__ = _("Plays the file associated to the specified cart on the selected music audio device.")
    
    def script_sayFile(self, gesture):
        m = re.match(".*f([0-9]+)$", gesture.identifiers[0])
        if m:
            cart = m.group(1)
            ui.message(_("Cart {i} file: {file}".format(i=cart, file=self.carts.get(cart, None))))
    script_sayFile.__doc__ = _("Speaks the filename associated to this cart.")

    def script_previewFile(self, gesture):
        logHandler.log.info("Gesture  %s" % (gesture.identifiers[0]))
    script_previewFile.__doc__ = _("Plays the loaded file on the selected monitor audio device.")
    __gestures = {
        "kb:nvda+alt+c": "cycleAudioOutput",
        "kb:nvda+alt+space": "toggleRadioMode",
    }
    
        
                       
            
