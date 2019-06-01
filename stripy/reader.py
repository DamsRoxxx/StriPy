# coding=UTF-8
import os
import fitz
import rarfile
from PIL import Image

class Reader:
	THUMB_WIDTH 		= 300
	FITZ_SUPPORTED_EXT 	= ['.pdf', '.cbz', '.epub']
	RAR_SUPPORTED_EXT 	= ['.cbr']
		
	def __fitzRenderPage(filePath, imgPath, page, width):
		# Render with PyMuPDF
		doc 	= fitz.open(filePath)
		page 	= doc.loadPage(page)
		pix 	= page.getPixmap()

		# Convert to a PIL image
		img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
		
		# Resize image
		img.thumbnail((width, width))

		# Save image
		img.convert('RGB').save(imgPath)
	
	def __rarRenderPage(filePath, imgPath, page, width):
		# Open with rarfile
		rf = rarfile.RarFile(filePath)
		
		# If there is content
		if rf.infolist():
			# open first file
			imgfile 	= rf.open(rf.infolist()[page])
			
			# Convert to a PIL image
			img = Image.open(imgfile)

			# Resize image
			img.thumbnail((width, width))

			# Save image
			img.save(imgPath)
			
	def renderPage(filePath, imgPath, page, width):
		filename 		= os.path.basename(filePath)
		basename, ext 	= os.path.splitext(filename)
		
		# If format is supported by fitz
		if ext in Reader.FITZ_SUPPORTED_EXT:
			Reader.__fitzRenderPage(filePath, imgPath, page, width)
		# If format is supported by rar
		elif ext in Reader.RAR_SUPPORTED_EXT:
			Reader.__rarRenderPage(filePath, imgPath, page, width)

	def thumbFirstPage(filePath, imgPath):
		Reader.renderPage(filePath, imgPath, 0, Reader.THUMB_WIDTH);
	