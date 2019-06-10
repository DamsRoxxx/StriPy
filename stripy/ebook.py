# coding=UTF-8
import os
import fitz
import logging
import rarfile
import zipfile
from PIL import Image

class eBookImgTools:
	IMG_SUPPORTED_EXT 	= ['.jpg', '.jpeg', '.png']

	def isImgFile(filename):
		basename, ext = os.path.splitext(filename)
		return ext.lower() in eBookImgTools.IMG_SUPPORTED_EXT

	def fileRenderPage(imgfile, imgPath, width):
		# Convert to a PIL image
		img = Image.open(imgfile)
		eBookImgTools.imgRenderPage(img, imgPath, width)

	def imgRenderPage(img, imgPath, width):
		imgWidth, imgHeight = img.size

		# If image width is superior to desired width
		if width < imgWidth:
			# Resize image
			img.resize((width, int(width * float(imgHeight/imgWidth))), Image.ANTIALIAS)

			# Save image
			img.save(imgPath, quality=80, optimize=True, progressive=True)
		else:
			# Save image
			img.save(imgPath)

class eBook(object):
	SUPPORTED_EXT 	= []
	filePath = None

	def __init__(self, filePath):
		logging.debug('Initialize eBook file ({})...'.format(filePath))	
		self.filePath = filePath
		
	def pageCount(self):
		return 0;

	def renderPage(self, imgPath, page, width):
		return;
		
	def Open(filePath):
		logging.debug('Opening eBook file ({})...'.format(filePath))	
		filename 		= os.path.basename(filePath)
		basename, ext 	= os.path.splitext(filename)
		
		# If format is supported by fitz
		if ext in FITZBook.SUPPORTED_EXT:
			return FITZBook(filePath)
		# If format is supported by zip
		elif ext in CBZBook.SUPPORTED_EXT:
			return CBZBook(filePath)
		# If format is supported by rar
		elif ext in CBRBook.SUPPORTED_EXT:
			return CBRBook(filePath)
		else:
			return eBook(filePath)
		
class FITZBook(eBook):
	SUPPORTED_EXT 	= ['.pdf', '.epub']
	doc = None

	def __init__(self, filePath):
		logging.debug('Opening FITZ eBook file ({})...'.format(filePath))	
		super().__init__(filePath)
		self.doc = fitz.open(self.filePath)

	def pageCount(self):
		return self.doc.pageCount;

	def renderPage(self, imgPath, index, width):
		page 		= self.doc.loadPage(index)
		pageWidth 	= page.rect.width
		zoomFactor	= width/pageWidth
		pix 		= page.getPixmap(matrix = fitz.Matrix(zoomFactor, zoomFactor), colorspace=fitz.csRGB, alpha=False)

		# Convert to a PIL image
		img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
		eBookImgTools.imgRenderPage(img, imgPath, width)

class ArchiveBook(eBook):
	pages = None

	def __init__(self, filePath, infolist):
		logging.debug('Initialize archive eBook file ({})...'.format(filePath))	
		super().__init__(filePath)

		# If there is content
		if infolist:
			# Get pages images ordered
			logging.debug('Initialize archive eBook file ({}) : Filtering and sorting image files...'.format(filePath))	
			self.pages = sorted([page for page in infolist if eBookImgTools.isImgFile(page.filename)], key=lambda fileinfo: fileinfo.filename.lower())
			logging.debug('Initialize archive eBook file ({}) : Page Count = {}'.format(filePath, self.pageCount()))	

	def pageCount(self):
		return len(self.pages);

class CBZBook(ArchiveBook):
	SUPPORTED_EXT 	= ['.cbz']
	zipFile	= None

	def __init__(self, filePath):
		logging.debug('Opening CBZ eBook file ({})...'.format(filePath))	
		# Open with zipfile
		self.zipFile = zipfile.ZipFile(filePath)	
		super().__init__(filePath, self.zipFile.infolist())

	def renderPage(self, imgPath, index, width):
		logging.debug('CBZBook({}) : Render page({})...'.format(self.filePath, index))	
		# If there is content
		if self.pages:
			# If desired page is in range
			if index in range(len(self.pages)):
				try:
					# Render file
					eBookImgTools.fileRenderPage(self.zipFile.open(self.pages[index]), imgPath, width)
				except zipfile.BadZipfile as e:
					logging.error('CBZBook({}) : Error while rendering page({}) : {}'.format(self.filePath, index, str(e)))	
	
class CBRBook(ArchiveBook):
	SUPPORTED_EXT 	= ['.cbr']
	rarFile	= None

	def __init__(self, filePath):
		logging.debug('Opening CBR eBook file ({})...'.format(filePath))	
		# Open with zipfile
		self.rarFile = rarfile.RarFile(filePath)	
		super().__init__(filePath, self.rarFile.infolist())

	def renderPage(self, imgPath, index, width):
		logging.debug('CBRBook({}) : Render page({})...'.format(self.filePath, index))	
		# If there is content
		if self.pages:
			# If desired page is in range
			if index in range(len(self.pages)):
				# Render file
				eBookImgTools.fileRenderPage(self.rarFile.open(self.pages[index]), imgPath, width)
