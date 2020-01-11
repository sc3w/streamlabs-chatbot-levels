#---------------------------
#   Import Libraries
#---------------------------
import os
import sys
import json
import re
import time
import math
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "lib")) #point at lib folder for classes / references

import codecs
import ctypes

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
ScriptSettings = None

global Timer
Timer = 0

global Active
Active = False

global TimerTick
TimerTick = None

global Levels
Levels = 3

global CurrentLevel
CurrentLevel = 0

global CurrentLevelFileName
CurrentLevelFileName = "Overlays\currentlevel.txt"

global ConfettiStarted
ConfettiStarted = False

# Compiled regex to verify USERNOTICE and extract tags
reUserNotice = re.compile(r"(?:^(?:@(?P<irctags>[^\ ]*)\ )?:tmi\.twitch\.tv\ USERNOTICE)")

# Compiled regex to extract bits from IRCv3 Tags
reBitsUsed = re.compile(r"^@.*?bits=(?P<amount>\d*);?")

#---------------------------
#   Script Functions
#---------------------------
def UpdateTime(extraMinutes):
    global Timer
    Timer += extraMinutes

def StartTimer():
    global Active
    Active = True

def StopTimer():
    global Active
    Active = False

def ResetTimer():
    global Timer
    global CurrentLevel
    global CurrentLevelFileName
    global ConfettiStarted
    global Active

    Timer = 0
    CurrentLevel = 0
    ConfettiStarted = False
    Active = False 

    WriteTimeToFile(0)

    path = os.path.dirname(__file__)

    with codecs.open(os.path.join(path, CurrentLevelFileName), "r") as f:
        data = f.read()

    with codecs.open(os.path.join(path, CurrentLevelFileName), encoding='utf-8-sig', mode='w+') as file:
        file.write("0")

    return

#---------------------------
#   Lifecycle Functions
#---------------------------

def Init():

    global ScriptSettings
    path = os.path.dirname(__file__)

    # Create Settings Directory
    directory = os.path.join(os.path.dirname(__file__), "Settings")
    if not os.path.exists(directory):
        os.makedirs(directory)

    if not os.path.exists(os.path.join(path, CurrentLevelFileName)):
        with open(os.path.join(path, CurrentLevelFileName), "w+") as f:
            f.write("0")

    # Load settings
    SettingsFile = os.path.join(os.path.dirname(__file__), "Settings\settings.json")

    ScriptSettings = MySettings(SettingsFile)

    ScriptSettings.Initialized = True

    return


def Execute(data):

    global ScriptSettings

    if ScriptSettings is None:
        return

    # Raw IRC message from Twitch
    if data.IsRawData() and data.IsFromTwitch():

        # Apply regex on raw data to detect subscription usernotice
        usernotice = reUserNotice.search(data.RawData)
        if usernotice:

            # Parse IRCv3 tags in a dictionary
            tags = dict(re.findall(r"([^=]+)=([^;]*)(?:;|$)", usernotice.group("irctags")))

            # local vars
            addMinutes = 0

            # Tier 3000 aka 25$
            if tags["msg-param-sub-plan"] == "3000":
                addMinutes = ScriptSettings.Tier3SubProgress * 60
            # Tier 2000 aka 10$
            elif tags["msg-param-sub-plan"] == "2000":
                addMinutes = ScriptSettings.Tier2SubProgress * 60
            # Tier 1000 aka 5$ OR Prime
            else:
                addMinutes = ScriptSettings.Tier1SubProgress * 60

            UpdateTime(addMinutes)

    elif data.IsChatMessage() and data.IsFromTwitch():

        # Apply bits regex to detect bits usage if timeAddedPerBits is set to not zero
        BitsSearch = reBitsUsed.search(data.RawData)

        # There is a regex result and a bits amount is given
        if BitsSearch and BitsSearch.group("amount"):
            # local vars
            totalBits = BitsSearch.group("amount")
            UpdateTime(float(ScriptSettings.BitProgress) * 60 * float(totalBits))
        
        elif (data.IsChatMessage() and data.GetParam(0).lower() == "!levels" 
                and Parent.HasPermission(data.User, "moderator", "")):

            if data.GetParam(1).lower() == "tier1":
               UpdateTime(ScriptSettings.Tier1SubProgress * 60)

            if data.GetParam(1).lower() == "tier2":
                UpdateTime(ScriptSettings.Tier2SubProgress * 60)

            if data.GetParam(1).lower() == "tier3":
                UpdateTime(ScriptSettings.Tier3SubProgress * 60)

            if data.GetParam(1).lower() == "dono":
                donation = float(data.GetParam(2))
                UpdateTime(ScriptSettings.DonationProgress * 60 * donation)

            if data.GetParam(1).lower() == "bits":
                bits = float(data.GetParam(2))
                UpdateTime(float(ScriptSettings.BitProgress) * bits)
        elif (data.IsChatMessage() and data.GetParam(0).lower() == "!sron"
                and Parent.HasPermission(data.User, "caster", "")):
            StartTimer()
        elif (data.IsChatMessage() and data.GetParam(0).lower() == "!sroff"
                and Parent.HasPermission(data.User, "caster", "")):
            StopTimer()
        elif (data.IsChatMessage() and data.GetParam(0).lower() == "!srreset"
                and Parent.HasPermission(data.User, "caster", "")):
            ResetTimer()

    return 

