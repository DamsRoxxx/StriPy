# coding=UTF-8
import os
import fitz
import rarfile
import zipfile
from PIL import Image

class Reader:
	THUMB_WIDTH 		= 300
	IMG_SUPPORTED_EXT 	= ['.jpg', '.jpeg', '.png']
	FITZ_SUPPORTED_EXT 	= ['.pdf', '.epub']
	ZIP_SUPPORTED_EXT 	= ['.cbz']
	RAR_SUPPORTED_EXT 	= ['.cbr']
		
	def __isImgFile(filename):
		basename, ext = os.path.splitext(filename)
		return ext in Reader.IMG_SUPPORTED_EXT

	def __fitzRenderPage(filePath, imgPath, page, width):
		# Render with PyMuPDF
		doc 	= fitz.open(filePath)
		page 	= doc.loadPage(page)
		pix 	= page.getPixmap(colorspace=fitz.csRGB, alpha=False)

		# Convert to a PIL image
		img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
		Reader.__imgRenderPage(img, imgPath, width)
	
	def __zipRenderPage(filePath, imgPath, index, width):
		# Open with zipfile
		archive = zipfile.ZipFile(filePath)
		
		# If there is content
		if archive.infolist():
			# Get pages images ordered
			pages = sorted([page for page in archive.infolist() if Reader.__isImgFile(page.filename)], key=lambda fileinfo: fileinfo.filename)

			# If desired page is in range
			if index in range(len(pages)):
				# Render file
				Reader.__fileRenderPage(archive.open(pages[index]), imgPath, width)
			
			
	def __rarRenderPage(filePath, imgPath, index, width):
		# Open with rarfile
		archive = rarfile.RarFile(filePath)
		
		# If there is content
		if archive.infolist():
			# Get pages images ordered
			pages = sorted([page for page in archive.infolist() if Reader.__isImgFile(page.filename)], key=lambda fileinfo: fileinfo.filename)

			# If desired page is in range
			if index in range(len(pages)):
				# Render file
				Reader.__fileRenderPage(archive.open(pages[index]), imgPath, width)
			
	def __fileRenderPage(imgfile, imgPath, width):
		# Convert to a PIL image
		img = Image.open(imgfile)
		Reader.__imgRenderPage(img, imgPath, width)

	def __imgRenderPage(img, imgPath, width):
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

	def renderPage(filePath, imgPath, page, width):
		filename 		= os.path.basename(filePath)
		basename, ext 	= os.path.splitext(filename)
		
		# If format is supported by fitz
		if ext in Reader.FITZ_SUPPORTED_EXT:
			Reader.__fitzRenderPage(filePath, imgPath, page, width)
		# If format is supported by zip
		elif ext in Reader.ZIP_SUPPORTED_EXT:
			Reader.__zipRenderPage(filePath, imgPath, page, width)
		# If format is supported by rar
		elif ext in Reader.RAR_SUPPORTED_EXT:
			Reader.__rarRenderPage(filePath, imgPath, page, width)

	def thumbFirstPage(filePath, imgPath):
		Reader.renderPage(filePath, imgPath, 0, Reader.THUMB_WIDTH);
	