import arcpy
import pythonaddins
import os
import urllib2

rel_path = os.path.dirname(__file__)
toolbox_path = os.path.join(rel_path, "WPdownload.pyt")

class ButtonClass1(object):
    """Implementation for WPDwnld_btn_addin.button (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        try:
    		urllib2.urlopen("https://www.google.com/")
    	except Exception as e:
    		pythonaddins.MessageBox("Sorry, there is no internet connection.", "Connection error")
    	else:
        	pythonaddins.GPToolDialog(toolbox_path, "WPDownload") 
            #This function results in the following error being printed to the ArcMap Python console: "TypeError: GPToolDialog() takes at most 1 argument (2 given)" - This is a bug known to ESRI and is logged under issue no NIM089253