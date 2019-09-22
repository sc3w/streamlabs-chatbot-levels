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
ScriptSettings = None

global Timer
Timer = 0

global TimerTick
TimerTick = None

global Levels
Levels = 3

global DonationsAmount
DonationsAmount = None

# Compiled regex to verify USERNOTICE and extract tags
reUserNotice = re.compile(r"(?:^(?:@(?P<irctags>[^\ ]*)\ )?:tmi\.twitch\.tv\ USERNOTICE)")

# Compiled regex to extract bits from IRCv3 Tags
reBitsUsed = re.compile(r"^@.*?bits=(?P<amount>\d*);?")


#---------------------------
#   Script Functions
#---------------------------
def GetPercent():
    global ScriptSettings

    if ScriptSettings.CurrentLevel == ScriptSettings.Levels:
        return 100
    
    relativeTime = Timer / ScriptSettings.CurrentLevel

    return (relativeTime * ScriptSettings.LevelMaxTime) / 100


def SendUpdateMessage(extraMinutes):
    payload = {
        "type": "progress",
        "addMinutes": extraMinutes
    }

    Parent.BroadcastWsEvent("LEVELS_UPDATE",json.dumps(payload))


def SendStartTimer():
    payload = {
        "type": "start"
    }

    Parent.BroadcastWsEvent("LEVELS_UPDATE",json.dumps(payload))
    return


def SendStopTimer():
    payload = {
        "type": "stop"
    }

    Parent.BroadcastWsEvent("LEVELS_UPDATE",json.dumps(payload))
    return


def GetDonationsAmount():
    url = ScriptSettings.GetDonationsUrl()

    httpResult = Parent.GetRequest(url, {})
    jsonResult = json.loads(httpResult)
    result = json.loads(jsonResult['response'])

    return int(result['data']['amount']['current'])


def CheckForDonations():
    
    newDonationsAmount = GetDonationsAmount()

    global DonationsAmount
    global ScriptSettings

    if DonationsAmount is None:
        DonationsAmount = newDonationsAmount
    elif newDonationsAmount != DonationsAmount:

        # there is no new donation or
        # the donation widget has been reseted
        if newDonationsAmount <= DonationsAmount:
            DonationsAmount = newDonationsAmount
            return

        amount = newDonationsAmount - DonationsAmount

        DonationsAmount = newDonationsAmount

        SendUpdateMessage(ScriptSettings.DonationProgress * 60 * amount)
    
    return

def RefreshOverlay():
    payload = {
        "type": "reload"
    }

    Parent.BroadcastWsEvent("LEVELS_UPDATE", json.dumps(payload))

    return

#---------------------------
#   Lifecycle Functions
#---------------------------

def Init():

    global ScriptSettings

    # Create Settings Directory
    directory = os.path.join(os.path.dirname(__file__), "Settings")
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Load settings
    SettingsFile = os.path.join(os.path.dirname(__file__), "Settings\settings.json")

    ScriptSettings = MySettings(SettingsFile)

    TimerTick = time.time()

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
    

            SendUpdateMessage(addMinutes)

    elif data.IsChatMessage() and data.IsFromTwitch():

        # Apply bits regex to detect bits usage if timeAddedPerBits is set to not zero
        BitsSearch = reBitsUsed.search(data.RawData)

        # There is a regex result and a bits amount is given
        if BitsSearch and BitsSearch.group("amount"):
            # local vars
            totalBits = BitsSearch.group("amount")
            SendUpdateMessage(ScriptSettings.BitProgress * 60 * int(totalBits))
        
        elif (data.IsChatMessage() and data.GetParam(0).lower() == "!levels" 
                and Parent.HasPermission(data.User, "moderator", "")):

            if data.GetParam(1).lower() == "tier1":
               SendUpdateMessage(ScriptSettings.Tier1SubProgress * 60)

            if data.GetParam(1).lower() == "tier2":
                SendUpdateMessage(ScriptSettings.Tier2SubProgress * 60)

            if data.GetParam(1).lower() == "tier3":
                SendUpdateMessage(ScriptSettings.Tier3SubProgress * 60)

            if data.GetParam(1).lower() == "donation":
                donation = int(data.GetParam(2))
                SendUpdateMessage(ScriptSettings.DonationProgress * 60 * donation)

            if data.GetParam(1).lower() == "bits":
                bits = int(data.GetParam(2))
                SendUpdateMessage(ScriptSettings.BitProgress * 60 * bits)


    return


def Tick():

    global ScriptSettings

    if ScriptSettings is None:
        return

    if not ScriptSettings.Enabled and not ScriptSettings.Initialized:
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

        if Timer % 4 == 0:
            CheckForDonations()

            isLive = Parent.IsLive()

            # start timer if the stream went live
            # stop the timer if the tream went down
            if isLive != ScriptSettings.IsLive:
                if isLive:
                    SendStartTimer()
                else:
                    SendStopTimer()
                
                ScriptSettings.IsLive = isLive

    return


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
