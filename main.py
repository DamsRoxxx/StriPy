import cherrypy
import cherrypy.process.plugins
import logging
import os
import re
import sys
import sqlite3
import threading
import datetime
import time
from stat import S_ISREG, ST_CTIME, ST_MODE
import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader
from cherrypy.lib import static
from stripy.library import *
from stripy.ebook import *
from stripy.dict import *

# Initialize environment
CLEANING_PERIOD = 3600
CURRENT_DIR 	= os.path.dirname(os.path.abspath(__file__))
JINJA_ENV 		= Environment(loader=FileSystemLoader('templates'))
LOG_DIR			= os.path.join(CURRENT_DIR, r'log')
LOG_FILE		= os.path.join(LOG_DIR, r'stripy-log')
DATA_DIR		= os.path.join(CURRENT_DIR, r'data')
COVER_DIR		= os.path.join(DATA_DIR, r'covers')
TMP_DIR			= os.path.join(DATA_DIR, r'tmp')
OPDS_ROOT		= '/opds-comics/'
OPDS_COMICS_ROOT = '/opds-comics/comics/'
OPDS_COMICREADER_ROOT = '/opds-comics/comicreader/'

class WebLibrary(object):
	library 	= None
	asyncUpdateThread = None

	def __init__(self, library):
		self.library = library
		
	def renderDir(self, id = None):
		title 		= 'StriPy'
		section		= 'Libraries'
		previous 	= '/'
	
		if id:
			dirInfos = library.getDirInfos(id)
			title 	= dirInfos.title
			section = dirInfos.title
			if dirInfos.parent_id:
				previous = '/dir/{}'.format(dirInfos.parent_id)
	
		self.template	= JINJA_ENV.get_template('main.html')
		return self.template.render(title=title, section=section, previous=previous, items=library.getDirContent(id))
		
	def renderReader(self, id):
		row = library.getBookInfos(id)
		if row:
			if 'epub' in row['EXT']:
				self.template	= JINJA_ENV.get_template('epub.html')
				return self.template.render(id=row['ID'], directory_id=row['DIRECTORY_ID'], title=row['TITLE'], page_count=row['PAGE_COUNT'], filename=row['FILENAME'], comicreader_root=OPDS_COMICREADER_ROOT)
			else:
				self.template	= JINJA_ENV.get_template('reader.html')
				return self.template.render(id=row['ID'], directory_id=row['DIRECTORY_ID'], title=row['TITLE'], page_count=row['PAGE_COUNT'], comicreader_root=OPDS_COMICREADER_ROOT)

	def sendFile(self, id):
		row = library.getBookInfos(id)
		if row:
			path = row['PATH']
			basename = os.path.basename(path)
			filename, ext = os.path.splitext(basename)
			if 'pdf' in ext:
				return static.serve_file(path, 'application/pdf', 'inline', basename)
			elif 'epub' in ext:
				return static.serve_file(path, 'application/epub+zip', 'inline', basename)
			else:
				return static.serve_file(path, 'application/octet-stream', 'inline', basename)
				
	def asyncUpdate(self):
		library.update()
		self.asyncUpdateThread = None			

	def _cp_dispatch(self, vpath):
		return vpath

	@cherrypy.expose
	def index(self):
		logging.debug("Index")
		return self.renderDir()

	@cherrypy.expose
	def dir(self, id):
		logging.debug("Dir")
		return self.renderDir(id)

	@cherrypy.expose
	def book(self, id):
		logging.debug("Book")
		return self.renderReader(id)

	@cherrypy.expose
	def download(self, id):
		logging.debug("Download")
		return self.sendFile(id)

	@cherrypy.expose
	def epub(self, id, filename):
		self.template	= JINJA_ENV.get_template('epub.html')
		logging.debug("EPUB")
		return self.sendFile(id)

	@cherrypy.expose
	def update(self):
		logging.debug("Update")
		if not self.asyncUpdateThread:
			logging.debug("Starting update")
			self.asyncUpdateThread = threading.Thread(target=self.asyncUpdate, args=())
			self.asyncUpdateThread.start();
		else:
			logging.debug("Update already started!")

	@cherrypy.expose
	def status(self):
		logging.debug("Status")
		if self.asyncUpdateThread:
			logging.debug("Updating")
			return 'updating'
		return 'idle'

