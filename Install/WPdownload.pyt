import arcpy
import csv
import io
import os
import numpy as np
from ftplib import FTP

"""
Arcpy Python Toolbox with WPDownload tool. Tool reads covariate .csv on WorldPop FTP, creates dropdown of layers available and downloads layer to chosen diretory and adds to map if selected.

Toolbox can be used as standalone tool or it is installed through 'WPDwnld_btn.esriaddin' addin as a button.

"""


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "WPDownload"
        self.alias = "Download WorldPop Raster Covariates"

        # List of tool classes associated with this toolbox
        self.tools = [WPDownload]


class WPDownload(object):
    """Class to create tool within toolbox. Creates CSVDownload and FTPDownload to read csv of rasters available, create dropdown menu, and download rasters to specified folder
    """

    def __init__(self):
        """Define the tool (tool name is the name of the class) and set attributes."""
        self.label = "WorldPop Download"
        self.description = "Download WorldPop Raster Covariates from WorldPop FTP"
        self.canRunInBackground = False
        self.csv = CSVDownload()
        self.csv_reader, self.lf = self.csv.read_csv()
        #Make dictionary of layers available for each country
        self.cov_dict = self.csv.make_dict(self.csv_reader, self.lf) 
            
        

    def getParameterInfo(self):
        """Define parameter definitions"""

        #Countries available dropdown
        isos = arcpy.Parameter(
            displayName="Choose country",
            name="country",
            parameterType="Required",
            datatype = "String",
            direction="Input",
            )
        isos.filter.list = sorted(self.cov_dict.keys())
        
        #Covariates/population per pixel rasters available dropdown
        covariates = arcpy.Parameter(
            displayName="Choose covariate",
            name="covariate",
            parameterType="Required",
            direction="Input",
            datatype = "String",
            #parameterType="Derived",
            enabled=False
            )

        #Check button to load raster to map following download
        add_to_map_doc = arcpy.Parameter(
            displayName="Add to map after download",
            name="check_box",
            parameterType="Required",
            direction="input",
            datatype="GPBoolean",
            )
        add_to_map_doc.value = False

        #Path to directory in which to download raster
        outfile = arcpy.Parameter(
            displayName="Save location",
            name="savename",
            datatype="DEFolder",
            direction="Input"
            )

        params = [isos, covariates, outfile, add_to_map_doc]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute. Not applicable."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed.
        """

        if parameters[0].value:
            parameters[1].enabled = True #enable dropdown for rasters avail.
            parameters[1].filter.list = list(self.cov_dict[parameters[0].valueAsText]['Description'])
        return
    
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return 

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.env.addOutputsToMap = True
        country = parameters[0].valueAsText
        covariate = parameters[1].valueAsText
        ftp_path = self.cov_dict[country]['Folder'][np.where(self.cov_dict[country]['Description'] == covariate)][0]
        iso = self.cov_dict[country]['iso']
        raster = self.cov_dict[country]['Raster_name'][np.where(self.cov_dict[country]['Description'] == covariate)][0]
        download_path = parameters[2].valueAsText
        add_output_to_map = parameters[3].value

        download_raster = FTPDownload(iso, raster, ftp_path, download_path)
        download_raster.download_ftp()
        if add_output_to_map == True:
            original_workspace = arcpy.env.workspace
            mxd = arcpy.mapping.MapDocument("Current")
            arcpy.env.workspace = download_path #Temporarily change workspace to download location
            lyr = arcpy.mapping.Layer(raster)
            arcpy.ApplySymbologyFromLayer_management(lyr, "default_symbology/symbology.lyr") #Default greyscale symbology
            arcpy.env.workspace = original_workspace #Revert to original workspace
        return
    

class FTPDownload:
    """Class with methods to download layers from the FTP.

    Args:
    iso(str): Country chosen.
    raster_name(str): Name of tif to download.
    ftp_folder(str): Path to folder on FTP.
    destination_folder(str): Path to download folder.

    Attributes:
    ftp_url: URL of ftp.
    ftp_user: Ftp user.
    ftp_password: Only for testing. To be removed in public repo.
    raster_name: As above
    ftp_folder: As above concatinated with path to covariates (***This will need to be changed when ppp layers are included)
    destination_folder: As above

    """

    def __init__(self, iso, raster_name, ftp_folder, destination_folder):   
        self.ftp_url = "ftp.worldpop.org.uk"
        self.ftp_user = ""
        self.ftp_password = ""
        self.raster_name = raster_name
        self.ftp_folder = ftp_folder.replace("\\", "/")
        self.destination_folder = destination_folder

    def download_ftp(self):
        """Method to download raster from ftp into target folder.

        Args:
        None

        Returns:
        None
        """
        download_path = os.path.join(self.destination_folder, self.raster_name)
        ftp = FTP(self.ftp_url)
        ftp.login(self.ftp_user, self.ftp_password) #Function previously called when FTP was password protected.
        ftp.cwd(self.ftp_folder + "/")
        lf = open(download_path, 'wb')
        ftp.retrbinary('RETR ' + self.raster_name, lf.write)
        lf.close()
        ftp.quit()

class CSVDownload:
    """Class to read covariate csv on ftp
    
    Args:
    None

    Attributes:
    ftp_url: URL of ftp.
    ftp_user: Ftp user.
    ftp_password: Only for testing. To be removed in public repo

    """

    def __init__(self):
        self.ftp_url = "ftp.worldpop.org.uk"
        self.ftp_user = ""
        self.ftp_password = ""

    def read_csv(self):
        """Function to read csv held on FTP to query layers available
        
        Args:
        None.

        Returns:
        csv_contents, reference to bytes read from csv (to be closed in make_dict function).
        """
        ftp = FTP(self.ftp_url)
        ftp.login(self.ftp_user, self.ftp_password) #Function previously called when FTP was password protected.
        ftp.cwd('/assets')
        lf = io.BytesIO()
        ftp.retrbinary("RETR wpgpDatasets.csv", lf.write)
        lf.seek(0)
        csv_reader = csv.reader(lf)
        ftp.quit()
        return csv_reader, lf

    
    def make_dict(self, csv_reader, lf):
        """Make dictionary with keys of each country and values of lists of covariates, file and pathnames associated with each country.

        Args:
        csv_reader: data read from csv on ftp.
        lf = opened file (needs to be closed after reading).

        Return:
        cov_dict: Dictionary of data read from csv.
        """
        isos = []
        description = []
        rstName = []
        folder = []
        name_english = []
        for row in csv_reader:
            if not row[0] == 'ID':
                isos.append(row[2])
                description.append(row[6])
                rstName.append(row[5].split('/')[-1])
                folder.append(os.path.join(*row[5].split('/')[:-1]))
                name_english.append(row[3])
        isos_unique = list(set(isos))
        isos_np = np.array(isos)
        description_np = np.array(description)
        rstName_np = np.array(rstName)
        folder_np = np.array(folder)
        name_english_np = np.array(name_english)
        name_english_unique = sorted(list(set(name_english)))
        cov_dict = {}
        for i in name_english_unique:
            #if i.endswith('land Islands'): #UTF-8 characters not read correctly.
            #    name = 'Aland Islands'
            #else:
            name = i
            cov_dict[name] = {}
            cov_dict[name]['Description'] = description_np[np.where(name_english_np == i)]
            cov_dict[name]['Raster_name'] = rstName_np[np.where(name_english_np == i)]
            cov_dict[name]['Folder'] = folder_np[np.where(name_english_np == i)]
            cov_dict[name]['iso'] = isos_np[np.where(name_english_np == i)][0]
            ####################################NEED TO MAKE KEY AND VALUE PAIR FOR PPP ----------------> THE APPROPRIATE FOLDER THEN NEEDS TO BE USED WHEN DOWNLOADING (COVARIATE OR PPP)#########################
        lf.close() #Close reference to data read from csv on ftp.
        return cov_dict

        
            
            
