# coding: utf-8
# dictionaries.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2019 André-Abush CLAUSE, released under GPL.
from __future__ import unicode_literals
import gui
import wx
import os.path
import re

import addonHandler
addonHandler.initTranslation()
import config
import louis

from collections import namedtuple
from . import configBE
from . import utils


BrailleDictEntry = namedtuple("BrailleDictEntry", ("opcode", "textPattern", "braillePattern", "direction", "comment"))
OPCODE_SIGN = "sign"
OPCODE_MATH = "math"
OPCODE_REPLACE = "replace"
OPCODE_LABELS = {
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_SIGN: _("Sign"),
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_MATH: _("Math"),
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_REPLACE: _("Replace"),
}
OPCODE_LABELS_ORDERING = (OPCODE_SIGN, OPCODE_MATH, OPCODE_REPLACE)

DIRECTION_BOTH = "both"
DIRECTION_BACKWARD = "nofor"
DIRECTION_FORWARD = "noback"
DIRECTION_LABELS = {
	DIRECTION_BOTH: _("Both (input and output)"),
	DIRECTION_BACKWARD: _("Backward (input only)"),
	DIRECTION_FORWARD: _("Forward (output only)")
}
DIRECTION_LABELS_ORDERING = (DIRECTION_BOTH, DIRECTION_FORWARD, DIRECTION_BACKWARD)

dictTables = []
invalidDictTables = set()

def checkTable(path):
	global invalidDictTables
	try:
		louis.checkTable([path])
		return True
	except RuntimeError: invalidDictTables.add(path)
	return False

def getValidPathsDict():
	types = ["default", "table", "tmp"]
	paths = [getPathDict(type_) for type_ in types]
	valid = lambda path: os.path.exists(path) and os.path.isfile(path) and checkTable(path)
	return [path for path in paths if valid(path)]

def getPathDict(type_):
	if type_ == "table": path = os.path.join(configBE.configDir, "brailleDicts", config.conf["braille"]["translationTable"])
	elif type_ == "tmp": path = os.path.join(configBE.configDir, "brailleDicts", "tmp")
	else: path = os.path.join(configBE.configDir, "brailleDicts", "default")
	return "%s.cti" % path

def getDictionary(type_):
	path = getPathDict(type_)
	if not os.path.exists(path): return False, []
	out = []
	with open(path, "rb") as f:
		for line in f:
			line = line.decode("UTF-8")
			line = line.replace(" ", "	").replace("		", "	").replace("		", "	").strip().split("	", 4)
			if line[0].lower().strip() not in [DIRECTION_BACKWARD, DIRECTION_FORWARD]: line.insert(0, DIRECTION_BOTH)
			if len(line) < 4: continue
			if len(line) == 4: line.append("")
			out.append(BrailleDictEntry(line[1], line[2], line[3], line[0], ' '.join(line[4:]).replace("	", " ")))
	return True, out

def saveDict(type_, dict_):
	path = getPathDict(type_)
	f = open(path, "wb")
	for entry in dict_:
		direction = entry.direction if entry.direction != "both" else ''
		line = ("%s	%s	%s	%s	%s" % (direction, entry.opcode, entry.textPattern, entry.braillePattern, entry.comment)).strip()+"\n"
		f.write(line.encode("UTF-8"))
	f.write('\n'.encode("UTF-8"))
	f.close()
	return True

def setDictTables():
	global dictTables
	invalidDictTables.clear()
	dictTables = getValidPathsDict()
	if hasattr(louis.liblouis, "lou_free"): louis.liblouis.lou_free()
	else: return False
	return True

def notifyInvalidTables():
	if invalidDictTables:
		dicts = {
			getPathDict("default"): "default",
			getPathDict("table"): "table",
			getPathDict("tmp"): "tmp"
		}
		msg = _("One or more errors are present in dictionaries tables. Concerned dictionaries: %s. As a result, these dictionaries are not loaded." % ", ".join([dicts[path] for path in invalidDictTables if path in dicts]))
		wx.CallAfter(gui.messageBox, msg, _("Braille Extender"), wx.OK|wx.ICON_ERROR)

def removeTmpDict():
	path = getPathDict("tmp")
	if os.path.exists(path): os.remove(path)

setDictTables()
notifyInvalidTables()

