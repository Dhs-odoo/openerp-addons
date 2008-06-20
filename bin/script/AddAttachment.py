import os
import uno
import unohelper
import xmlrpclib
import base64
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.tools import * 
    from LoginTest import *
    database="test"
    uid = 3

class AddAttachment(unohelper.Base, XJobExecutor ):
    Kind = {
	'PDF' : 'pdf',
	'OpenOffice': 'sxw',
    }
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "tiny_report"
        self.version = "0.1"
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)

        self.aSearchResult = []
        desktop=getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo=oDoc2.getDocumentInfo()

        if docinfo.getUserFieldValue(2) <> "" and docinfo.getUserFieldValue(3) <> "":
            self.win = DBModalDialog(60, 50, 180, 70, "Add Attachment to Server")
            self.win.addFixedText("lblResourceType", 2 , 5, 100, 10, "Select Appropriate Resource Type:")
            self.win.addComboListBox("lstResourceType", -2, 25, 176, 15,True)
            self.win.addButton('btnOkWithoutInformation', -2 , -5, 25 , 15,'OK' ,actionListenerProc = self.btnOkWithoutInformation_clicked )
        else:
            self.win = DBModalDialog(60, 50, 180, 190, "Add Attachment to Server")
            self.win.addFixedText("lblModuleName",2 , 9, 42, 20, "Select Module:")
            self.win.addComboListBox("lstmodel", -2, 5, 134, 15,True)
            self.lstModel = self.win.getControl( "lstmodel" )
	    self.dModel = {}

	    if 1:
		self.dModel = {
		    "Partner":'res.partner',
		    "Case":"crm.case",
		    "Sale Order":"sale.order",
		    "Purchase Order":"purchase.order",
		    "Analytic Account":"account.analytic.account",
		    "Project":"project.project",
		    "Tasks":"project.task",
		    "Employee":"hr.employee"
		}

	    else:
		sock = xmlrpclib.ServerProxy( docinfo.getUserFieldValue(0) + '/xmlrpc/object' )
		ids = sock.execute(database, uid, docinfo.getUserFieldValue(1), 'ir.model' , 'search',[])
		fields = [ 'name', 'model' ]
		models = sock.execute(database, uid, docinfo.getUserFieldValue(1), 'ir.model' , 'read', ids, fields)
		models.sort(lambda x, y: cmp(x['name'],y['name']))

		for model in models:
		    self.dModel[model['name']] = model['model']

	    for item in self.dModel.keys():
		self.lstModel.addItem(item, self.lstModel.getItemCount())

            self.win.addFixedText("lblSearchName",2 , 25, 60, 10, "Enter Search String:")
            self.win.addEdit("txtSearchName", 2, 35, 149, 15,)
            self.win.addButton('btnSearch', -2 , 35, 25 , 15,'Search' ,actionListenerProc = self.btnSearch_clicked )

            self.win.addFixedText("lblSearchRecord", 2 , 55, 60, 10, "Search Result:")
            self.win.addComboListBox("lstResource", -2, 65, 176, 70, False )
            self.lstResource = self.win.getControl( "lstResource" )

            self.win.addFixedText("lblResourceType", 2 , 137, 100, 20, "Select Appropriate Resource Type:")
            self.win.addComboListBox("lstResourceType", -2, 147, 176, 15,True )

            self.win.addButton('btnOkWithInformation', -2 , -5, 25 , 15,'OK' ,actionListenerProc = self.btnOkWithInformation_clicked )

	self.lstResourceType = self.win.getControl( "lstResourceType" )
	for kind in self.Kind.keys(): 
	    self.lstResourceType.addItem( kind, self.lstResourceType.getItemCount() )
	self.win.addButton('btnCancel', -2 - 27 , -5 , 30 , 15, 'Cancel' ,actionListenerProc = self.btnCancel_clicked )
        self.win.doModalDialog("lstResourceType", self.Kind.keys()[0])

    def btnSearch_clicked( self, oActionEvent ):
	modelSelectedItem = self.win.getListBoxSelectedItem("lstmodel")
	if modelSelectedItem == "":
	    return

	desktop=getDesktop()
	oDoc2 = desktop.getCurrentComponent()
	docinfo=oDoc2.getDocumentInfo()

	sock = xmlrpclib.ServerProxy(docinfo.getUserFieldValue(0) +'/xmlrpc/object')
	self.aSearchResult = sock.execute( database, uid, docinfo.getUserFieldValue(1), self.dModel[modelSelectedItem], 'name_search', self.win.getEditText("txtSearchName"))
	self.win.removeListBoxItems("lstResource", 0, self.win.getListBoxItemCount("lstResource"))
	if self.aSearchResult == []:
	    ErrorDialog("No search result found !!!", "", "Search ERROR" )
	    return

	for result in self.aSearchResult:
	    self.lstResource.addItem(result[1],result[0])

    def _send_attachment( self, name, data, res_model, res_id ):
	desktop = getDesktop()
	oDoc2 = desktop.getCurrentComponent()
	docinfo = oDoc2.getDocumentInfo()

	sock = xmlrpclib.ServerProxy( docinfo.getUserFieldValue(0) + '/xmlrpc/object' )
	params = {
	    'name': name, 
	    'datas': base64.encodestring( data ), 
	    'res_model' : res_model, 
	    'res_id' : int(res_id),
	}

	return sock.execute( database, uid, docinfo.getUserFieldValue(1), 'ir.attachment', 'create', params )

    def send_attachment( self, model, resource_id ):
	desktop = getDesktop()
	oDoc2 = desktop.getCurrentComponent()
	docinfo = oDoc2.getDocumentInfo()

	if oDoc2.getURL() == "":
	    ErrorDialog("Please save your file", "", "Saving ERROR" )
	    return None 

	url = oDoc2.getURL()
	if self.Kind[self.win.getListBoxSelectedItem("lstResourceType")] == "pdf":
	    url = self.doc2pdf(url[7:])

	if url == None:
	    ErrorDialog( "Ploblem in creating PDF", "", "PDF Error" )
	    return None 

	url = url[7:]
	data = read_data_from_file( get_absolute_file_path( url ) )
	return self._send_attachment( os.path.basename( url ), data, model, resource_id )

    def btnOkWithoutInformation_clicked( self, oActionEvent ):
	desktop = getDesktop()
	oDoc2 = desktop.getCurrentComponent()
	docinfo = oDoc2.getDocumentInfo()

	if self.win.getListBoxSelectedItem("lstResourceType") == "":
	    ErrorDialog("Please select resource type", "", "Selection ERROR" )
	    return 

	res = self.send_attachment( docinfo.getUserFieldValue(3), docinfo.getUserFieldValue(2) )
	self.win.endExecute()

    def btnOkWithInformation_clicked(self,oActionEvent):
	if self.win.getListBoxSelectedItem("lstResourceType") == "":
	    ErrorDialog( "Please select resource type", "", "Selection ERROR" )
	    return 

	if self.win.getListBoxSelectedItem("lstResource") == "" or self.win.getListBoxSelectedItem("lstmodel") == "":
	    ErrorDialog("Please select Model and Resource","","Selection ERROR")
	    return 

	resourceid = None
	for s in self.aSearchResult:
	    if s[1] == self.win.getListBoxSelectedItem("lstResource"):
		resourceid = s[0]
		break

	if resourceid == None:
	    ErrorDialog("No resource selected !!!", "", "Resource ERROR" )
	    return 

	res = self.send_attachment( self.dModel[self.win.getListBoxSelectedItem('lstmodel')], resourceid )
	self.win.endExecute()

    def btnCancel_clicked( self, oActionEvent ):
	self.win.endExecute()

    def doc2pdf(self, strFile):
	oDoc = None
	strFilterSubName = ''

	strUrl = convertToURL( strFile )
	desktop = getDesktop()
	oDoc = desktop.loadComponentFromURL( strUrl, "_blank", 0, Array(self._MakePropertyValue("Hidden",True)))
	if oDoc:
	    strFilterSubName = ""
	    # select appropriate filter
	    if oDoc.supportsService("com.sun.star.presentation.PresentationDocument"):
		strFilterSubName = "impress_pdf_Export"
	    elif oDoc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
		strFilterSubName = "calc_pdf_Export"
	    elif oDoc.supportsService("com.sun.star.text.WebDocument"):
		strFilterSubName = "writer_web_pdf_Export"
	    elif oDoc.supportsService("com.sun.star.text.GlobalDocument"):
		strFilterSubName = "writer_globaldocument_pdf_Export"
	    elif oDoc.supportsService("com.sun.star.text.TextDocument"):
		strFilterSubName = "writer_pdf_Export"
	    elif oDoc.supportsService("com.sun.star.drawing.DrawingDocument"):
		strFilterSubName = "draw_pdf_Export"
	    elif oDoc.supportsService("com.sun.star.formula.FormulaProperties"):
		strFilterSubName = "math_pdf_Export"
	    elif oDoc.supportsService("com.sun.star.chart.ChartDocument"):
		strFilterSubName = "chart_pdf_Export"
	    else:
		pass

	    filename = len(strFilterSubName) > 0 and convertToURL( os.path.splitext( strFile )[0] + ".pdf" ) or None

	    if len(strFilterSubName) > 0:
		oDoc.storeToURL( filename, Array(self._MakePropertyValue("FilterName", strFilterSubName ),self._MakePropertyValue("CompressMode", "1" )))

	    oDoc.close(True)
	    # Can be None if len(strFilterSubName) <= 0
	    return filename

    def _MakePropertyValue(self, cName = "", uValue = u"" ):
       oPropertyValue = createUnoStruct( "com.sun.star.beans.PropertyValue" )
       if cName:
          oPropertyValue.Name = cName
       if uValue:
          oPropertyValue.Value = uValue
       return oPropertyValue


if __name__<>"package" and __name__=="__main__":
    AddAttachment(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( AddAttachment, "org.openoffice.tiny.report.addattachment", ("com.sun.star.task.Job",),)
