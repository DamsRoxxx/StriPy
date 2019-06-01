# coding=UTF-8
import collections
import sqlite3
import logging
import os
import fitz
import rarfile
from PIL import Image

IMG_WIDTH 	= 195
IMG_HEIGHT 	= 280

def fitzRenderFirstPage(filePath, imgPath):
	global IMG_WIDTH
	global IMG_HEIGHT

	# Render with PyMuPDF
	doc 	= fitz.open(filePath)
	page 	= doc.loadPage(0)
	pix 	= page.getPixmap()

	# Convert to a PIL image
	img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
	
	# Resize image
	img.thumbnail((IMG_WIDTH, IMG_HEIGHT))

	# Save image
	img.convert('RGB').save(imgPath)
	
def rarExtractFirstPage(filePath, imgPath):
	global IMG_WIDTH
	global IMG_HEIGHT
	
	# Open with rarfile
	rf = rarfile.RarFile(filePath)
	
	# If there is content
	if rf.infolist():
		# open first file
		imgfile 	= rf.open(rf.infolist()[0])
		
		# Convert to a PIL image
		img = Image.open(imgfile)

		# Resize image
		img.thumbnail((IMG_WIDTH, IMG_HEIGHT))

		# Save image
		img.save(imgPath)


class Library:
	SCHEMA = 'schema.sql'
	SUPPORTED_EXT = ['.pdf', '.cbz', '.cbr', '.epub']
	FITZ_SUPPORTED_EXT 	= ['.pdf', '.cbz', '.epub']
	RAR_SUPPORTED_EXT 	= ['.cbr']
	THUMBIMG_EXT		= '.jpg'

	#Library management statements
	INSERT_LIBRARY = 'INSERT INTO LIBRARY (PATH) VALUES (?)'
	SELECT_LIBRARY = 'SELECT ID, PATH FROM LIBRARY'
	DELETE_LIBRARY = 'DELETE FROM LIBRARY WHERE ID = ?'

	# Directory management statements
	SELECT_DIRECTORY = 'SELECT ID FROM DIRECTORY WHERE LIBRARY_ID = ? AND PARENT_ID = ? AND TITLE = ?'
	INSERT_DIRECTORY = 'INSERT INTO DIRECTORY (LIBRARY_ID, PARENT_ID, TITLE, PATH) VALUES (?, ?, ?, ?)'
	DELETE_DIRECTORY = 'DELETE FROM DIRECTORY WHERE ID = ?'
	SELECT_DIRECTORY_NULL = 'SELECT ID FROM DIRECTORY WHERE LIBRARY_ID = ? AND TITLE = ? AND PARENT_ID IS NULL'
	SELECT_DIRECTORY_LIBRARY = 'SELECT ID FROM DIRECTORY WHERE LIBRARY_ID = ?'
	DELETE_DIRECTORY_LIBRARY = 'DELETE FROM DIRECTORY WHERE LIBRARY_ID = ?'
	UPDATE_DIRECTORY = 'UPDATE DIRECTORY SET COVER_ID = ? WHERE ID = ?'
	SELECT_ALL_DIRECTORY = 'SELECT ID, PATH FROM DIRECTORY'
	
	# Book management statements
	SELECT_BOOK = 'SELECT ID FROM BOOK WHERE LIBRARY_ID = ? AND DIRECTORY_ID = ? AND TITLE = ?'
	INSERT_BOOK = 'INSERT INTO BOOK (LIBRARY_ID, DIRECTORY_ID, TITLE, PATH) VALUES (?, ?, ?, ?)'
	DELETE_BOOK = 'DELETE FROM BOOK WHERE ID = ?'
	SELECT_BOOK_DIRECTORY = 'SELECT ID FROM BOOK WHERE DIRECTORY_ID = ?'
	DELETE_BOOK_DIRECTORY = 'DELETE FROM BOOK WHERE DIRECTORY_ID = ?'
	SELECT_BOOK_LIBRARY = 'SELECT ID FROM BOOK WHERE LIBRARY_ID = ?'
	DELETE_BOOK_LIBRARY = 'DELETE FROM BOOK WHERE LIBRARY_ID = ?'
	SELECT_ALL_BOOK = 'SELECT ID, PATH FROM BOOK'
	
	# Content statements
	SELECT_BOOK_INFOS	=	"SELECT ID, TITLE, PATH FROM BOOK WHERE ID = ?"
	SELECT_ROOT_CONTENT = 	"SELECT 'dir' AS TYPE, ID AS ID, TITLE AS TITLE, PATH AS PATH, COVER_ID AS COVER_ID FROM DIRECTORY WHERE PARENT_ID IS NULL \
							UNION \
							SELECT 'book' AS TYPE, ID AS ID, TITLE AS TITLE, PATH AS PATH, COALESCE(ID, 0) AS COVER_ID FROM BOOK WHERE DIRECTORY_ID IS NULL  \
							ORDER BY TITLE"
	SELECT_DIR_CONTENT = 	"SELECT 'dir' AS TYPE, ID AS ID, TITLE AS TITLE, PATH AS PATH, COVER_ID AS COVER_ID FROM DIRECTORY WHERE PARENT_ID = ? \
							UNION \
							SELECT 'book' AS TYPE, ID AS ID, TITLE AS TITLE, PATH AS PATH, COALESCE(ID, 0) FROM BOOK WHERE DIRECTORY_ID = ?  \
							ORDER BY TITLE"

	# Informations statements
	SELECT_DIR_INFOS = 'SELECT ID, PARENT_ID, TITLE FROM DIRECTORY WHERE ID = ?'
	
	# Attributes
	DATABASE_FILE 	= 'database.db'
	COVER_DIR 		= 'covers'
	connection 		= None
	dataPath		= None
	databasePath 	= None
	coverPath 		= None
	
	DirInfos = collections.namedtuple('DirInfos', 'id parent_id title')
	
	def __init__(self, dataPath):
		init = False
		self.dataPath		= dataPath
		self.databasePath 	= os.path.join(dataPath, self.DATABASE_FILE)		
		self.coverPath 		= os.path.join(dataPath, self.COVER_DIR)
		
		# Create data directories
		if not os.path.isdir(self.dataPath): os.mkdir(self.dataPath)
		if not os.path.isdir(self.coverPath): os.mkdir(self.coverPath)
	
		# If the database does not exists
		if not os.path.isfile(self.databasePath):
			init = True
			
		# Open the database
		self.__openDatabase(self.databasePath)

		# Init the schema
		if init:
			try:
				self.__createDatabase()
			except sqlite3.Error as e:
				logging.error('Error while creating database : {}'.format(e.args[0]))
				self.__closeDatabase()
				os.remove(databasePath)				
			except:
				logging.error('Error while creating database \'{}\''.format(databasePath))
				self.__closeDatabase()
				os.remove(databasePath)
				
	def __openDatabase(self, databasePath):
		logging.info('Opening database \'{}\'...'.format(databasePath))
		self.connection = sqlite3.connect(databasePath, check_same_thread=False)
		self.connection.text_factory = str
		self.connection.row_factory = sqlite3.Row

		# Create cursor
		self.cursor = self.connection.cursor()

	def __closeDatabase(self):
		logging.info('Closing database...')
		self.connection.close()

	def __createDatabase(self):
		logging.info('Creating database...')
		with open(self.SCHEMA) as schemaFile:
			cursor = self.connection.cursor()
			sql = schemaFile.read()
			cursor.executescript(sql)
			self.connection.commit()

	def __getDirectoryID(self, libraryID, parentID, title, path):
		logging.debug('Search directory ({}, {}, {})...'.format(libraryID, parentID, title))	
		dirID = None
		cursor = self.connection.cursor()
		
		if parentID:
			cursor.execute(self.SELECT_DIRECTORY, (libraryID, parentID, title))
		else:
			cursor.execute(self.SELECT_DIRECTORY_NULL, (libraryID, title))
		
		row = cursor.fetchone()
		if row:
			dirID = row['ID']
			logging.debug('Directory ({}, {}, {}) found : Id = {}'.format(libraryID, parentID, title, dirID))	
		else:
			cursor.execute(self.INSERT_DIRECTORY, (libraryID, parentID, title, path))
			dirID = cursor.lastrowid
			logging.debug('Directory ({}, {}, {}) created : Id = {}'.format(libraryID, parentID, title, dirID))	
			
		return dirID
					
	def __setDirectoryCover(self, dirID, coverID):
		logging.debug('Setting directory cover ({}, {})...'.format(dirID, coverID))	
		cursor = self.connection.cursor()
		cursor.execute(self.UPDATE_DIRECTORY, (coverID, dirID))

	def __getBookID(self, libraryID, parentID, title, ext, path):
		logging.debug('Search book ({}, {}, {})...'.format(libraryID, parentID, title))	
		bookID = None
		coverID = None
		cursor = self.connection.cursor()		
		cursor.execute(self.SELECT_BOOK, (libraryID, parentID, title))		
		row = cursor.fetchone()
		if row:
			bookID = row['ID']
			logging.debug('Book ({}, {}, {}) found : Id = {}'.format(libraryID, parentID, title, bookID))	
			coverName = '{:d}{}'.format(bookID, self.THUMBIMG_EXT)
			coverPath = os.path.join(self.coverPath, coverName)
			logging.debug('Book ({}, {}, {}) search cover thumb image...'.format(libraryID, parentID, title))	
			if os.path.isfile(coverPath): 
				coverID = bookID
				logging.debug('Book ({}, {}, {}) Cover thumb image = \'{}\''.format(libraryID, parentID, title, coverPath))
			else:
				logging.debug('Book ({}, {}, {}) No cover thumb image \'{}\' found!'.format(libraryID, parentID, title, coverPath))				
		else:
			cursor.execute(self.INSERT_BOOK, (libraryID, parentID, title, path))
			bookID = cursor.lastrowid
			logging.debug('Book ({}, {}, {}) created : Id = {}'.format(libraryID, parentID, title, bookID))	
			
			# TODO : Factorize
			# If format is supported by fitz
			if ext in self.FITZ_SUPPORTED_EXT:
				logging.debug('Book ({}, {}, {}) create cover thumb image with fitz...'.format(libraryID, parentID, title))
				coverID = bookID
				coverName = '{:d}{}'.format(bookID, self.THUMBIMG_EXT)
				coverPath = os.path.join(self.coverPath, coverName)
				logging.debug('Book ({}, {}, {}) Cover thumb image = \'{}\''.format(libraryID, parentID, title, coverPath))
				fitzRenderFirstPage(path, coverPath)
			# If format is supported by rar
			elif ext in self.RAR_SUPPORTED_EXT:
				logging.debug('Book ({}, {}, {}) extract cover thumb image with unrar...'.format(libraryID, parentID, title))
				coverID = bookID
				coverName = '{:d}{}'.format(bookID, self.THUMBIMG_EXT)
				coverPath = os.path.join(self.coverPath, coverName)
				logging.debug('Book ({}, {}, {}) Cover thumb image = \'{}\''.format(libraryID, parentID, title, coverPath))
				rarExtractFirstPage(path, coverPath)
			else:
				logging.debug('Book ({}, {}, {}) Unsupported file format, no thumb image created!'.format(libraryID, parentID, title))
				
				
		return bookID, coverID
		
	def __removeBook(self, bookID):
		logging.debug('Removing book ({})...'.format(bookID))
		cursor = self.connection.cursor()
		cursor.execute(self.DELETE_BOOK, (bookID,))
		self.__removeBookCover(bookID)
	
	def __removeBookCover(self, bookID):
		logging.debug('Removing book cover ({})...'.format(bookID))
		coverName = '{:d}{}'.format(bookID, self.THUMBIMG_EXT)
		coverPath = os.path.join(self.coverPath, coverName)
		
		# Remove cover
		if os.path.isfile(coverPath):
			logging.debug('Removing cover file ''{}''...'.format(coverPath))
			os.remove(coverPath)	

	def __checkBooks(self):
		logging.info('Checking books...')
		cursor = self.connection.cursor()

		try:
			# Select all books from directory
			cursor.execute(self.SELECT_ALL_BOOK)
			
			# Remove each book cover
			row = cursor.fetchone()
			while row is not None:
				bookID = row['ID']
				bookPath = row['PATH']
				logging.debug('Checking book ''{}''...'.format(bookPath))
				
				if not os.path.isfile(bookPath):
					logging.info('Book ''{}'' not found, removing...'.format(bookPath))
					self.__removeBook(bookID)
					
				# Next
				row = cursor.fetchone()			
		except sqlite3.Error as e:
			logging.error('Error while checking books : {}'.format(e.args[0]))
			raise e

	def __removeDirectory(self, directoryID):
		logging.debug('Removing directory ({})...'.format(directoryID))
		cursor = self.connection.cursor()

		try:
			# Select all books from directory
			cursor.execute(self.SELECT_BOOK_DIRECTORY, (directoryID,))
			
			# Remove each book cover
			row = cursor.fetchone()
			while row is not None:
				self.__removeBookCover(row['ID'])				
				row = cursor.fetchone()			
			
			# Delete associated data
			cursor.execute(self.DELETE_BOOK_DIRECTORY, (directoryID,))
			cursor.execute(self.DELETE_DIRECTORY, (directoryID,))
		except sqlite3.Error as e:
			logging.error('Error while removing directory ({})!'.format(directoryID))
			raise e

	def __checkDirectories(self):
		logging.info('Checking directories...')
		cursor = self.connection.cursor()

		try:
			# Select all books from directory
			cursor.execute(self.SELECT_ALL_DIRECTORY)
			
			# Remove each book cover
			row = cursor.fetchone()
			while row is not None:
				dirID = row['ID']
				dirPath = row['PATH']
				logging.debug('Checking directory ''{}''...'.format(dirPath))
				
				if not os.path.isdir(dirPath):
					logging.info('Directory ''{}'' not found, removing...'.format(dirPath))
					self.__removeDirectory(dirID)

				# Next
				row = cursor.fetchone()			
		except sqlite3.Error as e:
			logging.error('Error while checking directories : {}'.format(e.args[0]))
			raise e

	def __scanDirectory(self, libraryID, dirPath, title, parentID = None):
		coverIDs = []
		logging.debug('Scanning directory \'{}\'...'.format(dirPath))	
		if not os.path.isdir(dirPath):
			logging.error('Directory \'{}\' is not valid'.format(dirPath))
			return
					
		dirID = self.__getDirectoryID(libraryID, parentID, title, dirPath)
	
		# Scan directory
		for file in sorted(os.listdir(dirPath)):
			itemCoverID = None
			path = os.path.join(dirPath, file)
			if os.path.isfile(path):
				# Handle book
				filename, ext = os.path.splitext(file)
				if ext in self.SUPPORTED_EXT:
					bookID, itemCoverID = self.__getBookID(libraryID, dirID, filename, ext, path)
				
			elif os.path.isdir(path):
				# Handle dir
				itemCoverID = self.__scanDirectory(libraryID, path, file, dirID)

			# If item has a cover
			if itemCoverID:
				# Append cover
				coverIDs.append(itemCoverID)
		
		# If covers where found
		if coverIDs:
			coverID = coverIDs[0]
			logging.debug('Directory \'{}\' : Cover = {}...'.format(dirPath, coverID))
			self.__setDirectoryCover(dirID, coverID)
			return coverID
		else:
			logging.debug('Directory \'{}\' : No cover!'.format(dirPath))
			self.__setDirectoryCover(dirID, None)
				
		return None

	def __scanLibraries(self):
		logging.info('Scanning libraries...')
		cursor = self.connection.cursor()
		cursor.execute(self.SELECT_LIBRARY)
		
		# Scan each libraries
		row = cursor.fetchone()
		while row is not None:
			id = row['ID']
			path = row['PATH']
			parent, title = os.path.split(path)
			try:			
				coverID = self.__scanDirectory(id, path, title)
			except sqlite3.Error as e:
				logging.error('Error while scanning library path \'{}\' : {}'.format(path, e.args[0]))
				raise e
			
			# Fetch next line
			row = cursor.fetchone()

	def addLibraryPath(self, path):
		try:
			cursor = self.connection.cursor()
			cursor.execute(self.INSERT_LIBRARY, (path,))
			self.connection.commit()
		except sqlite3.Error as e:
			logging.error('Error while inserting library path \'{}\' : {}'.format(path, e.args[0]))
			self.connection.rollback()
	
	def removeLibrary(self, libraryID):
		logging.info('Removing library ({})...'.format(libraryID))
		cursor = self.connection.cursor()

		try:
			# Select all books from library
			cursor.execute(self.SELECT_BOOK_LIBRARY, (libraryID,))
			
			# Remove each book cover
			row = cursor.fetchone()
			while row is not None:
				self.__removeBookCover(row['ID'])				
				row = cursor.fetchone()			
			
			# Delete associated data
			cursor.execute(self.DELETE_BOOK_LIBRARY, (libraryID,))
			cursor.execute(self.DELETE_DIRECTORY_LIBRARY, (libraryID,))
			cursor.execute(self.DELETE_LIBRARY, (libraryID,))
			self.connection.commit()
		except sqlite3.Error as e:
			logging.error('Error while removing library ({})!'.format(libraryID))
			self.connection.rollback()

	def update(self):
		logging.info('Updating library...')
		#try:
		self.__checkDirectories()
		self.__checkBooks()
		self.__scanLibraries()
		self.connection.commit()
		#except:
		#	logging.error('Error while updating library!')
		#	self.connection.rollback()
		logging.info('Update done')
			
	def getDirContent(self, dirID = None):
		logging.debug('Get directory content ({})...'.format(dirID))
		cursor = self.connection.cursor()

		try:
			if dirID:
				# Select item from directory
				cursor.execute(self.SELECT_DIR_CONTENT, (dirID, dirID))
			else:
				# Select item from root
				cursor.execute(self.SELECT_ROOT_CONTENT)			
			return cursor.fetchall()
		except sqlite3.Error as e:
			logging.error('Error while fetching directory content ({})!'.format(libraryID))

	def getDirInfos(self, dirID):
		logging.debug('Get directory infos ({})...'.format(dirID))
		cursor = self.connection.cursor()

		try:
			# Select infos from directory
			cursor.execute(self.SELECT_DIR_INFOS, (dirID,))
			# Remove each book cover
			row = cursor.fetchone()
			if row is not None:
				return Library.DirInfos(row['ID'], row['PARENT_ID'], row['TITLE'])

		except sqlite3.Error as e:
			logging.error('Error while fetching directory infos ({})!'.format(libraryID))
		
		return Non

	def getBookInfos(self, bookID):
		logging.debug('Get book informations ({})...'.format(bookID))
		cursor = self.connection.cursor()

		try:
			# Select item from root
			cursor.execute(self.SELECT_BOOK_INFOS, (bookID,))			
			return cursor.fetchone()
		except sqlite3.Error as e:
			logging.error('Error while fetching book informations ({})!'.format(bookID))
		