class DictionaryDlg(gui.settingsDialogs.SettingsDialog):

	def __init__(self, parent, title, type_):
		self.title = title
		self.type_ = type_
		self.tmpDict = getDictionary(type_)[1]
		super(DictionaryDlg, self).__init__(parent, hasApplyButton=True)

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: The label for the combo box of dictionary entries in speech dictionary dialog.
		entriesLabelText = _("&Dictionary entries")
		self.dictList = sHelper.addLabeledControl(entriesLabelText, wx.ListCtrl, style=wx.LC_REPORT|wx.LC_SINGLE_SEL,size=(550,350))
		# Translators: The label for a column in dictionary entries list used to identify comments for the entry.
		self.dictList.InsertColumn(0, _("Comment"), width=150)
		# Translators: The label for a column in dictionary entries list used to identify original character.
		self.dictList.InsertColumn(1, _("Text pattern"),width=150)
		# Translators: The label for a column in dictionary entries list and in a list of symbols from symbol pronunciation dialog used to identify replacement for a pattern or a symbol
		self.dictList.InsertColumn(2, _("Braille pattern"),width=150)
		# Translators: The label for a column in dictionary entries list used to identify whether the entry is a sign, math, replace
		self.dictList.InsertColumn(4, _("Opcode"),width=50)
		# Translators: The label for a column in dictionary entries list used to identify whether the entry is a sign, math, replace
		self.dictList.InsertColumn(5, _("Direction"),width=50)
		for entry in self.tmpDict:
			direction = DIRECTION_LABELS[entry[3]] if len(entry) >= 4 and entry[3] in DIRECTION_LABELS else "both"
			self.dictList.Append((
				entry.comment,
				self.getReprTextPattern(entry.textPattern),
				self.getReprBraillePattern(entry.braillePattern),
				entry.opcode,
				direction
			))
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in speech dictionaries dialog to add new entries.
			label=_("&Add")
		).Bind(wx.EVT_BUTTON, self.OnAddClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in speech dictionaries dialog to edit existing entries.
			label=_("&Edit")
		).Bind(wx.EVT_BUTTON, self.OnEditClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in speech dictionaries dialog to remove existing entries.
			label=_("&Remove")
		).Bind(wx.EVT_BUTTON, self.OnRemoveClick)

		sHelper.addItem(bHelper)

	@staticmethod
	def getReprTextPattern(textPattern):
		if re.match(r"^\\x[0-8a-f]+$", textPattern, re.IGNORECASE):
			textPattern = textPattern.lower()
			textPattern = chr(int(''.join([c for c in textPattern if c in "abcdef1234567890"]), 16))
		if len(textPattern) == 1: return "%s (%s)" % (textPattern, hex(ord(textPattern)).replace("0x", r"\x"))
		return textPattern

	@staticmethod
	def getReprBraillePattern(braillePattern):
		if re.match("^[0-8\-]+$", braillePattern):
			return "%s (%s)" % (utils.descriptionToUnicodeBraille(braillePattern), braillePattern)
		return braillePattern

	def OnAddClick(self, evt):
		entryDialog = DictionaryEntryDlg(self,title=_("Add Dictionary Entry"))
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.dictEntry
			self.tmpDict.append(entry)
			direction = DIRECTION_LABELS[entry[3]] if len(entry)>=4 and entry[3] in DIRECTION_LABELS else "both"
			comment = entry[4] if len(entry)==5 else ''
			self.dictList.Append((
				comment,
				self.getReprTextPattern(entry.textPattern),
				self.getReprBraillePattern(entry.braillePattern),
				entry.opcode,
				direction
			))
			index = self.dictList.GetFirstSelected()
			while index >= 0:
				self.dictList.Select(index,on=0)
				index=self.dictList.GetNextSelected(index)
			addedIndex = self.dictList.GetItemCount()-1
			self.dictList.Select(addedIndex)
			self.dictList.Focus(addedIndex)
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def OnEditClick(self, evt):
		if self.dictList.GetSelectedItemCount() != 1: return
		editIndex = self.dictList.GetFirstSelected()
		entryDialog = DictionaryEntryDlg(self)
		entryDialog.textPatternTextCtrl.SetValue(self.tmpDict[editIndex].textPattern)
		entryDialog.braillePatternTextCtrl.SetValue(self.tmpDict[editIndex].braillePattern)
		entryDialog.commentTextCtrl.SetValue(self.tmpDict[editIndex].comment)
		entryDialog.setOpcode(self.tmpDict[editIndex].opcode)
		entryDialog.setDirection(self.tmpDict[editIndex].direction)
		if entryDialog.ShowModal() == wx.ID_OK:
			self.tmpDict[editIndex] = entryDialog.dictEntry
			entry = entryDialog.dictEntry
			direction = DIRECTION_LABELS[entry.direction] if len(entry) >= 4 and entry.direction in DIRECTION_LABELS else "both"
			self.dictList.SetItem(editIndex, 0, entry.comment)
			self.dictList.SetItem(editIndex, 1, self.getReprTextPattern(entry.textPattern))
			self.dictList.SetItem(editIndex, 2, self.getReprBraillePattern(entry.braillePattern))
			self.dictList.SetItem(editIndex, 3, entry.opcode)
			self.dictList.SetItem(editIndex, 4, direction)
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def OnRemoveClick(self,evt):
		index = self.dictList.GetFirstSelected()
		while index>=0:
			self.dictList.DeleteItem(index)
			del self.tmpDict[index]
			index = self.dictList.GetNextSelected(index)
		self.dictList.SetFocus()

	def onApply(self, evt):
		res = saveDict(self.type_, self.tmpDict)
		if not setDictTables(): notImplemented(_("Please restart NVDA to apply these changes"))
		if res: super(DictionaryDlg, self).onApply(evt)
		else: notImplemented("Error during writing file, more info in log.")
		notifyInvalidTables()
		self.dictList.SetFocus()

	def onOk(self, evt):
		res = saveDict(self.type_, self.tmpDict)
		if not setDictTables(): notImplemented(_("Please restart NVDA to apply these changes"))
		notifyInvalidTables()
		if res: super(DictionaryDlg, self).onOk(evt)
		else: notImplemented("Error during writing file, more info in log.")
		notifyInvalidTables()