@cherrypy.expose
class UbooquityOPDSLibrary(object):
	library 	= None

	def __init__(self, library):
		self.library = library		
	
	@cherrypy.tools.accept(media='text/plain')
	def GET(self, id = None, **params):
		logging.debug("UbooquityOPDSLibrary(id={})".format(id))
		if 'groupByFolder' in params:
			logging.debug("UbooquityOPDSLibrary(id={}) : groupByFolder={}".format(id, params['groupByFolder']))
		if 'latest' in params:
			logging.debug("UbooquityOPDSLibrary(id={}) : latest={}".format(id, params['latest']))
		if 'displayFiles' in params:
			logging.debug("UbooquityOPDSLibrary(id={}) : displayFiles={}".format(id, params['displayFiles']))

		if not id:
			self.template	= JINJA_ENV.get_template('opds-root.xml')
			return self.template.render(opds_root=OPDS_ROOT, opds_comics_root=OPDS_COMICS_ROOT, opds_comicreader_root=OPDS_COMICREADER_ROOT)
		elif id == 'all':
			self.template	= JINJA_ENV.get_template('opds-content.xml')
			return self.template.render(opds_root=OPDS_ROOT, opds_comics_root=OPDS_COMICS_ROOT, opds_comicreader_root=OPDS_COMICREADER_ROOT, items=library.getDirContent())
		else:
			self.template	= JINJA_ENV.get_template('opds-content.xml')
			return self.template.render(opds_root=OPDS_ROOT, opds_comics_root=OPDS_COMICS_ROOT, opds_comicreader_root=OPDS_COMICREADER_ROOT, items=library.getDirContent(id))

	def POST(self, length=8):
		return

	def PUT(self, another_string):
		return

	def DELETE(self):
		return
		
@cherrypy.expose
class UbooquityOPDSBook(object):
	library 	= None

	def __init__(self, library):
		self.library = library		
	
	@cherrypy.tools.accept(media='text/plain')
	def GET(self, id, file, **params):
		logging.debug("UbooquityOPDSBook(id={}, file={})".format(id, file))
		for param in params:
			logging.debug("UbooquityOPDSBook(id={}, file={}) param={}".format(id, file, param))
			
		if 'cover' in params:
			logging.debug("UbooquityOPDSBook(id={}) : cover={}".format(id, params['cover']))
			if 'true' == params['cover']:
				coverfile = '{}{}'.format(id, Library.THUMBIMG_EXT)
				coverpath = os.path.join(COVER_DIR, coverfile)
				logging.debug("UbooquityOPDSBook(id={}) : coverpath={}".format(id, coverpath))
				if os.path.isfile(coverpath):
					logging.debug("UbooquityOPDSBook(id={}) : coverpath={} serving...".format(id, coverpath))
					return static.serve_file(coverpath, 'image/jpeg', 'inline', coverfile)
				else:
					logging.debug("UbooquityOPDSBook(id={}) : coverpath={} not found!".format(id, coverpath))
		else:
			row = library.getBookInfos(id)
			if row:
				path = row['PATH']
				basename = os.path.basename(path)
				filename, ext = os.path.splitext(basename)
				logging.debug("UbooquityOPDSBook(id={}) : file={} serving...".format(id, path))
				if 'pdf' in ext:
					return static.serve_file(path, 'application/pdf', 'inline', basename)
				elif 'epub' in ext:
					return static.serve_file(path, 'application/epub+zip', 'inline', basename)
				else:
					return static.serve_file(path, 'application/octet-stream', 'inline', basename)		

	def POST(self, length=8):
		return

	def PUT(self, another_string):
		return

	def DELETE(self):
		return

