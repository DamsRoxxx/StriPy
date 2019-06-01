import cherrypy
import logging
import os
import re
import sys
import sqlite3
import threading
import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader
from cherrypy.lib import static
from stripy.library import *

# Initialize environment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
JINJA_ENV 	= Environment(loader=FileSystemLoader('templates'))
LOG_DIR		= r'log'
LOG_FILE	= os.path.join(LOG_DIR, r'stripy-log')
DATA_DIR	= r'data'

class LibraryRenderer(object):
	library 	= None
	asyncUpdateThread = None

	def __init__(self, library):
		self.library = library
		
	def renderDir(self, id = None):
		title 		= 'Bibliothèques'
		previous 	= '/'
	
		if id:
			dirInfos = library.getDirInfos(id)
			title = dirInfos.title
			if dirInfos.parent_id:
				previous = '/dir/{}'.format(dirInfos.parent_id)
	
		self.template	= JINJA_ENV.get_template('main.html')
		return self.template.render(title=title, previous=previous, items=library.getDirContent(id))
		
	def renderOPDS(self, id = None):
		if not id:
			self.template	= JINJA_ENV.get_template('opds-root.xml')
			return self.template.render()
		elif id == 'all':
			self.template	= JINJA_ENV.get_template('opds-content.xml')
			return self.template.render(items=library.getDirContent())
		else:
			self.template	= JINJA_ENV.get_template('opds-content.xml')
			return self.template.render(items=library.getDirContent(id))

	def sendFile(self, id):
		row = library.getBookInfos(id)
		if row:
			path = row['PATH']
			basename = os.path.basename(path)
			filename, ext = os.path.splitext(basename)
			if 'pdf' in ext:
				return static.serve_file(path, 'application/pdf', 'attachment', basename)
			elif 'epub' in ext:
				return static.serve_file(path, 'application/epub+zip', 'attachment', basename)
			else:
				return static.serve_file(path, 'application/octet-stream', 'attachment', basename)
				
	def asyncUpdate(self):
		library.update()
		self.asyncUpdateThread = None			

	def _cp_dispatch(self, vpath):
		return vpath

	@cherrypy.expose
	def index(self):
		cherrypy.log("------> Index")
		return self.renderDir()

	@cherrypy.expose
	def dir(self, id):
		cherrypy.log("------> Dir")
		return self.renderDir(id)

	@cherrypy.expose
	def book(self, id):
		cherrypy.log("------> Book")
		return self.sendFile(id)

	@cherrypy.expose
	def update(self):
		cherrypy.log("------> Update")
		if not self.asyncUpdateThread:
			cherrypy.log("------> Starting update")
			self.asyncUpdateThread = threading.Thread(target=self.asyncUpdate, args=())
			self.asyncUpdateThread.start();
		else:
			cherrypy.log("------> Update already started!")

	@cherrypy.expose
	def status(self):
		cherrypy.log("------> Status")
		if self.asyncUpdateThread:
			cherrypy.log("------> Updating")
			return 'updating'
		return 'idle'

	@cherrypy.expose(['opds-comics'])
	def opds(self, arg1 = None, arg2 = None, arg3 = None, **params):
		cherrypy.log("------> OPDS(args1={}, args2={})".format(arg1, arg2))
		if not arg2:
			id=arg1
			cherrypy.log("------> OPDS(id={})".format(id))
			if 'groupByFolder' in params:
				cherrypy.log("------> OPDS(id={}) : groupByFolder={}".format(id, params['groupByFolder']))
			if 'latest' in params:
				cherrypy.log("------> OPDS(id={}) : latest={}".format(id, params['latest']))
			if 'displayFiles' in params:
				cherrypy.log("------> OPDS(id={}) : displayFiles={}".format(id, params['displayFiles']))
				
			return self.renderOPDS(id)
		else:
			id=arg2
			return self.sendFile(id)
			

if __name__ == '__main__':
	#*****************************************************************
	# Logging
	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)

	# Create data directories
	if not os.path.isdir(LOG_DIR): os.mkdir(LOG_DIR)

	# Adding file log handleer
	with open(LOG_FILE, 'w'): pass
	fileHandler = logging.FileHandler(LOG_FILE)
	fileHandler.setLevel(logging.DEBUG)
	fileHandler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
	logger.addHandler(fileHandler)

	#*****************************************************************
	# Opening library
	library = Library(DATA_DIR)
	
	#*****************************************************************
	# Start server
	myLibraryRenderer = LibraryRenderer(library)
	cherrypy.config.update({'server.socket_host': '0.0.0.0'})   
	cherrypy.quickstart(myLibraryRenderer, '/', r'stripy-web.conf')