class DictionaryEntryDlg(wx.Dialog):
	# Translators: This is the label for the edit dictionary entry dialog.
	def __init__(self, parent=None, title=_("Edit Dictionary Entry"), textPattern='', specifyDict=False):
		super(DictionaryEntryDlg, self).__init__(parent, title=title)
		mainSizer=wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		if specifyDict:
			# Translators: This is a label for an edit field in add dictionary entry dialog.
			dictText = _("Dictionary")
			outTable = configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])]
			dictChoices = ["Global", "Table (%s)" % outTable, "Temporary"]
			self.dictRadioBox = sHelper.addItem(wx.RadioBox(self, label=dictText, choices=dictChoices))
			self.dictRadioBox.SetSelection(1)

		# Translators: This is a label for an edit field in add dictionary entry dialog.
		patternLabelText = _("&Text pattern")
		self.textPatternTextCtrl = sHelper.addLabeledControl(patternLabelText, wx.TextCtrl)
		if textPattern: self.textPatternTextCtrl.SetValue(textPattern)

		# Translators: This is a label for an edit field in add dictionary entry dialog and in punctuation/symbol pronunciation dialog.
		braillePatternLabelText = _("&Braille pattern")
		self.braillePatternTextCtrl = sHelper.addLabeledControl(braillePatternLabelText, wx.TextCtrl)

		# Translators: This is a label for an edit field in add dictionary entry dialog.
		commentLabelText = _("&Comment")
		self.commentTextCtrl=sHelper.addLabeledControl(commentLabelText, wx.TextCtrl)

		# Translators: This is a label for a set of radio buttons in add dictionary entry dialog.
		opcodeText = _("&Opcode")
		opcodeChoices = [OPCODE_LABELS[i] for i in OPCODE_LABELS_ORDERING]
		self.opcodeRadioBox = sHelper.addItem(wx.RadioBox(self, label=opcodeText, choices=opcodeChoices))

		# Translators: This is a label for a set of radio buttons in add dictionary entry dialog.
		directionText = _("&Direction")
		directionChoices = [DIRECTION_LABELS[i] for i in DIRECTION_LABELS_ORDERING]
		self.directionRadioBox = sHelper.addItem(wx.RadioBox(self, label=directionText, choices=directionChoices))

		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))

		mainSizer.Add(sHelper.sizer,border=20,flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.setOpcode(OPCODE_SIGN)
		toFocus = self.dictRadioBox if specifyDict else self.textPatternTextCtrl
		toFocus.SetFocus()
		self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)

	def getOpcode(self):
		opcodeRadioValue = self.opcodeRadioBox.GetSelection()
		if opcodeRadioValue == wx.NOT_FOUND: return OPCODE_SIGN
		return OPCODE_LABELS_ORDERING[opcodeRadioValue]

	def getDirection(self):
		directionRadioValue = self.directionRadioBox.GetSelection()
		if directionRadioValue == wx.NOT_FOUND: return DIRECTION_BOTH
		return DIRECTION_LABELS_ORDERING[directionRadioValue]

	def onOk(self, evt):
		textPattern = self.textPatternTextCtrl.GetValue()
		textPattern = textPattern.replace("\t", r"\t").replace(" ", r"\s")
		newEntry = BrailleDictEntry(self.getOpcode(), textPattern, self.braillePatternTextCtrl.GetValue(), self.getDirection(), self.commentTextCtrl.GetValue())
		save = True if hasattr(self, "dictRadioBox") else False
		if save:
			dicts = ["default", "table", "tmp"]
			type_ = dicts[self.dictRadioBox.GetSelection()]
			dict_ = getDictionary(type_)[1]
			dict_.append(newEntry)
			saveDict(type_, dict_)
			self.Destroy()
			setDictTables()
			notifyInvalidTables()
		else: self.dictEntry = newEntry
		evt.Skip()

	def setOpcode(self, opcode):
		self.opcodeRadioBox.SetSelection(OPCODE_LABELS_ORDERING.index(opcode))

	def setDirection(self, direction):
		self.directionRadioBox.SetSelection(DIRECTION_LABELS_ORDERING.index(direction))
