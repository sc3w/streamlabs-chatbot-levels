import os
import codecs
import json

class MySettings(object):
	def __init__(self, settingsfile=None):
		try:
			with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
				self.__dict__ = json.load(f, encoding="utf-8")
		except:
			self.Levels = 3
			self.LevelMaxTime = 80
			self.Tier1SubProgress = 5
			self.Tier2SubProgress = 10
			self.Tier3SubProgress = 20
			self.BitProgress = 1
			self.DonationProgress = 5
			self.DonationToken = ""
			self.OverlayWidgetHeight = 48
			self.OverlayWidgetFontSize = 16
			self.OverlayWidgetFontColor = "rgba(255,255,255,1.0)"
			self.OverlayWidgetProgressBarTrackColor = "rgba(0,0,0,1.0)"
			self.OverlayWidgetProgressBarColor = "rgba(255,0,0,1.0)"
			self.OverlayWidgetBorderRadius = 5
			self.OverlayWidgetCurrentLevelMessage = "Level {0} unlocked!"
			self.OverlayWidgetAllUnlockedMessage = "All levels unlocked!"

	def Reload(self, jsondata):
		self.__dict__ = json.loads(jsondata, encoding="utf-8")
		return

	def Save(self, settingsfile):
		try:
			with codecs.open(settingsfile, encoding="utf-8-sig", mode="w+") as f:
				json.dump(self.__dict__, f, encoding="utf-8")
			with codecs.open(settingsfile.replace("json", "js"), encoding="utf-8-sig", mode="w+") as f:
				f.write("var settings = {0};".format(json.dumps(self.__dict__, encoding='utf-8')))
		except:
			Parent.Log(ScriptName, "Failed to save settings to file.")
		return