# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import re


kReBrackets = re.compile('[[\]{}()]')
kReComments = re.compile('(?:#|//).*$|/\*.*?\*/|<!--.*?-->')
kReNumbers = re.compile('0x[0-9a-fA-F]+|\d+')
kReStrings = re.compile(
    r"(\"\"\".*?(?<!\\)\"\"\")|('''.*?(?<!\\)''')|(\".*?(?<!\\)\")|('.*?(?<!\\)')")
kReWordBoundary = re.compile('(?:\w+)|(?:\W+)')


# No selection.
kSelectionNone = 0
# Entire document selected.
kSelectionAll = 1
# A rectangular block selection.
kSelectionBlock = 2
# Character by character selection.
kSelectionCharacter = 3
# Select whole lines.
kSelectionLine = 4
# Select whole words.
kSelectionWord = 5
# How many selection modes are there.
kSelectionModeCount = 6

kSelectionModeNames = [
  'None',
  'All',
  'Block',
  'Char',
  'Line',
  'Word',
];


class Selectable:
  def __init__(self):
    self.lines = []
    self.cursorRow = 0
    self.cursorCol = 0
    self.goalCol = 0
    self.markerRow = 0
    self.markerCol = 0
    self.markerEndRow = 0
    self.markerEndCol = 0
    self.selectionMode = kSelectionNone

  def selection(self):
    return (self.cursorRow, self.cursorCol, self.markerRow, self.markerCol)

  def selectionModeName(self):
    return kSelectionModeNames[self.selectionMode]

  def setSelection(self, other):
    (self.cursorRow, self.cursorCol, self.markerRow, self.markerCol,
        self.markerEndRow, self.markerEndCol,
        self.selectionMode) = other

  def getSelectedText(self):
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
    return self.getText(upperRow, upperCol, lowerRow, lowerCol)

  def getText(self, upperRow, upperCol, lowerRow, lowerCol):
    lines = []
    if self.selectionMode == kSelectionAll:
      lines = self.lines[:]
    elif self.selectionMode == kSelectionBlock:
      for i in range(upperRow, lowerRow+1):
        lines.append(self.lines[i][upperCol:lowerCol])
    elif (self.selectionMode == kSelectionCharacter or
        self.selectionMode == kSelectionWord):
      if upperRow == lowerRow:
        lines.append(self.lines[upperRow][upperCol:lowerCol])
      else:
        for i in range(upperRow, lowerRow+1):
          if i == upperRow:
            lines.append(self.lines[i][upperCol:])
          elif i == lowerRow:
            lines.append(self.lines[i][:lowerCol])
          else:
            lines.append(self.lines[i])
    elif self.selectionMode == kSelectionLine:
      for i in range(upperRow, lowerRow+1):
        lines.append(self.lines[i])
    return tuple(lines)

  def doDeleteSelection(self):
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
    self.prg.log('doDelete', upperRow, upperCol, lowerRow, lowerCol)
    if self.selectionMode == kSelectionAll:
      self.lines = [""]
    elif self.selectionMode == kSelectionBlock:
      for i in range(upperRow, lowerRow+1):
        line = self.lines[i]
        self.lines[i] = line[:upperCol] + line[lowerCol:]
    elif (self.selectionMode == kSelectionCharacter or
        self.selectionMode == kSelectionWord):
      if upperRow == lowerRow:
        line = self.lines[upperRow]
        self.lines[upperRow] = line[:upperCol] + line[lowerCol:]
      elif upperCol == 0 and lowerCol == 0:
        del self.lines[upperRow:lowerRow]
      else:
        self.lines[upperRow] = (self.lines[upperRow][:upperCol] +
            self.lines[lowerRow][lowerCol:])
        upperRow += 1
        del self.lines[upperRow:lowerRow+1]
    elif self.selectionMode == kSelectionLine:
      if lowerRow+1 == len(self.lines):
        self.lines.append('')
      del self.lines[upperRow:lowerRow+1]

  def insertLines(self, lines):
    if len(lines) == 0:
      return
    lines = list(lines)
    if self.selectionMode == kSelectionAll:
      self.lines = lines
      return
    lines.reverse()
    if (self.selectionMode == kSelectionNone or
        self.selectionMode == kSelectionCharacter or
        self.selectionMode == kSelectionWord):
      firstLine = self.lines[self.cursorRow]
      if len(lines) == 1:
        self.lines[self.cursorRow] = (firstLine[:self.cursorCol] + lines[0] +
            firstLine[self.cursorCol:])
      else:
        self.lines[self.cursorRow] = (firstLine[:self.cursorCol] +
            lines[-1])
        row = self.cursorRow + 1
        self.lines.insert(row,
            lines[0] + firstLine[self.cursorCol:])
        for line in lines[1:-1]:
          self.lines.insert(row, line)
    elif self.selectionMode == kSelectionBlock:
      for line in lines:
        self.lines[self.cursorRow] = (
            self.lines[self.cursorRow][:self.cursorCol] + line +
            self.lines[self.cursorRow][self.cursorCol:])
    elif self.selectionMode == kSelectionLine:
      self.prg.log('insertLines', self.cursorRow, len(lines))
      if (self.cursorRow == len(self.lines)-1 and
          len(self.lines[-1]) == 0):
        self.lines = self.lines[:-1]
      for line in lines:
        self.lines.insert(self.cursorRow, line)
    else:
      self.prg.log('selection mode not recognized', self.selectionMode)

  def extendWords(self, upperRow, upperCol, lowerRow, lowerCol):
    line = self.lines[upperRow]
    for segment in re.finditer(kReWordBoundary, line):
      if segment.start() <= upperCol < segment.end():
        upperCol = segment.start()
        break
    line = self.lines[lowerRow]
    for segment in re.finditer(kReWordBoundary, line):
      if segment.start() < lowerCol < segment.end():
        lowerCol = segment.end()
        break
    return upperCol, lowerCol

  def extendSelection(self):
    if self.selectionMode == kSelectionNone:
      return (0, 0, 0, -self.markerRow,
          -self.markerCol, 0)
    elif self.selectionMode == kSelectionAll:
      if len(self.lines):
        return (len(self.lines)-1-self.cursorRow,
            len(self.lines[-1])-self.cursorCol,
            len(self.lines[-1])-self.goalCol,
            -self.markerRow, -self.markerCol, 0)
    elif self.selectionMode == kSelectionLine:
      return (0, -self.cursorCol, -self.goalCol,
          0, -self.markerCol, 0)
    elif self.selectionMode == kSelectionWord:
      if self.cursorRow > self.markerRow or (
          self.cursorRow == self.markerRow and
          self.cursorCol > self.markerCol):
        upperCol, lowerCol = self.extendWords(self.markerRow,
            self.markerCol, self.cursorRow, self.cursorCol)
        return (0,
            lowerCol-self.cursorCol,
            lowerCol-self.goalCol,
            0, upperCol-self.markerCol, 0)
      else:
        upperCol, lowerCol = self.extendWords(self.cursorRow,
            self.cursorCol, self.markerRow, self.markerCol)
        return (0,
            upperCol-self.cursorCol,
            upperCol-self.goalCol,
            0, lowerCol-self.markerCol, 0)

  def startAndEnd(self):
    """Get the marker and cursor pair as the ealier of the two then the later
    of the two. The result accounts for the current selection mode."""
    upperRow = 0
    upperCol = 0
    lowerRow = 0
    lowerCol = 0
    if self.selectionMode == kSelectionNone:
      upperRow = self.cursorRow
      upperCol = self.cursorCol
      lowerRow = self.cursorRow
      lowerCol = self.cursorCol
    elif self.selectionMode == kSelectionAll:
      upperRow = 0
      upperCol = 0
      lowerRow = len(self.lines)
      lowerCol = lowerRow and len(self.lines[-1])
    elif self.selectionMode == kSelectionBlock:
      upperRow = min(self.markerRow, self.cursorRow)
      upperCol = min(self.markerCol, self.cursorCol)
      lowerRow = max(self.markerRow, self.cursorRow)
      lowerCol = max(self.markerCol, self.cursorCol)
    elif self.selectionMode == kSelectionCharacter:
      upperRow = self.markerRow
      upperCol = self.markerCol
      lowerRow = self.cursorRow
      lowerCol = self.cursorCol
      if upperRow == lowerRow and upperCol > lowerCol:
        upperCol, lowerCol = lowerCol, upperCol
      elif upperRow > lowerRow:
        upperRow, lowerRow = lowerRow, upperRow
        upperCol, lowerCol = lowerCol, upperCol
    elif self.selectionMode == kSelectionLine:
      upperRow = min(self.markerRow, self.cursorRow)
      upperCol = 0
      lowerRow = max(self.markerRow, self.cursorRow)
      lowerCol = 0
    elif self.selectionMode == kSelectionWord:
      upperRow = self.markerRow
      upperCol = self.markerCol
      lowerRow = self.cursorRow
      lowerCol = self.cursorCol
      if upperRow == lowerRow and upperCol > lowerCol:
        upperCol, lowerCol = lowerCol, upperCol
      elif upperRow > lowerRow:
        upperRow, lowerRow = lowerRow, upperRow
        upperCol, lowerCol = lowerCol, upperCol
    #self.prg.log('start and end', upperRow, upperCol, lowerRow, lowerCol)
    return (upperRow, upperCol, lowerRow, lowerCol)