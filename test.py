import sqlite3
import logging
import sys
import os
import rarfile
from stripy.library import *
from PIL import Image

init        = False
logfile     = 'unfe.log'
datadir		= 'data'

#*****************************************************************
# Logging
root = logging.getLogger()
root.setLevel(logging.DEBUG)

# Adding file log handleer
with open(logfile, 'w'): pass
fileHandler = logging.FileHandler(logfile)
fileHandler.setLevel(logging.DEBUG)
fileHandler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
root.addHandler(fileHandler)

# Adding stdout log handler
stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setLevel(logging.INFO)
stdoutHandler.setFormatter(logging.Formatter('%(message)s'))
root.addHandler(stdoutHandler)

library = Library(datadir)
library.addLibraryPath(r'\\Isengard\eBooks\ORDERED\Jeux de Rôle\English\Stormbringer - Elric')
library.addLibraryPath(r'\\Isengard\eBooks\ORDERED\\Comics\Star Wars')
library.addLibraryPath(r'\\Isengard\eBooks\ORDERED\Magazines')
library.update()

'''
rarExtractFirstPage(r'\\Isengard\eBooks\ORDERED\Comics\Star Wars\Star Wars Omnibus - Boba Fett (2010).cbr', 'test.png')
'''
'''
rf = rarfile.RarFile(r'\\Isengard\eBooks\ORDERED\Comics\Star Wars\Star Wars Omnibus - Boba Fett (2010).cbr')
if rf.infolist():
	firstfile 	= rf.infolist()[0]
	filename 	= firstfile.filename
	imgfile 	= rf.open(firstfile)
	
	# Convert to a PIL image
	img = Image.open(imgfile)

	# Resize image
	img.thumbnail((195, 280))

	# Save image
	img.save('test.png')
'''