@cherrypy.expose
class UbooquityOPDSReader(object):
	library 	= None
	cache		= CacheDict(size=10, timeout=600)

	def __init__(self, library):
		self.library = library		
	
	@cherrypy.tools.accept(media='text/plain')
	def GET(self, id, **params):
		logging.debug("UbooquityOPDSReader(id={})".format(id))
		row = library.getBookInfos(id)
		if row:
			ebookfile 	= None
			path 		= row['PATH']
			page 		= 0
			width 		= Library.THUMB_WIDTH
			
			# Cache ebook file
			if path in self.cache:
				ebookfile = self.cache.get(path)
			else:
				ebookfile 			= eBook.Open(path)
				self.cache[path] 	= ebookfile
				
			# Handle parameters
			if 'page' in params:
				page = int(params['page'])
				logging.debug("UbooquityOPDSReader(id={}) : page={}".format(id, page))

			if 'width' in params:
				width = int(params['width'])
				logging.debug("UbooquityOPDSReader(id={}) : width={}".format(id, width))

			page = ebookfile.getPage(page)
			if 'jpeg' in page.type:
				cherrypy.response.headers['Content-Type'] = "image/jpeg"
			elif 'png' in page.type:
				cherrypy.response.headers['Content-Type'] = "image/png"
			elif 'svg' in page.type:
				cherrypy.response.headers['Content-Type'] = "image/svg+xml"
			return cherrypy.lib.file_generator(page.fp)
				
	def POST(self, length=8):
		return

	def PUT(self, another_string):
		return

	def DELETE(self):
		return
		
def CleanTmp():
	logging.info('Removing old cached images (older than {} seconds) from \'{}\'...'.format(CLEANING_PERIOD, TMP_DIR))

	# get all entries in the directory w/ stats
	entries = (os.path.join(TMP_DIR, fn) for fn in os.listdir(TMP_DIR))
	entries = ((os.stat(path), path) for path in entries)

	# leave only regular files, insert creation date
	entries = ((stat[ST_CTIME], path)
			   for stat, path in entries if S_ISREG(stat[ST_MODE]))
	#NOTE: on Windows `ST_CTIME` is a creation date 
	#  but on Unix it could be something else
	#NOTE: use `ST_MTIME` to sort by a modification date

	# foreach file
	for cdate, path in sorted(entries):
		filedate = datetime.datetime.strptime(time.ctime(cdate), "%a %b %d %H:%M:%S %Y")
		if filedate < (datetime.datetime.now() - datetime.timedelta(seconds=CLEANING_PERIOD)):
			logging.debug('Removing old file ({}) \'{}\'...'.format(filedate, path))
			try:
				os.remove(path)
			except:
				logging.error('Error while trying to remove old file \'{}\'!'.format(path))
		else:
			# Exist as there is no old file
			return

if __name__ == '__main__':
	# Create directories
	if not os.path.isdir(LOG_DIR): 		os.mkdir(LOG_DIR)
	if not os.path.isdir(DATA_DIR): 	os.mkdir(DATA_DIR)
	if not os.path.isdir(COVER_DIR): 	os.mkdir(COVER_DIR)
	if not os.path.isdir(TMP_DIR): 		os.mkdir(TMP_DIR)

	#*****************************************************************
	# Logging
	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)

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
	# Configuration
	opds_conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'text/xml')],
        }
    }

	cherrypy.config.update(r'stripy-global.conf')   
	cherrypy.tree.mount(WebLibrary(library), '/', r'stripy-web.conf')
	cherrypy.tree.mount(UbooquityOPDSLibrary(library), OPDS_ROOT, opds_conf)
	cherrypy.tree.mount(UbooquityOPDSBook(library), OPDS_COMICS_ROOT, opds_conf)
	cherrypy.tree.mount(UbooquityOPDSReader(library), OPDS_COMICREADER_ROOT, opds_conf)
	
	#*****************************************************************
	# Start background tasks
	CleanTmp()
	tmpCleaner = cherrypy.process.plugins.BackgroundTask(CLEANING_PERIOD, CleanTmp)
	tmpCleaner.start()

	#*****************************************************************
	# Start server
	if hasattr(cherrypy.engine, 'block'):
		# 3.1 syntax
		cherrypy.engine.start()
		cherrypy.engine.block()
	else:
		# 3.0 syntax
		cherrypy.server.quickstart()
		cherrypy.engine.start()

	#*****************************************************************
	# Stop background tasks
	tmpCleaner.cancel()