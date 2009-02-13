# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import re
import smtplib
from email.charset import Charset, BASE64
from thread import start_new_thread

from screener.utils import generate_template, url_for

MAXHEADERLEN = 76

class NotificationSystem(object):

    def __init__(self, config):

        self.enabled     = config.enabled
        self.smtp_server = config.smtp_server
        self.smtp_port   = config.smtp_port
        self.smtp_user   = config.smtp_user
        self.smtp_pass   = config.smtp_pass
        self.smtp_from   = config.smtp_from
        self.from_name   = config.from_name
        self.reply_to    = config.reply_to
        self.use_tls     = config.use_tls

        if not self.smtp_from and not self.reply_to:
            self.enabled = False

        self._charset = Charset()
        self._charset.input_charset = 'utf-8'
        self._charset.header_encoding = BASE64
        self._charset.body_encoding = BASE64
        self._charset.output_charset = 'utf-8'
        self._charset.input_codec = 'utf-8'
        self._charset.output_codec = 'utf-8'


    def format_header(self, key, name, email=None):
        from email.header import Header
        maxlength = MAXHEADERLEN-(len(key)+2)
        # Do not sent ridiculous short headers
        if maxlength < 10:
            raise Exception("Header length is too short")
        try:
            tmp = name.encode('ascii')
            header = Header(tmp, 'ascii', maxlinelen=maxlength)
        except UnicodeEncodeError:
            header = Header(name, self._charset, maxlinelen=maxlength)
        if not email:
            return header
        return '"%s" <%s>' % (header, email)

    def add_headers(self, msg, headers):
        for h in headers:
            msg[h] = self.encode_header(h, headers[h])

    def encode_header(self, key, value):
        if isinstance(value, tuple):
            return self.format_header(key, value[0], value[1])
        if isinstance(value, list):
            items = []
            for v in value:
                items.append(self.encode_header(v))
            return ',\n\t'.join(items)
#        mo = self.longaddr_re.match(value)
#        if mo:
#            return self.format_header(key, mo.group(1), mo.group(2))
        return self.format_header(key, value)

#    def send(self, template, data, torcpts, ccrcpts, mime_headers={}):
#    def send(self, subject, content, to, mime_headers={}):
    def send(self, subject, template, data, tos, mime_headers={}):
        from email.mime.text import MIMEText
        from email.utils import formatdate

        self.server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        if self.use_tls:
            self.server.ehlo()
            if not self.server.esmtp_features.has_key('starttls'):
                raise Exception("TLS Enabled and yet the smtp server does not "
                                "support it.")
            self.server.starttls()
            self.server.ehlo()
        if self.smtp_user:
            self.server.login(self.smtp_user, self.smtp_pass)

        stream = generate_template('email/%s' % template, **data)
        body = stream.render('text')
#        body = content
        headers = {}
        headers['X-Mailer'] = 'Screener 0.1, by UfSoft.org'
        headers['X-Screener-Version'] = '0.1'
#        headers['X-URL']
        headers['Precedence'] = 'bulk'
        headers['Auto-Submitted'] = 'auto-generated'
#        headers['Subject'] = "From Screener"
        headers['Subject'] = subject
        headers['From'] = (self.from_name, self.smtp_from)
        headers['Reply-To'] = self.reply_to

#        recipients = torcpts
#        headers['To'] = ', '.join(torcpts)
        headers['To'] = tos
        headers['Date'] = formatdate()
        if not self._charset.body_encoding:
            try:
                dummy = body.encode('ascii')
            except UnicodeDecodeError:
                raise Exception("Failed to encode body")
        msg = MIMEText(body, 'plain')
        # Message class computes the wrong type from MIMEText constructor,
        # which does not take a Charset object as initializer. Reset the
        # encoding type to force a new, valid evaluation
        del msg['Content-Transfer-Encoding']
        msg.set_charset(self._charset)
        self.add_headers(msg, headers);
        self.add_headers(msg, mime_headers);
        msgtext = msg.as_string()
        # Ensure the message complies with RFC2822: use CRLF line endings
        recrlf = re.compile("\r?\n")
        msgtext = CRLF = '\r\n'.join(recrlf.split(msgtext))
#        self.server.sendmail(msg['From'], (recipients,), msgtext)
        self.server.sendmail(msg['From'], (tos,), msgtext)

        if self.use_tls:
            # avoid false failure detection when the server closes
            # the SMTP connection with TLS enabled
            import socket
            try:
                self.server.quit()
            except socket.sslerror:
                pass
        else:
            self.server.quit()

    def sendmail(self, subject=None, template=None, data=None, tos=None):
        if not self.enabled:
            return

        self.send(subject, template, data, tos)
#        start_new_thread(self.send, (subject, content, to))
