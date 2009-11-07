#!/bin/env python
# -*- coding: iso-8859-1 -*-

#Copyright 2009  Domingo Aguilera

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import wx
from wx.lib.embeddedimage import PyEmbeddedImage
from boto import connect_s3
import sys
import wx.html as html
import s3accounts
import time
from datetime import datetime
from threading import Thread
from wsgiref.simple_server import make_server
import cStringIO as  StringIO
try:
	from PIL import Image,ImageFilter
except:
	pass

try:
	import Growl
except:
	pass

import urllib
import json
import os
IMAGE_WIDTH = 200

Smiles = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAolJ"
    "REFUOI1tk91Lk2EYxn/vx7OmwyBhVsytmY1cCBFBQWSRlYVGJ51EjajptliH4X/QQeJ5J+ZJ"
    "f0AnIVSWJ0EQQfQhzNG3JkRQILrl3tft6sDNRvnAdfI8z8V939d13Vi2w79IpS4pHt8p17Vk"
    "jK1EIqpcLqPN/to0nWwmrc5IUL29n3jw4Ajl8mVKpYvcv7+frq5HdEZqymauqZljWbYDwOlT"
    "xxSL/eTOnfMY4wElYAWoAhXgI75fIJ/3mJ8/wvST5xaw3kE2k1YsBhMTtzEmCYTqxEaxVaCM"
    "MRYTE1uIxZ6RzVxdf7Rsh2i0XZ5XkPRF0mONjo4KkJSSlBKgcDgsqVVSizwPRTuRZTu42Uxa"
    "XV1rGNMCOECN8fHxpimX6OnpYW5uDmgF1TAEuXG9yuf5lOyZmYcMDUWAReAj8LqJXAEWWVhY"
    "aLqrQaWVoZNtzMxMYRljq1S6iTFtwCrDw9+ZnPQ2hIOFuqB1crUKSx34qw6hXfMNG7264stM"
    "TvrAEvAOKDaRBVpjd2cQ/BbwgwDY8XiEYvEb8AMokky+BF7UK+svGR+qNp+/L0O5jeKcRXxX"
    "GLe//wxTU/fo7Q0AolCAUEiUGoWpAWtQtTi4rw19iUB5K1OPf9F//GTDRkue11K3ad0qBYMK"
    "BAJyXUehoKv93e3S4l6p0Cfv1QlFdwS0EeXBwTT5/Op6mw389qn4Pr5jcTjZweunUVgOw1qA"
    "/K0ig2fOsREky3YYGOjTyAjyPCTVUbWllW3St6T04ZC8N0c1cmGHBo4f0H/LNP3kueU4w3R3"
    "w9gYzM6CX3HwKzaz71cYu/uV7rMvcLb2Mf3srbURi81WNJdLK5HYLuMi46LEng7lMlc2Xec/"
    "xiMt8QU2mDwAAAAASUVORK5CYII=")



class UploadThread( Thread ):
	def __init__(self, window, bitmap, bucket, notifier,png_image, thumbnail):
		Thread.__init__(self)
		self.window = window
		self.bitmap = bitmap
		self.bucket = bucket
		self.growl_notifier = notifier
		self.png_image = png_image
		self.thumbnail = thumbnail

	def run(self):
		key = self.bucket.new_key( self.png_image )
		with  open( self.png_image, "rb") as f:
			key.set_contents_from_file( f, policy = "public-read" )
		key = self.bucket.new_key( self.thumbnail )
		with open( self.thumbnail, "rb") as f:
			key.set_contents_from_file( f, policy = "public-read" )
		msg = "{0} \n {1} ".format( self.png_image, self.thumbnail )
		title = "Uploaded"
		
		try:
			self.growl_notifier.notify("upload", msg,title,sticky = True)
		except:
			pass	
		try:
			os.remove(  self.png_image)
			os.remove( self.thumbnail )
		except:
			pass
		
		try:
			s3accounts.twitter_message
			wx.CallAfter( self.window.ShortenAndTweet, self.png_image)
		except:
			pass
		
		wx.CallAfter(self.window.OnListFiles )
		
		wx.CallAfter(self.window.staticbitmap.SetBitmap, self.bitmap )
		return
	
