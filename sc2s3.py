import wx
import boto.s3.connection as con
import os
import sys
import wx.html as html
import s3accounts

class HtmlWindowViewer(html.HtmlWindow):
	def __init__(self, parent, id):
		html.HtmlWindow.__init__( self, parent, id, style = wx.NO_FULL_REPAINT_ON_RESIZE)

class MainFrame( wx.Frame ):
	def __init__(self):
		wx.Frame.__init__(  self, None, -1, "Screenshot to s3", size = (800,600))
		self.OnAccount()
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
		wx.EVT_CLOSE(self, lambda _: self.Destroy() )
		mb.Append( accounts_menu, "Accounts")
		mb.Append( bucket, "Bucket" )
		self.SetMenuBar( mb )
		self.panel = wx.Panel(self, -1)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.list = wx.ListCtrl(self.panel, -1, style = wx.LC_REPORT)
		self.sizer.Add( self.list, 1, wx.GROW)
		self.html = HtmlWindowViewer( self.panel, -1)
		self.sizer.Add( self.html, 1, wx.GROW)
		self.panel.SetSizer( self.sizer )
		self.panel.SetAutoLayout( True )
		self.BuildListCtrl()

	def OnAccount( self, event = None):
		if event is None:
			account_name = s3accounts.accounts.keys()[0]
		else:	
			account_name  = self.accounts[event.GetId()]
		os.environ['AWS_ACCESS_KEY_ID'] = s3accounts.accounts[account_name][0]
		os.environ['AWS_SECRET_ACCESS_KEY'] = s3accounts.accounts[account_name][1]
		self.connection = con.S3Connection()

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

	def OnListFiles(self, event):
		self.BuildListCtrl()


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
				wx.MessageBox(u"Bucket {0} contains {1} file(s)".format(self.bucket_name,len(self.bucket.get_all_keys())) )
				self.BuildListCtrl()
	
if __name__ == "__main__":
	app = wx.PySimpleApp()
	f = MainFrame()
	f.Show()
	app.MainLoop()
