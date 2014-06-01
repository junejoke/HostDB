#!/usr/bin/env python
#
######################################################################
#
#                  Author: Raymond Jay Bullock
#                  Version: 0.1
#
##################
#
#                  Sumary: 
#                   Set of progress bars/activity bars/spinners
#
######################################################################

import sys

# progress bar
def drawProgressBar(percent, barLen = 20, perLoc = 'r'):
    if isinstance(percent, int):
        percent = float(percent)
    progress = ""
    block = int(round(barLen*percent))
    if block >= 1 and block < barLen:
        block -= 1
        progress = "="*block + ">" + " "*(barLen-block-1)
    else:
        progress = "="*block + " "*(barLen-block)

    if perLoc == "c":
        perLen = len("{0}%".format(int(round(percent * 100))))
        progress = progress[:int(round(barLen / 2) - round(perLen / 2))] + "{0}%".format(int(round(percent * 100))) + progress[int(round(barLen / 2) - round(perLen / 2)) + perLen:]

    if perLoc == 'l':
        perLoc = "{0}% [{1}]".format(int(round(percent * 100)), progress)
    elif perLoc == 'c':
        perLoc = "[{0}]".format(progress)
    else:
        perLoc = "[{0}] {1}%".format(progress, int(round(percent * 100)))
    

    sys.stdout.write("{0}".format(perLoc))
    sys.stdout.flush()

# spinner
def drawSpinner(spinner = 1, direction = 'r'):
    if spinner == 1:
        sys.stdout.write("[-]")
    elif spinner == 2:
        sys.stdout.write("[\]")
    elif spinner == 3:
        sys.stdout.write("[|]")
    elif spinner == 4:
        sys.stdout.write("[/]")

    if direction in ['r','f']:
        spinner += 1
        if spinner > 4: spinner = 1
    elif direction == 'l':
        spinner -= 1
        if spinner < 1: spinner = 4

    sys.stdout.flush()
    return spinner