def Tick():

    global ScriptSettings

    if ScriptSettings is None:
        return

    if not ScriptSettings.Enabled and not ScriptSettings.Initialized:
        return

    global TimerTick

    if TimerTick is None and Active:
        TimerTick = time.time()

    if (time.time() - TimerTick >= 1.0 and Active):
        global Timer
        Timer += (time.time() - TimerTick)
        
        Parent.Log(ScriptName, str(Timer))

        TimerTick = time.time()

        WriteTimeToFile(Timer)

        level = int(math.floor(Timer / (ScriptSettings.LevelMaxTime * 60)))
        
        global CurrentLevel
        global ConfettiStarted

        if level >= ScriptSettings.Levels:
            level = ScriptSettings.Levels-1
            if not ConfettiStarted:
                ConfettiStarted = True
                payload = {
                    "type": "start_confetti"
                }
                Parent.BroadcastWsEvent("LEVELS_UPDATE", json.dumps(payload))

        if CurrentLevel != level:
            CurrentLevel = level
            
            if (level+1) == ScriptSettings.Levels:
                Parent.SendTwitchMessage(ScriptSettings.OverlayWidgetAllUnlockedMessage)
            else:
                Parent.SendTwitchMessage(ScriptSettings.OverlayWidgetCurrentLevelMessage.format(level+1))

            with codecs.open(os.path.join(path, CurrentLevelFileName), "r") as f:
                data = f.read()

            #with open(os.path.join(path, CurrentLevelFileName), "w") as file:
            with codecs.open(os.path.join(path, CurrentLevelFileName), encoding='utf-8-sig', mode='w+') as file:
                file.write(str(level))

        WatchDonations()

 
    return

def WriteTimeToFile(timer):
    path = os.path.dirname(__file__)
    with codecs.open(os.path.join(path, 'overlay.js'), encoding='utf-8-sig', mode='w+') as file:
        file.write('var time =' + str(timer) + ';')

def WatchDonations():
    path = os.path.dirname(__file__)

    with codecs.open(os.path.join(path, 'donations.txt'), "r") as f:
        data = f.read()
        if len(data) > 0:
            UpdateTime(ScriptSettings.DonationProgress * 60 * float(data))
            with codecs.open(os.path.join(path, 'donations.txt'), encoding='utf-8-sig', mode='w+') as file:
                file.write('')

def ReloadSettings(jsonData):
    global ScriptSettings

    if ScriptSettings is None:
        return

    # this is never called due to a known issue:
    # https://github.com/AnkhHeart/Streamlabs-Chatbot-Python-Boilerplate/issues/7
    ScriptSettings.Reload(jsonData)
    ScriptSettings.Save(SettingsFile)
    return


def Unload():

    global ScriptSettings
    if ScriptSettings is None:
        return

    ScriptSettings.Enabled = False

    return


def ScriptToggled(state):

    global ScriptSettings
    if ScriptSettings is None:
        return

    if not state:
        Unload()
    else:
        ScriptSettings.Enabled = True
        Init()

    return
