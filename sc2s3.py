import wx
from boto import connect_s3
import sys
import wx.html as html
import s3accounts
import time
from datetime import datetime
IMAGE_WIDTH = 100


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
		self.Bind(wx.EVT_MENU, self.OnAcl, bucket.Append(-1, "Acl"))
		screenshot = wx.Menu()
		self.Bind(wx.EVT_MENU, self.OnScreenshot, screenshot.Append( -1, u"Do it!"))
		wx.EVT_CLOSE(self, lambda _: self.Destroy() )
		mb.Append( accounts_menu, "Accounts")
		mb.Append( bucket, "Bucket" )
		mb.Append( screenshot, "Screenshot")
		self.SetMenuBar( mb )
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
		self.staticbitmap = wx.StaticBitmap(self.panel,-1,wx.EmptyBitmap( 100,100))
		self.sizer.Add( self.staticbitmap, 1, wx.GROW)
		self.html = HtmlWindowViewer( self.panel, -1)
		self.sizer.Add( self.html, 1, wx.GROW)
		self.panel.SetSizer( self.sizer )
		self.panel.SetAutoLayout( True )
		self.OnAccount()
		self.BuildListCtrl()

	def OnAccount( self, event = None):
		if event is None:
			account_name = s3accounts.accounts.keys()[0]
		else:	
			account_name  = self.accounts[event.GetId()]
		self.connection = connect_s3( *s3accounts.accounts[account_name])
		self.account_name = account_name
		self.label.SetLabel( "S3 account : {0}".format( self.account_name ))


	def OnScreenshot(self, event):
		wx.MessageBox(u"You got 5 seconds to go!", "Warning" )
		time.sleep( 5 )
		sfile = "screenshot{0}".format(datetime.now())
		for x in " .-:":
			sfile = sfile.replace(x , "")
    		sfile = "{0}.png".format(sfile)
		Screenshot(filename = sfile)
		image2 = wx.Image(sfile, wx.BITMAP_TYPE_ANY)
			
		width = image2.GetWidth()
		width_factor = float(width) / float(IMAGE_WIDTH)
				
		height = image2.GetHeight()
				
		image3 = image2.Scale(IMAGE_WIDTH, int(height/width_factor))
		self.staticbitmap.SetBitmap(wx.BitmapFromImage(image3))
		self.Refresh()
		key = self.bucket.new_key( sfile )
		f = open( sfile, "rb")
		key.set_contents_from_file( f, policy = "public-read" )
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

	def OnExit( self, event):
		self.Close()

	def OnAcl( self, event):
		pass

	def OnListFiles(self, event = None):
		self.BuildListCtrl()
		self.label.SetLabel(u"S3 account : {2} -- Bucket {0} contains {1} file(s)".format(self.bucket_name,len(self.bucket.get_all_keys()),self.account_name ) )


	def OnSetBucket( self, event):
		try:
			self.bucket_name
		except:
			self.bucket_name = ""
		try:
			buckets = [x.name for x in self.connection.get_all_buckets()]
		except:
			buckets = []
		if not buckets:
			return
		self.bucket_name = wx.GetSingleChoice("Bucket", "List", buckets)
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
