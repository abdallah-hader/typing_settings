import nvwave
import globalPluginHandler
import speech
import config
import os, shutil
import glob
import wx
import addonHandler
import api
from random import randint
from globalCommands import SCRCAT_CONFIG
from ui import message
from scriptHandler import script
from gui import NVDASettingsDialog, guiHelper, mainFrame
from gui.settingsDialogs import SettingsPanel
from controlTypes import STATE_READONLY, STATE_EDITABLE
from .create import NewPack

def confinit():
	confspec = {
		"typingsnd": "boolean(default=true)",
		"typing_sound": f"string(default={get_sounds_folders()[0]})",
		"speak_on_protected":"boolean(default=True)"}
	config.confspec["typing_settings"] = confspec

addonHandler.initTranslation()
effects_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "effects")
controls = (8, 52, 82)
typingProtected = api.isTypingProtected

def get_sounds_folders():
	folders = []
	for folder in os.listdir(effects_dir):
		if os.path.isdir(os.path.join(effects_dir, folder)):
			folders.append(folder)
	return folders

def get_sounds(name):
	return [os.path.basename(sound) for sound in glob.glob(f"{effects_dir}/{name}/*.wav")]

def RestoreTypingProtected():
	api.isTypingProtected = typingProtected

def IsTypingProtected():
	if config.conf["typing_settings"]["speak_on_protected"]:
		return False
	focus = api.getFocusObject()
	if focus.isProtected:
		return True

confinit()
class TypingSettingsPanel(SettingsPanel):
	title = _("typing settings")
	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.tlable = sHelper.addItem(wx.StaticText(self, label=_("typing sound:"), name="ts"))
		self.typingSound = sHelper.addItem(wx.Choice(self, name="ts"))
		sounds = get_sounds_folders()
		self.typingSound.Set(sounds)
		self.typingSound.SetStringSelection(config.conf["typing_settings"]["typing_sound"])
		self.slable = sHelper.addItem(wx.StaticText(self, label=_("sounds"), name="ts"))
		self.sounds = sHelper.addItem(wx.Choice(self, name="ts"))
		delete = sHelper.addItem(wx.Button(self, -1, _("delete")))
		create = sHelper.addItem(wx.Button(self, -1, _("Create a new soundpack")))
		sHelper.addItem(wx.StaticText(self, label=_("speek characters")))
		self.playTypingSounds = sHelper.addItem(wx.CheckBox(self, label=_("play sounds while typing")))
		self.playTypingSounds.SetValue(config.conf["typing_settings"]["typingsnd"])
		self.speakPasswords = sHelper.addItem(wx.CheckBox(self, label=_("speak passwords")))
		self.speakPasswords.SetValue(config.conf["typing_settings"]["speak_on_protected"])
		self.OnChangeTypingSounds(None)
		self.onChange(None)
		self.playTypingSounds.Bind(wx.EVT_CHECKBOX, self.OnChangeTypingSounds)
		self.typingSound.Bind(wx.EVT_CHOICE, self.onChange)
		self.sounds.Bind(wx.EVT_CHOICE, self.onPlay)
		create.Bind(wx.EVT_BUTTON, self.OnCreate)
		delete.Bind(wx.EVT_BUTTON, self.OnDelete)


	def postInit(self):
		self.typingSound.SetFocus()

	def OnChangeTypingSounds(self, evt):
		for obj in self.GetChildren():
			if obj.Name == "ts": obj.Hide() if not self.playTypingSounds.GetValue() else obj.Show()

	def onChange(self, event):
		sounds = get_sounds(self.typingSound.GetStringSelection())
		self.sounds.Set(sounds)
		try:
			self.sounds.SetSelection(0)
		except: pass

	def OnDelete(self, event):
		index = self.typingSound.Selection
		Pack = f"{effects_dir}/{self.typingSound.GetStringSelection()}"
		msg = wx.MessageBox(_("Are you sure you want to delete {pack}?").format(pack=os.path.basename(Pack)), _("confirm"), style=wx.YES_NO)
		if msg:
			shutil.rmtree(Pack)
			self.typingSound.Delete(self.typingSound.Selection)
			try:
				self.typingSound.Selection = index-1
			except:
				self.typingSound.Selection = 0

	def onPlay(self, event):
		nvwave.playWaveFile(f"{effects_dir}/{self.typingSound.GetStringSelection()}/{self.sounds.GetStringSelection()}", True)

	def OnCreate(self, event):
		wx.CallAfter(NewPack, mainFrame)

	def onSave(self):
		config.conf["typing_settings"]["typing_sound"] = self.typingSound.GetStringSelection()
		config.conf["typing_settings"]["speak_on_protected"] = self.speakPasswords.GetValue()
		config.conf["typing_settings"]["typingsnd"] = self.playTypingSounds.GetValue()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		NVDASettingsDialog.categoryClasses.append(TypingSettingsPanel)

	def IsEditable(self, object):
		return (object.role in controls or STATE_EDITABLE in object.states) and not STATE_READONLY in object.states

	def event_gainFocus(self, object, nextHandler):
		api.isTypingProtected = IsTypingProtected
		nextHandler()

	def event_typedCharacter(self, obj, nextHandler, ch):
		if self.IsEditable(obj) and config.conf["typing_settings"]["typingsnd"]:
			if ch == " ":
				nvwave.playWaveFile(os.path.join(effects_dir, config.conf['typing_settings']['typing_sound'], "space.wav"), True)
			elif ch == "\b":
				nvwave.playWaveFile(os.path.join(effects_dir, config.conf['typing_settings']['typing_sound'], "delete.wav"), True)
			elif os.path.isfile(os.path.join(effects_dir, config.conf['typing_settings']['typing_sound'], "return.wav")) and ord(ch) == 13 or ch == "\n":
				try:
					nvwave.playWaveFile(os.path.join(effects_dir, config.conf['typing_settings']['typing_sound'], "return.wav"), True)
				except:
					pass
			else:
				count = self.SoundsCount(config.conf["typing_settings"]["typing_sound"])
				nvwave.playWaveFile(os.path.join(effects_dir, config.conf['typing_settings']['typing_sound'], "typing.wav" if count<=0 else f"typing_{randint(1, count)}.wav"), True)
		nextHandler()

	def SoundsCount(self, name):
		path = f"{effects_dir}/{name}"
		files = len([file for file in os.listdir(path) if file.startswith("typing_")])
		return files


	@script(
		description = _("Enable and disable typing sounds"),
		category=_("typing settings"),
		gestures=["kb:nvda+shift+k"])
	def script_toggle_typing_sounds(self, gesture):
		current = config.conf["typing_settings"]["typingsnd"]
		if current:
			config.conf["typing_settings"]["typingsnd"] = False
			message(_("typing sounds off"))
		else:
			config.conf["typing_settings"]["typingsnd"] = True
			message(_("typing sounds on"))

	@script(
		description = _("Enable or disable speak passwords"),
		category = _("typing settings"),
		gestures = ["kb:nvda+shift+p"])
	def script_toggle_speak_passwords(self, gesture):
		if config.conf["typing_settings"]["speak_on_protected"]:
			config.conf["typing_settings"]["speak_on_protected"] = False
			message(_("speak passwords off"))
		else:
			config.conf["typing_settings"]["speak_on_protected"] = True
			message(_("speak passwords on"))

	def terminate(self):
		RestoreTypingProtected()
		NVDASettingsDialog.categoryClasses.remove(TypingSettingsPanel)