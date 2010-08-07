# -*- encoding: utf-8 -*-

#
# Copyright P. Christeas <p_christ@hol.gr> 2008,2009
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################


import netsvc
import tools
from dav_fs import openerp_dav_handler
from tools.config import config
from DAV.WebDAVServer import DAVRequestHandler
from service.websrv_lib import HTTPDir, FixSendError, HttpOptions
from BaseHTTPServer import BaseHTTPRequestHandler
import urlparse
import urllib
from string import atoi,split
from DAV.errors import *
# from DAV.constants import DAV_VERSION_1, DAV_VERSION_2

def OpenDAVConfig(**kw):
    class OpenDAV:
        def __init__(self, **kw):
            self.__dict__.update(**kw)
            
        def getboolean(self, word):
            return self.__dict__.get(word, False)

    class Config:
        DAV = OpenDAV(**kw)

    return Config()


class DAVHandler(HttpOptions, FixSendError, DAVRequestHandler):
    verbose = False
    protocol_version = 'HTTP/1.1'
    _HTTP_OPTIONS= { 'DAV' : ['1',],
                    'Allow' : [ 'GET', 'HEAD', 'COPY', 'MOVE', 'POST', 'PUT', 
                            'PROPFIND', 'PROPPATCH', 'OPTIONS', 'MKCOL',
                            'DELETE', 'TRACE', 'REPORT', ]
                    }

    def get_userinfo(self,user,pw):
        return False
    def _log(self, message):
        netsvc.Logger().notifyChannel("webdav",netsvc.LOG_DEBUG,message)
    
    def handle(self):
        self._init_buffer()

    def finish(self):
        pass

    def get_db_from_path(self, uri):
        # interface class will handle all cases.
        res =  self.IFACE_CLASS.get_db(uri, allow_last=True)
        return res

    def setup(self):
        self.davpath = '/'+config.get_misc('webdav','vdir','webdav')
        self.baseuri = "http://%s:%d/"% (self.server.server_name, self.server.server_port)
        self.IFACE_CLASS  = openerp_dav_handler(self, self.verbose)
        
    def copymove(self, CLASS):
        """ Our uri scheme removes the /webdav/ component from there, so we
        need to mangle the header, too.
        """
        dest = self.headers['Destination']
        up = urlparse.urlparse(urllib.unquote(self.headers['Destination']))
        if up.path.startswith(self.davpath):
            self.headers['Destination'] = up.path[len(self.davpath):]
        else:
            raise DAV_Forbidden("Not allowed to copy/move outside webdav path")
        DAVRequestHandler.copymove(self, CLASS)

    def get_davpath(self):
        return self.davpath
    
    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('webdav', netsvc.LOG_DEBUG_RPC, format % args)

    def log_error(self, format, *args):
        netsvc.Logger().notifyChannel('xmlrpc', netsvc.LOG_WARNING, format % args)

    def _prep_OPTIONS(self, opts):
        ret = opts
        dc=self.IFACE_CLASS
        uri=urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri=urllib.unquote(uri)
        try:
            #location = dc.put(uri,body,ct)
            ret = dc.prep_http_options(uri, opts)
        except DAV_Error, (ec,dd):
            pass
        except Exception,e:
            self.log_error("Error at options: %s", str(e))
            raise
        return ret
            
    def send_response(self, code, message=None):
        # the BufferingHttpServer will send Connection: close , while
        # the BaseHTTPRequestHandler will only accept int code.
        # workaround both of them.
        BaseHTTPRequestHandler.send_response(self, int(code), message)

    def send_header(self, key, value):
        if key == 'Connection' and value == 'close':
            self.close_connection = 1
        DAVRequestHandler.send_header(self, key, value)

    def send_body(self, DATA, code = None, msg = None, desc = None, ctype='application/octet-stream', headers=None):
        if headers and 'Connection' in headers:
            pass
        elif self.request_version in ('HTTP/1.0', 'HTTP/0.9'):
            pass
        elif self.close_connection == 1: # close header already sent
            pass
        else:
            if headers is None:
                headers = {}
            if self.headers.get('Connection',False) == 'Keep-Alive':
                headers['Connection'] = 'keep-alive'

        DAVRequestHandler.send_body(self, DATA, code=code, msg=msg, desc=desc,
                    ctype=ctype, headers=headers)

    def do_PUT(self):
        dc=self.IFACE_CLASS        
        uri=urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri=urllib.unquote(uri)
        # Handle If-Match
        if self.headers.has_key('If-Match'):
            test = False
            etag = None
            
            for match in self.headers['If-Match'].split(','):                
                if match.startswith('"') and match.endswith('"'):
                    match = match[1:-1]
                if match == '*':
                    if dc.exists(uri):
                        test = True
                        break
                else:
                    if dc.match_prop(uri, match, "DAV:", "getetag"):
                        test = True
                        break
            if not test:
                self._get_body()
                self.send_status(412)
                return

        # Handle If-None-Match
        if self.headers.has_key('If-None-Match'):
            test = True
            etag = None            
            for match in self.headers['If-None-Match'].split(','):
                if match == '*':
                    if dc.exists(uri):
                        test = False
                        break
                else:
                    if dc.match_prop(uri, match, "DAV:", "getetag"):
                        test = False
                        break
            if not test:
                self._get_body()
                self.send_status(412)
                return

        # Handle expect
        expect = self.headers.get('Expect', '')
        if (expect.lower() == '100-continue' and
                self.protocol_version >= 'HTTP/1.1' and
                self.request_version >= 'HTTP/1.1'):
            self.send_status(100)
            self._flush()

        # read the body
        body=self._get_body()

        # locked resources are not allowed to be overwritten
        if self._l_isLocked(uri):
            return self.send_body(None, '423', 'Locked', 'Locked')

        ct=None
        if self.headers.has_key("Content-Type"):
            ct=self.headers['Content-Type']
        try:
            location = dc.put(uri,body,ct)
        except DAV_Error, (ec,dd):
            return self.send_status(ec)

        headers = {}
        if location:
            headers['Location'] = location

        try:
            etag = dc.get_prop(location or uri, "DAV:", "getetag")
            headers['ETag'] = etag
        except:
            pass

        self.send_body(None, '201', 'Created', '', headers=headers)

    def _get_body(self):
        body = None
        if self.headers.has_key("Content-Length"):
            l=self.headers['Content-Length']
            body=self.rfile.read(atoi(l))
        return body

    def do_DELETE(self):
        try:
            DAVRequestHandler.do_DELETE(self)
        except DAV_Error, (ec, dd):
            return self.send_status(ec)

from service.http_server import reg_http_service,OpenERPAuthProvider

class DAVAuthProvider(OpenERPAuthProvider):
    def authenticate(self, db, user, passwd, client_address):
        """ authenticate, but also allow the False db, meaning to skip
            authentication when no db is specified.
        """
        if db is False:
            return True
        return OpenERPAuthProvider.authenticate(self, db, user, passwd, client_address)

try:

    if (config.get_misc('webdav','enable',True)):
        directory = '/'+config.get_misc('webdav','vdir','webdav') 
        handler = DAVHandler
        verbose = config.get_misc('webdav','verbose',True)
        handler.debug = config.get_misc('webdav','debug',True)
        _dc = { 'verbose' : verbose,
                'directory' : directory,
                'lockemulation' : False,
                    
                }

        conf = OpenDAVConfig(**_dc)
        handler._config = conf
        reg_http_service(HTTPDir(directory,DAVHandler,DAVAuthProvider()))
        netsvc.Logger().notifyChannel('webdav', netsvc.LOG_INFO, "WebDAV service registered at path: %s/ "% directory)
except Exception, e:
    logger = netsvc.Logger()
    logger.notifyChannel('webdav', netsvc.LOG_ERROR, 'Cannot launch webdav: %s' % e)

#eof



