# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import sys
import xmlrpclib
from time import time
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher, resolve_dotted_attribute
from werkzeug.wrappers import BaseResponse

from screener.database import session, Category

class XMLRPC(object, SimpleXMLRPCDispatcher):
    """A XMLRPC dispatcher that uses our request and response objects.  It
    also works around a problem with Python 2.4 / 2.5 compatibility and
    registers the introspection functions automatically.
    """

    def __init__(self, no_introspection=False):
        if sys.version_info[:2] < (2, 5):
            SimpleXMLRPCDispatcher.__init__(self)
        else:
            SimpleXMLRPCDispatcher.__init__(self, False, 'utf-8')
        if not no_introspection:
            self.register_introspection_functions()

    def handle_request(self, request):
        if request.method == 'POST':
            response = self._marshaled_dispatch(request)
            return BaseResponse(response, mimetype='application/xml')
        return BaseResponse('\n'.join((
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">',
            '<title>XMLRPC Interface</title>',
            '<h1>XMLRPC Interface</h1>',
            '<p>This URL provides an XMLRPC interface.  You have to '
            'connect to it using an XMLRPC client.</p>'
        )), 405, [('Allow', 'POST'), ('Content-Type', 'text/html')])

    def __call__(self, request):
        return self.handle_request(request)

    def _marshaled_dispatch(self, request, dispatch_method = None):
        """Dispatches an XML-RPC method from marshalled (XML) data.

        XML-RPC methods are dispatched from the marshalled (XML) data
        using the _dispatch method and the result is returned as
        marshalled data. For backwards compatibility, a dispatch
        function can be provided as an argument (see comment in
        SimpleXMLRPCRequestHandler.do_POST) but overriding the
        existing method through subclassing is the prefered means
        of changing method dispatch behavior.
        """
        data = request.data

        try:
            params, method = xmlrpclib.loads(data)
            print params, method

            # generate response
            if dispatch_method is not None:
                response = dispatch_method(request, method, params)
            else:
                response = self._dispatch(request, method, params)
            # wrap response in a singleton tuple
            response = (response,)
            response = xmlrpclib.dumps(response, methodresponse=1,
                                       allow_none=self.allow_none,
                                       encoding=self.encoding)
        except xmlrpclib.Fault, fault:
            response = xmlrpclib.dumps(fault, allow_none=self.allow_none,
                                       encoding=self.encoding)
        except:
            # report exception back to server
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % (sys.exc_type, sys.exc_value)),
                encoding=self.encoding, allow_none=self.allow_none,
                )

        return response

    def _dispatch(self, request, method, params):
        func = None
        try:
            # check to see if a matching function has been registered
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                # check for a _dispatch method
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(request, method, params)
                else:
                    # call instance method directly
                    try:
                        func = resolve_dotted_attribute(
                            self.instance,
                            method,
                            self.allow_dotted_names
                            )
                    except AttributeError:
                        pass

        if func is not None:
            return func(request, *params)
        else:
            raise Exception('method "%s" is not supported' % method)
#        return SimpleXMLRPCDispatcher._dispatch(self, method, params)


from screener.services import images
service = XMLRPC()
service.register_function(images.upload,
                          'images.upload')