class WebServer(Thread):
	def __init__(self, window, port, bucket):
		Thread.__init__(self)
		self.window = window
		self.port = port
		self.bucket_name = bucket
		self.setDaemon(1)
		
	def doit(self, environ, start_response):
		status = "200 OK"
		headers = [('Content-type', 'text/html')]
		start_response( status, headers )
		action = environ.get("PATH_INFO","").split("/")[-1]
		if action != "click":
			return "<html><body>Boo!</body></html>"
		sc_date = datetime.now()
		sfile = "screenshot{0}".format(sc_date)
		for x in " .-:":
			sfile = sfile.replace(x , "")
			
		sfile = "{0}.png".format(sfile)
		url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, sfile)
		wx.CallAfter(self.window.OnAsyncUpload, None, sc_date)

		return '<html><body>Wait some seconds and click <a href="{0}">here</a></body></html>'.format(url)
	
	def run(self):
		s = make_server("", self.port, self.doit)
		self.server = s
		s.serve_forever()
		
	def stop(self):
		self.server.shutdown()
		self.join()
	
class Screenshot(object):
	def __init__(self, filename = "snap.png"):
		self.filename = filename
		try:
			p = wx.GetDisplaySize()
			self.p = p
			bitmap = wx.EmptyBitmap( p.x, p.y)
			dc = wx.ScreenDC()
			memdc = wx.MemoryDC()
			memdc.SelectObject(bitmap)
			memdc.Blit(0,0, p.x, p.y, dc, 0,0)
			memdc.SelectObject(wx.NullBitmap)
			bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG )

		except:
			self.filename = ""


