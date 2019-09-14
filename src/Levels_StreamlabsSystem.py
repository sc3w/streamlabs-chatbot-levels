#---------------------------
#   Import Libraries
#---------------------------
import os
import sys
import json
import re
import time
sys.path.append(os.path.join(os.path.dirname(__file__), "lib")) #point at lib folder for classes / references

import clr
clr.AddReference("IronPython.SQLite.dll")
clr.AddReference("IronPython.Modules.dll")

from Settings_Module import MySettings

#---------------------------
#   Script Information
#---------------------------
ScriptName = "Levels"
Website = "https://sc3w.net"
Description = "Divide uptime into levels. Unlock levels faster with subs/cheers/donations"
Creator = "sc3w"
Version = "1.0.0.0"

#---------------------------
#   Global Variables
#---------------------------
global SettingsFile
SettingsFile = ""

global ScriptSettings
ScriptSettings = MySettings()

global Timer
Timer = 0

global TimerTick
TimerTick = None

global Levels
Levels = 3

# Compiled regex to verify USERNOTICE and extract tags
reUserNotice = re.compile(r"(?:^(?:@(?P<irctags>[^\ ]*)\ )?:tmi\.twitch\.tv\ USERNOTICE)")

# Compiled regex to extract bits from IRCv3 Tags
reBitsUsed = re.compile(r"^@.*?bits=(?P<amount>\d*);?")


#---------------------------
#   Script Functions
#---------------------------

def LogSettings():
    Parent.Log(ScriptName, "Settings:")

    for key in ScriptSettings.__dict__:
        value = ScriptSettings.__dict__[key]
        Parent.Log(ScriptName, "%s: %s" % (key, value))

    return


def GetOverlayText():
    return ScriptSettings.OverlayWidgetCurrentLevelMessage.format(1)


def GetPercent():
    if ScriptSettings.CurrentLevel == ScriptSettings.Levels:
        return 100
    
    relativeTime = Timer / ScriptSettings.CurrentLevel

    return (relativeTime * ScriptSettings.LevelMaxTime) / 100


def SendInitMessage():
    payload = {
        "height": ScriptSettings.OverlayWidgetHeight,
        "fontSize": ScriptSettings.OverlayWidgetFontSize,
        "fontColor": ScriptSettings.OverlayWidgetFontColor,
        "trackColor": ScriptSettings.OverlayWidgetProgressBarTrackColor,
        "progressBarColor": ScriptSettings.OverlayWidgetProgressBarColor,
        "borderRadius": ScriptSettings.OverlayWidgetBorderRadius,
        "text": GetOverlayText(),
        "enabled":  ScriptSettings.Enabled,
        "percent": GetPercent(),
        "timerMax": ScriptSettings.LevelMaxTime * 60,
        "levels": ScriptSettings.Levels
    }

    Parent.BroadcastWsEvent("LEVELS_INIT",json.dumps(payload))

def SendUpdateMessage():
    payload = {
        "levels": ScriptSettings.Levels,
        "currentLevel": ScriptSettings.CurrentLevel,
        "percent": GetPercent(),
        "text": GetOverlayText(),
        "enabled":  ScriptSettings.Enabled
    }

    Parent.BroadcastWsEvent("LEVELS_UPDATE",json.dumps(payload))
#---------------------------
#   Lifecycle Functions
#---------------------------

def Init():

    # Create Settings Directory
    directory = os.path.join(os.path.dirname(__file__), "Settings")
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Load settings
    SettingsFile = os.path.join(os.path.dirname(__file__), "Settings\settings.json")
    ScriptSettings = MySettings(SettingsFile)

    SendInitMessage()

    TimerTick = time.time()

    return


def Execute(data):

    # Raw IRC message from Twitch
    if data.IsRawData() and data.IsFromTwitch():

        # Apply regex on raw data to detect subscription usernotice
        usernotice = reUserNotice.search(data.RawData)
        if usernotice:

            # Parse IRCv3 tags in a dictionary
            tags = dict(re.findall(r"([^=]+)=([^;]*)(?:;|$)", usernotice.group("irctags")))

            # local vars
            extraMinutes = 0

            # Tier 3000 aka 25$
            if tags["msg-param-sub-plan"] == "3000":
                extraMinutes = ScriptSettings.Tier3SubProgress * 60
            # Tier 2000 aka 10$
            elif tags["msg-param-sub-plan"] == "2000":
                extraMinutes = ScriptSettings.Tier2SubProgress * 60
            # Tier 1000 aka 5$ OR Prime
            else:
                extraMinutes = ScriptSettings.Tier1SubProgress * 60
    
            Timer += extraMinutes

            SendUpdateMessage()

    return


def Tick():
    if not ScriptSettings.Enabled:
        return

    global TimerTick

    if TimerTick is None:
        TimerTick = time.time()

    if (time.time() - TimerTick >= 1.0):
        TimerTick = time.time()

        global Timer
        Timer += 1

        percent = GetPercent()

        if percent >= 100:
            if ScriptSettings.CurrentLevel < ScriptSettings.Levels:
                ScriptSettings.CurrentLevel += 1
            else:
                ScriptSettings.CurrentLevel = ScriptSettings.Levels

                ScriptSettings.Enabled = False
                Timer = ScriptSettings.LevelMaxTime

    return



def Parse(parseString, userid, username, targetid, targetname, message):
    
    if "$myparameter" in parseString:
        return parseString.replace("$myparameter","I am a cat!")
    
    return parseString


def ReloadSettings(jsonData):
    # this is never called due to a known issue:
    # https://github.com/AnkhHeart/Streamlabs-Chatbot-Python-Boilerplate/issues/7
    ScriptSettings.Reload(jsonData)
    ScriptSettings.Save(SettingsFile)
    return


def Unload():
    ScriptSettings.Enabled = False
    return

def ScriptToggled(state):

    if not state:
        Unload()
    else:
        ScriptSettings.Enabled = True
        Init()

    LogSettings()

    return
