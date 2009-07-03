import wx
from boto import connect_s3
import sys
import wx.html as html
import s3accounts
import time
from datetime import datetime
from threading import Thread
from wsgiref.simple_server import make_server
IMAGE_WIDTH = 200


class WebServer(Thread):
	def __init__(self, window, bucket):
		Thread.__init__(self)
		self.window = window
		self.bucket_name = bucket
		
	def doit(self, environ, start_response):
		status = "200 OK"
		headers = [('Content-type', 'text/html')]
		start_response( status, headers )
		sc_date = datetime.now()
		sfile = "screenshot{0}".format(sc_date)
		for x in " .-:":
			sfile = sfile.replace(x , "")
			
		sfile = "{0}.png".format(sfile)
		url = "http://s3.amazonaws.com/{0}/{1}".format(self.bucket_name, sfile)
		wx.CallAfter(self.window.RemoteScreenshot, sc_date)
		return '<html><body>Wait some seconds and click <a href="{0}">here</a></body></html>'.format(url)
	
	def run(self):
		s = make_server("", 8000, self.doit)
		s.serve_forever()
	
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


class HtmlWindowViewer(html.HtmlWindow):
	def __init__(self, parent, id):
		html.HtmlWindow.__init__( self, parent, id, style = wx.NO_FULL_REPAINT_ON_RESIZE)

class MainFrame( wx.Frame ):
	def __init__(self):
		wx.Frame.__init__(  self, None, -1, "Screenshot to s3", size = (800,600))
		mb = wx.MenuBar()
		accounts_menu = wx.Menu()
		self.accounts = dict()
		for x in s3accounts.accounts.keys():
			id = wx.NewId()
			self.accounts[id] = x
			self.Bind( wx.EVT_MENU, self.OnAccount, accounts_menu.AppendRadioItem( id, x ) )
		
		bucket = wx.Menu()
		self.Bind(wx.EVT_MENU, self.OnSetBucket, bucket.Append(-1, "Set Bucket"))
		self.Bind(wx.EVT_MENU, self.OnListFiles, bucket.Append(-1, "List Files"))
		#self.Bind(wx.EVT_MENU, self.OnAcl, bucket.Append(-1, "Acl"))
		screenshot = wx.Menu()
		self.Bind(wx.EVT_MENU, self.OnScreenshot, screenshot.Append( -1, u"Do it!"))
		self.Bind(wx.EVT_MENU, self.OnScreenshotSeries, screenshot.Append( -1, u"Do series"))
		wx.EVT_CLOSE(self, lambda _: self.Destroy() )
		mb.Append( accounts_menu, "Accounts")
		mb.Append( bucket, "Bucket" )
		mb.Append( screenshot, "Screenshot")
		self.SetMenuBar( mb )

		self.popupmenu = wx.Menu()
		self.Bind(wx.EVT_MENU, self.OnCopyUrl, self.popupmenu.Append( -1 , "Copy Url to Clibpboard"))
		self.Bind(wx.EVT_MENU, self.OnAddToList, self.popupmenu.Append( -1 , "Add to List"))
		self.Bind(wx.EVT_MENU, self.OnMakePage, self.popupmenu.Append( -1, "Make a Page with List"))
		self.panel = wx.Panel(self, -1)
		self.sizer = wx.FlexGridSizer(4,1,1,1)
		self.label = wx.StaticText(self.panel, -1, "...", wx.DefaultPosition, wx.DefaultSize, 0)
		self.label.SetMinSize( (800,20))
		self.sizer.AddGrowableRow(1,5)
		self.sizer.AddGrowableRow(2,3)
		self.sizer.AddGrowableRow(3,5)
		self.sizer.Add( self.label, 1, wx.GROW)
		self.list = wx.ListCtrl(self.panel, -1, style = wx.LC_REPORT)
		self.sizer.Add( self.list, 1, wx.GROW)
		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnLCtrl,  self.list)
		self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRightClick,  self.list)
		self.staticbitmap = wx.StaticBitmap(self.panel,-1,wx.EmptyBitmap( 100,100))
		self.sizer.Add( self.staticbitmap, 1, wx.GROW)
		self.html = HtmlWindowViewer( self.panel, -1)
		self.sizer.Add( self.html, 1, wx.GROW)
		self.panel.SetSizer( self.sizer )
		self.panel.SetAutoLayout( True )
		WebServer( self, s3accounts.preferred_bucket ).start()
		self.OnAccount()
		#self.BuildListCtrl()
		self.OnSetBucket()

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
		print self.filelist
		
	def OnMakePage( self, event ):
		try:
			self.filelist
		except:
			wx.MessageBox("You have to select a file first!")
		page = []
		page.append( "<html><body><b>Screenshot index</b><br/><ul>")
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
		wx.MessageBox(u"{0} file is in bucket {1} {2}".format(page_name,self.bucket_name, clip_msg ), "Upload status" )
		self.OnListFiles()
			
			
	def OnScreenshot(self, event):
		wx.MessageBox(u"You got 5 seconds to go!", "Warning" )
		time.sleep( 5 )
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
		wx.MessageBox(u"{0} file is in bucket {1} {2}".format(sfile,self.bucket_name, clip_msg ), "Upload status" )
		self.OnListFiles()

	def RemoteScreenshot(self, screenshot_date):
		sfile = "screenshot{0}".format(screenshot_date)
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
		return url

		
	def BuildListCtrl(self):
		try:
			self.list.ClearAll()
		except:
			pass

		bg1 = wx.Colour( 239, 235, 239 )
		bg2 = wx.Colour( 255, 207, 99 )

		title = "#,File,Size,Last Modified"
		for i, colTitle in enumerate(title.split(",")):
			self.list.InsertColumn(i, colTitle)

		try:
			for x, key in enumerate(self.bucket.get_all_keys()):
				try:
					if self.restrict_number and x >= 1000:
						return
				except:
					pass

				i = self.list.InsertStringItem(sys.maxint, "%06d" % x)
				bgcolor = bg1
				if i % 2 == 0:
					bgcolor = bg2

				self.list.SetItemBackgroundColour( i, bgcolor)
				self.list.SetStringItem( i, 1, key.name)
				self.list.SetStringItem( i, 2, "{0}".format(key.size))
				self.list.SetStringItem( i, 3, key.last_modified)
			for i in range(4):
				self.list.SetColumnWidth(i, wx.LIST_AUTOSIZE)
			self.Refresh()
		except:
			pass
		return

	def OnLCtrl( self, event ):
		self.selected_file = self.list.GetItem( event.m_itemIndex,1).GetText()

	def OnRightClick( self, event ):
		self.PopupMenu( self.popupmenu )

	def OnExit( self, event):
		self.Close()

	def OnAcl( self, event):
		pass

	def OnListFiles(self, event = None):
		self.BuildListCtrl()
		self.label.SetLabel(u"S3 account : {2} -- Bucket {0} contains {1} file(s)".format(self.bucket_name,len(self.bucket.get_all_keys()),self.account_name ) )

	def OnSetBucket( self, event = None):
		try:
			self.bucket_name
		except:
			self.bucket_name = ""
			
		if event is None:
			self.bucket_name = s3accounts.preferred_bucket
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
	f.Show()
	app.MainLoop()