class MainFrame( wx.Frame ):
	def __init__(self):
		wx.Frame.__init__(  self, None, -1, "Screenshot to s3", size = (650,500))
		mb = wx.MenuBar()
		accounts_menu = wx.Menu()
		self.accounts = dict()
		for x in s3accounts.accounts.keys():
			id = wx.NewId()
			self.accounts[id] = x
			mitem = accounts_menu.AppendRadioItem( id, x)
			try:
				if x == s3accounts.preferred_account:
					mitem.Check(True)
			except:
				pass
			self.Bind( wx.EVT_MENU, self.OnAccount, mitem )
		
		bucket = wx.Menu()
		self.Bind(wx.EVT_MENU, self.OnSetBucket, bucket.Append(-1, "Set Bucket"))
		self.Bind(wx.EVT_MENU, self.OnListFiles, bucket.Append(-1, "List Files"))
		
		screenshot = wx.Menu()
		self.Bind(wx.EVT_MENU, self.OnScreenshot, screenshot.Append( -1, u"Do it!"))
		self.Bind(wx.EVT_MENU, self.OnScreenshotSeries, screenshot.Append( -1, u"Do series"))
		self.Bind(wx.EVT_MENU, self.OnAsyncUpload, screenshot.Append(-1,u"Async Upload"))
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		
		upload = wx.Menu()
		self.Bind( wx.EVT_MENU, self.OnUploadAFile, upload.Append(-1, "Upload a File in Private Mode"))
		self.Bind( wx.EVT_MENU, self.OnUploadAFileInPublicMode, upload.Append(-1, "Upload a File in Public Mode"))
		mb.Append( accounts_menu, "Accounts")
		mb.Append( bucket, "Bucket" )
		mb.Append( screenshot, "Screenshot")
		mb.Append( upload, "Upload")
		self.SetMenuBar( mb )

		self.popupmenu = wx.Menu()
		self.Bind(wx.EVT_MENU, self.OnCopyUrl, self.popupmenu.Append( -1 , "Copy Url to Clibpboard"))
		self.Bind(wx.EVT_MENU, self.OnAddToList, self.popupmenu.Append( -1 , "Add to List"))
		self.Bind(wx.EVT_MENU, self.OnRemoveFromList, self.popupmenu.Append( -1, "Remove from List"))
		self.Bind(wx.EVT_MENU, self.OnMakePage, self.popupmenu.Append( -1, "Make a Page from List"))

		try:
			s3accounts.bitly_login
			self.Bind(wx.EVT_MENU, self.OnShorten, self.popupmenu.Append( -1, "Shorten Selected File's URL and Copy to Clipboard"))
			self.Bind(wx.EVT_MENU, self.OnShortenAny, self.popupmenu.Append( -1, "Shorten Typed URL and Copy to Clipboard"))
		except:
			pass
		
		self.Bind(wx.EVT_MENU, self.OnUploadAFile, self.popupmenu.Append( -1, "Upload a File in Private Mode"))
		self.Bind(wx.EVT_MENU, self.OnUploadAFileInPublicMode, self.popupmenu.Append( -1, "Upload a File in Public Mode"))
		self.Bind(wx.EVT_MENU, self.OnDeleteFile, self.popupmenu.Append( -1, "Delete this file"))

		self.panel = wx.Panel(self, -1)
		self.sizer = wx.FlexGridSizer(4,1,1,1)
		self.label = wx.StaticText(self.panel, -1, "...", wx.DefaultPosition, wx.DefaultSize, style = wx.ALIGN_CENTER)
		self.label.SetMinSize( (650,20))
		
		self.label.SetBackgroundColour( wx.NamedColour("white"))
		self.sizer.AddGrowableRow(1,5)
		self.sizer.AddGrowableRow(2,3)
		self.sizer.Add( self.label, 1, wx.GROW)
		self.listctrl = wx.ListCtrl(self.panel, -1, style = wx.LC_REPORT)
		il = wx.ImageList(16,16,True)
		il.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, (16,16)))
		il.Add( Smiles.GetBitmap())
		self.listctrl.AssignImageList(il, wx.IMAGE_LIST_SMALL)
		self.sizer.Add( self.listctrl, 1, wx.GROW)
		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnLCtrl,  self.listctrl)
		self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRightClick,  self.listctrl)
		self.staticbitmap = wx.StaticBitmap(self.panel,-1,wx.EmptyBitmap( 100,100))
		self.sizer.Add( self.staticbitmap, 1, wx.GROW)
		self.panel.SetBackgroundColour( wx.NamedColour( "black"))
		self.panel.SetSizer( self.sizer )
		self.panel.SetAutoLayout( True )
		wsgi_server_running = True
		self.webserver = None
		try:
			pb = s3accounts.preferred_bucket
			dlg = wx.MessageDialog(self, "Do you want to run a webserver to control this application with a browser?", "Webserver", style = wx.YES_NO)
			retCode = dlg.ShowModal()
			if retCode == wx.ID_YES:
				port = wx.GetNumberFromUser("Port to run the webserver", "Port", "Webserver", value = 8000, min = 8000, max = 8100 )
				self.webserver = WebServer( self, port, pb )
				self.webserver.start()
			else:
				wsgi_server_running = False
			dlg.Destroy()
		except:
			wsgi_server_running = False
		if wsgi_server_running:
			wx.MessageBox("Web server running at port {0}".format(port))
		try:
			self.growl_notifier = Growl.GrowlNotifier("sc2s3",["upload"])
			self.growl_notifier.register()
		except:
			self.growl_notifier = None
			
		self.OnAccount()
		self.OnSetBucket()

	def OnClose(self, event):
		try:
			self.webserver.stop()
		except:
			pass
		
		self.Destroy()
		
	def OnDeleteFile(self, event):
		if  wx.MessageBox("Do you really want to delete {0}".format(self.selected_file), "Delete File", wx.YES_NO) == wx.YES:
			self.bucket.delete_key( self.selected_file )
			self.OnListFiles()
		return
		
	def OnUploadAFileInPublicMode(self,event):
		self.upload_mode = "public-read"
		self.OnUploadAFile(None)
		return
		
	def OnUploadAFile( self, event = None ):
		try:
			self.upload_mode
		except:
			self.upload_mode = "private"
		file_uploaded = False	
		dlg = wx.FileDialog( self, "Select File to upload to s3 in {0} mode".format(self.upload_mode), os.getcwd(), style = wx.OPEN, wildcard = "*.*")
		if dlg.ShowModal() == wx.ID_OK:
			
			file_path = dlg.GetPath()
			file_name = dlg.GetFilename()
			with open(file_path, "rb") as f1:
				key = self.bucket.new_key( file_name )
				key.set_contents_from_file( f1,  policy = self.upload_mode)
				file_uploaded = True
				try:
					self.growl_notifier.notify("upload", file_name,"Uploaded",sticky = True)
				except:
			
					pass
		
		dlg.Destroy()
		if file_uploaded:
			self.OnListFiles()
			
	def ShortenAndTweet(self, filename):
		self.bitly_url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, filename)
		self.OnShorten()
		from twyt.twitter import Twitter
		t = Twitter()
		t.set_auth(s3accounts.twitter_user,s3accounts.twitter_password)
		t.status_update("%s %s" % (s3accounts.twitter_message, self.bitly_shorten_url))
		return
		
		
	
	def OnShortenAny(self,event):
		self.bitly_url = wx.GetTextFromUser( message = "Type the url you want to get short by bit.ly",  caption = "Shorten a URL", default_value = "http://www.github.com/batok/sc2s3/tree/master")
		if self.bitly_url:
			self.OnShorten()
		
		
	def OnShorten(self, event = None):
		if event is None:
			l_url = self.bitly_url
		else:
			l_url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, self.selected_file)
		try:
			value = urllib.urlopen("http://api.bit.ly/shorten?version=2.0.1&longUrl=%s&login=%s&apiKey=%s" % ( l_url, s3accounts.bitly_login, s3accounts.bitly_apikey)).read()
			d = json.loads(value)
			bitly_url = str( d.get("results").get(l_url).get("shortUrl"))
			self.bitly_shorten_url = bitly_url
			txt = wx.TextDataObject( bitly_url )
			if wx.TheClipboard.Open():
				wx.TheClipboard.SetData( txt )
				wx.TheClipboard.Close()
				try:
					self.growl_notifier.notify("upload", "Shorten by bitly %s and copied to clipboard" % bitly_url, "Shorten URL by bit.ly")
				except:
					pass
		except:
			pass
		return
	
	def OnCopyUrl(self, event):
		url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, self.selected_file)
		txt = wx.TextDataObject( url )
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData( txt )
			wx.TheClipboard.Close()

	def OnAddToList( self, event ):
		try:
			self.filelist.append( self.selected_file )
			self.filelist = list(set( self.filelist ))
		except:
			self.filelist = [ self.selected_file ]
		
		
	def OnRemoveFromList( self, event):
		try:
			self.filelist.remove( self.selected_file)
		except:
			pass
		
	def OnMakePage( self, event ):
		try:
			self.filelist
		except:
			wx.MessageBox("You have to select a file first!")
			return
		
		page = []
		page.append( "<html><body><b>Index of AWS S3 files generated by sc2s3 </b><br/><ul>")
		for item in self.filelist:
			page.append('<li><a href="http://s3.amazonaws.com/{0}/{1}" />{1}</a></li>'.format(self.bucket_name, item))
		page.append( "</ul></body></html>")
		
		
		sfile = "index{0}".format(datetime.now())
		for x in " .-:":
			sfile = sfile.replace(x , "")

    		
    		sfile = "{0}.html".format(sfile)
		key = self.bucket.new_key( sfile )
		with open("indextemp.html" , "w") as f:
			f.write("\n".join(page))
		
		with open( "indextemp.html", "rb") as f:
			key.set_contents_from_file( f, policy = "public-read" )
			
		url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, sfile)
		txt = wx.TextDataObject( url )
		clip_msg = ""
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData( txt )
			wx.TheClipboard.Close()
			clip_msg = " and {0} is in clipboard".format( url )
			
		wx.MessageBox(u"{0} file is in bucket {1} {2}".format(sfile,self.bucket_name, clip_msg ), "Upload status" )
		self.OnListFiles()
		return

	def OnAccount( self, event = None):
		if event is None:
			try:
				account_name = s3accounts.preferred_account
			except:
				account_name = s3accounts.accounts.keys()[0]
			
		else:	
			account_name  = self.accounts[event.GetId()]
		self.connection = connect_s3( *s3accounts.accounts[account_name])
		self.account_name = account_name
		self.label.SetLabel( "S3 account : {0}".format( self.account_name ))
		
	def OnScreenshotSeries(self, event):
		how_many = wx.GetNumberFromUser( "# Screenshots", "# Screenshots", "Attention!", value = 3, min = 3, max = 10)
		time_to_start = wx.GetNumberFromUser( "Time to start", "Number of seconds", "Attention", value = 5, min = 2, max = 20)
		interval = wx.GetNumberFromUser( "Interval", "Seconds between screenshots", "Attention", value = 3, min = 1, max = 30)
		if how_many and time and interval:
			pass
		else:
			return
		shots = []
		page = []
		time.sleep( time_to_start )
		for shot in range( how_many ):
			if shot != 0:
				time.sleep( interval )
			
			sfile = "screenshot{0}".format(datetime.now())
			for x in " .-:":
				sfile = sfile.replace(x , "")
	
			sfile_thumbnail = "{0}_thumbnail.jpg".format(sfile)
			sfile = "{0}.png".format(sfile)
			Screenshot(filename = sfile)
			image2 = wx.Image(sfile, wx.BITMAP_TYPE_ANY)
				
			width = image2.GetWidth()
			width_factor = float(width) / float(IMAGE_WIDTH)
					
			height = image2.GetHeight()
					
			image3 = image2.Scale(IMAGE_WIDTH, int(height/width_factor))
			bmp = wx.BitmapFromImage(image3) 
			
			bmp.SaveFile(sfile_thumbnail, wx.BITMAP_TYPE_JPEG )
			shots.append([sfile, sfile_thumbnail])
			
		page.append( "<html><body><b>Screenshot Series ( generated by sc2s3 , created by Domingo Aguilera aka @batok at twitter ) </b><ul>")
		for sfile, sfile_thumbnail in shots:
			key = self.bucket.new_key( sfile )
			with open( sfile , "rb") as f:
				key.set_contents_from_file( f, policy = "public-read" )
			
			key2 = self.bucket.new_key( sfile_thumbnail )
			with open( sfile_thumbnail , "rb") as f:
				key2.set_contents_from_file( f, policy = "public-read" )
			url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, sfile)
			url_t = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, sfile_thumbnail)			
			page.append('<li>{2}<a href="{0}"><img src="{1}" /></a></li>'.format(url, url_t, sfile))
		page.append( "</ul></body></html>")
		with open("indextemp.html", "w") as f:
			f.write("\n".join(page))
		page_name = "index{0}".format(datetime.now())
		for x in " .-:":
			page_name = page_name.replace(x , "")
		
		with open("indextemp.html", "rb" ) as f:
			key = self.bucket.new_key( "{0}.html".format(page_name) )
			key.set_contents_from_file( f, policy = "public-read" )
			
		url = "http://s3.amazonaws.com/{0}/{1}.html".format(self.bucket_name, page_name)
		txt = wx.TextDataObject( url )
		clip_msg = ""
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData( txt )
			wx.TheClipboard.Close()
			clip_msg = " and {0} is in clipboard".format( url )
			msg = u"{0} file is in bucket {1} {2}".format(page_name,self.bucket_name, clip_msg )
			title = "Upload Status"
			try:
				self.growl_notifier.notify("upload", msg,title,sticky = True)
			except:
				
				wx.MessageBox(msg,title )
			
			self.OnListFiles()
			
	def OnAsyncUpload(self, event = None, sc_date = None):
		if not event is None:
			delay = wx.GetNumberFromUser("Seconds to go", "Start delay", "Time", value = 3, min = 3, max = 10)
			if delay:
				time.sleep(delay)
		if  sc_date is None:
			sc_date = datetime.now()
		sfile = "screenshot{0}".format(sc_date)
		for x in " .-:":
			sfile = sfile.replace(x , "")

    		sfile_thumbnail = "{0}_thumbnail.jpg".format(sfile)
		sfile = "{0}.png".format(sfile)
		Screenshot(filename = sfile)
				
		image2 = wx.Image(sfile, wx.BITMAP_TYPE_ANY)
		width = image2.GetWidth()
		width_factor = float(width) / float(IMAGE_WIDTH)
		height = image2.GetHeight()
		image3 = image2.Scale(IMAGE_WIDTH, int(height/width_factor))
		bmp = wx.BitmapFromImage(image3) 
		bmp.SaveFile(sfile_thumbnail, wx.BITMAP_TYPE_JPEG )
		UploadThread(self, bmp, self.bucket, self.growl_notifier, sfile, sfile_thumbnail).start()
		return
	
	def OnScreenshot(self, event):
		wx.MessageBox(u"You got 5 seconds to go!", "Warning" )
		time.sleep( 5 )
		sfile = "screenshot{0}".format(datetime.now())
		for x in " .-:":
			sfile = sfile.replace(x , "")

    		sfile_thumbnail = "{0}_thumbnail.jpg".format(sfile)
		sfile_jpg = "{0}.jpg".format(sfile)
    		sfile = "{0}.png".format(sfile)
		
		Screenshot(filename = sfile)
		try:
			Image
			with open(sfile, "rb") as f1:
				f_jpg = StringIO.StringIO()
				im = Image.open(f1)
				im.filter(ImageFilter.CONTOUR)
				im.save(f_jpg, "JPEG")
				key_jpeg = self.bucket.new_key( sfile_jpg )
				headers = {"Content-Type" : "image/jpeg"}
				key_jpeg.set_contents_from_file( f_jpg, headers = headers, policy = "public-read" )
				
		except:
			pass
				
		image2 = wx.Image(sfile, wx.BITMAP_TYPE_ANY)
			
		width = image2.GetWidth()
		width_factor = float(width) / float(IMAGE_WIDTH)
				
		height = image2.GetHeight()
				
		image3 = image2.Scale(IMAGE_WIDTH, int(height/width_factor))
		bmp = wx.BitmapFromImage(image3) 
		self.staticbitmap.SetBitmap(bmp)
		self.Refresh()
		key = self.bucket.new_key( sfile )
		f = open( sfile, "rb")
		key.set_contents_from_file( f, policy = "public-read" )
		f.close()
		
		bmp.SaveFile("screenshot_thumbnail.jpg", wx.BITMAP_TYPE_JPEG )
		key2 = self.bucket.new_key( sfile_thumbnail )
		f = open( "screenshot_thumbnail.jpg", "rb")
		key2.set_contents_from_file( f, policy = "public-read" )
		f.close()
		
		url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, sfile)
		txt = wx.TextDataObject( url )
		clip_msg = ""
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData( txt )
			wx.TheClipboard.Close()
			clip_msg = " and {0} is in clipboard".format( url )
			msg , title = u"{0} file is in bucket {1} {2}".format(sfile,self.bucket_name, clip_msg ), "Upload status"
			try:
				self.growl_notifier.notify("upload", msg,title,sticky = True)
			except:
				
				wx.MessageBox(msg,title )
			self.OnListFiles()
		
	def BuildListCtrl(self):
		try:
			self.listctrl.ClearAll()
		except:
			pass

		bg1 = wx.Colour( 239, 235, 239 )
		bg2 = wx.Colour( 229, 195, 135 )
		

		title = "#,File,Size,Last Modified"
		for i, colTitle in enumerate(title.split(",")):
			self.listctrl.InsertColumn(i, colTitle)

		try:
			for x, key in enumerate(self.bucket.get_all_keys()):
				try:
					if self.restrict_number and x >= 1000:
						return
				except:
					pass
				row = x + 1
				i = self.listctrl.InsertStringItem(sys.maxint, "%06d" % row )
				bgcolor = bg1
				if i % 2 == 0:
					bgcolor = bg2

				self.listctrl.SetItemBackgroundColour( i, bgcolor)
				self.listctrl.SetStringItem( i, 1, key.name)
				if "screenshot" in key.name:
					if "thumbnail" in key.name:
						self.listctrl.SetItemImage( i, 1, 1)
					else:
						self.listctrl.SetItemImage( i, 0, 0 )
				self.listctrl.SetStringItem( i, 2, "{0}".format(key.size))
				self.listctrl.SetStringItem( i, 3, key.last_modified)
			self.listctrl.SetColumnWidth(0,90)
			for i in range(1,4):
				self.listctrl.SetColumnWidth(i, wx.LIST_AUTOSIZE)
			self.Refresh()
		except:
			pass
		return

	def OnLCtrl( self, event ):
		self.selected_file = self.listctrl.GetItem( event.m_itemIndex,1).GetText()

	def OnRightClick( self, event ):
		self.PopupMenu( self.popupmenu )

	def OnExit( self, event):
		self.Close()

	def OnListFiles(self, event = None):
		self.BuildListCtrl()
		self.label.SetLabel(u"S3 account : {2} -- Bucket {0} contains {1} file(s)".format(self.bucket_name,len(self.bucket.get_all_keys()),self.account_name ) )

	def OnSetBucket( self, event = None):
		try:
			self.bucket_name
		except:
			self.bucket_name = ""
			
		if event is None:
			try:
				self.bucket_name = s3accounts.preferred_bucket
			except:
				pass
		try:
			buckets = [x.name for x in self.connection.get_all_buckets()]
		except:
			buckets = []
		if not buckets:
			return
		if event: self.bucket_name = wx.GetSingleChoice("Bucket", "List", buckets)
		if self.bucket_name:
			self.bucket = self.connection.get_bucket( self.bucket_name)
			if self.bucket:
				num_of_files = len( self.bucket.get_all_keys())
				self.restrict_number = False
				if num_of_files > 1000:
					wx.MessageBox(u"There are {0}.  Therefore I am going to include just 1000 in the list".format(num_of_files))
					self.restrict_number = False
				self.label.SetLabel(u"S3 account : {2} -- Bucket {0} contains {1} file(s)".format(self.bucket_name,len(self.bucket.get_all_keys()),self.account_name ) )
				self.BuildListCtrl()
	
if __name__ == "__main__":
	app = wx.PySimpleApp()
	f = MainFrame()
	f.CenterOnScreen()
	f.Show()
	app.MainLoop()
