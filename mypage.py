#!/usr/bin/python
# as a one liner:
# python -m http.server 8080

import markdown
import re, os, sys, time
from io import BytesIO
from html import escape
import urllib.parse

from http.server import SimpleHTTPRequestHandler
import socketserver

PORT = 8081


class DirectoryHandler(SimpleHTTPRequestHandler):
    def get_title(self, fullname):
        """ get a string to use as the title for a file """
        title = ""
        if re.search(r"\.txt$", fullname):
            try:
                f = open(fullname, "r")
                title = f.readline()
            except:
                pass
        else:
            title = "not .txt"

        return title

    def FOOdo_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        foo = "this is a page"
        self.send_header("Content-length", len(foo))
        self.end_headers()
        self.wfile.write(foo.encode())

    def list_directory(self, path):
        try:
            listing = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        listing.sort(key=lambda a: a.lower())
        f = BytesIO()
        displaypath = escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(("<html>\n<title>Directory listing for %s</title>\n" % displaypath).encode())
        f.write(("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath).encode())
        f.write(b"<hr>\n<ul>\n")
        for name in listing:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            date_modified = time.ctime(os.path.getmtime(fullname))
            file_title = self.get_title(fullname)
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"

            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /

            f.write(('<li><a href="%s">%s</a> - %s\n'
                    % (urllib.parse.quote(linkname), escape(displayname), file_title)).encode())

            # display date modified
            #f.write(('<li><a href="%s">%s - %s</a>\n'
            #        % (urllib.parse.quote(linkname), escape(displayname), date_modified)).encode())

        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f


httpd = socketserver.TCPServer(("", PORT), DirectoryHandler)
print("Serving at port", PORT)
httpd.serve_forever()
