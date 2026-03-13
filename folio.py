#!/usr/bin/env python3
"""
Folio - Personal Knowledge Base Navigator
"""

import markdown
import re
import os
import sys
import time
import argparse
from io import BytesIO
from html import escape
import urllib.parse

from http.server import SimpleHTTPRequestHandler
import socketserver

PORT = 8081
ROOT = os.getcwd()

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

CSS = """
<style>
  body {
    font-family: Georgia, serif;
    max-width: 860px;
    margin: 2em auto;
    padding: 0 1.2em;
    color: #222;
    line-height: 1.6;
  }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }

  nav.breadcrumb {
    font-size: 0.85em;
    color: #888;
    margin-bottom: 1.2em;
  }
  nav.breadcrumb a { color: #888; }

  .search-box { margin: 0.8em 0 1.5em; }
  .search-box input {
    padding: 0.4em 0.6em;
    width: 280px;
    border: 1px solid #ccc;
    border-radius: 3px;
    font-size: 0.95em;
  }
  .search-box button {
    padding: 0.4em 0.9em;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-size: 0.95em;
  }

  ul.dirlist { list-style: none; padding: 0; }
  ul.dirlist li {
    padding: 0.35em 0;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    align-items: baseline;
    gap: 0.5em;
  }
  ul.dirlist li a { font-weight: bold; }
  ul.dirlist li .title { color: #666; font-size: 0.88em; flex: 1; }
  ul.dirlist li .mtime { color: #aaa; font-size: 0.8em; white-space: nowrap; }

  .recent { margin-bottom: 2em; }
  .recent h2 { font-size: 1.1em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }
  .recent ul { list-style: none; padding: 0; }
  .recent li {
    padding: 0.3em 0;
    display: flex;
    align-items: baseline;
    gap: 0.6em;
  }
  .recent li a { flex: 1; }
  .recent li .mtime { color: #aaa; font-size: 0.8em; white-space: nowrap; }

  .search-results h2 { margin-top: 0.5em; font-size: 1.1em; }
  .result {
    margin: 1em 0;
    padding: 0.7em 1em;
    background: #f9f9f9;
    border-left: 3px solid #2563eb;
    border-radius: 2px;
  }
  .result a { font-size: 1em; font-weight: bold; }
  .result .path { color: #999; font-size: 0.78em; margin-top: 0.1em; }
  .result .snippet {
    color: #555;
    font-size: 0.88em;
    margin-top: 0.4em;
    font-family: monospace;
    white-space: pre-wrap;
    word-break: break-word;
  }

  article { line-height: 1.75; }
  article h1 { border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }
  article h2 { margin-top: 1.8em; }
  article code {
    background: #f4f4f4;
    padding: 0.15em 0.35em;
    border-radius: 2px;
    font-size: 0.88em;
  }
  article pre {
    background: #f4f4f4;
    padding: 1em 1.2em;
    overflow-x: auto;
    border-radius: 3px;
    font-size: 0.88em;
  }
  article pre code { background: none; padding: 0; }
  article blockquote {
    border-left: 3px solid #ddd;
    margin-left: 0;
    padding-left: 1em;
    color: #666;
  }
  article table { border-collapse: collapse; width: 100%; }
  article th, article td {
    border: 1px solid #ddd;
    padding: 0.4em 0.7em;
    text-align: left;
  }
  article th { background: #f4f4f4; }

  .dir-tree { margin-bottom: 2em; }
  .dir-tree h2 { font-size: 1.1em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; margin-bottom: 0.6em; }
  .dir-tree details { margin: 0; }
  .dir-tree summary {
    cursor: pointer;
    padding: 0.25em 0;
    list-style: none;
    display: flex;
    align-items: baseline;
    gap: 0.5em;
    user-select: none;
  }
  .dir-tree summary::-webkit-details-marker { display: none; }
  .dir-tree summary::before { content: "▶"; font-size: 0.65em; color: #bbb; width: 1em; flex-shrink: 0; }
  .dir-tree details[open] > summary::before { content: "▼"; }
  .dir-tree summary a { font-weight: bold; }
  .dir-tree .tree-leaf {
    padding: 0.25em 0 0.25em 1.45em;
    display: flex;
    align-items: baseline;
    gap: 0.5em;
  }
  .dir-tree .readme { color: #777; font-size: 0.85em; }
  .dir-tree .tree-children { padding-left: 1.2em; border-left: 1px solid #eee; margin-left: 0.35em; }
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def page_shell(title, body, breadcrumbs=""):
    search = (
        '<div class="search-box">'
        '<form method="get" action="/search">'
        '<input name="q" placeholder="Search notes..." />'
        '<button type="submit">Search</button>'
        '</form></div>'
    )
    return (
        f'<!DOCTYPE html>\n<html>\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<title>{escape(title)}</title>\n'
        f'{CSS}\n</head>\n<body>\n'
        f'{breadcrumbs}\n'
        f'{search}\n'
        f'{body}\n'
        f'</body>\n</html>\n'
    )


def make_breadcrumbs(url_path):
    parts = [p for p in url_path.strip("/").split("/") if p]
    crumbs = ['<a href="/">home</a>']
    for i, part in enumerate(parts):
        href = "/" + "/".join(urllib.parse.quote(p) for p in parts[:i + 1])
        crumbs.append(f'<a href="{href}">{escape(urllib.parse.unquote(part))}</a>')
    return '<nav class="breadcrumb">' + " / ".join(crumbs) + "</nav>"


def send_html(handler, html):
    data = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class FolioHandler(SimpleHTTPRequestHandler):

    # -- Title extraction ----------------------------------------------------

    def get_md_title(self, fullpath):
        """Return the first # H1 heading from a markdown file, or empty string."""
        try:
            with open(fullpath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("# "):
                        return line[2:].strip()
        except OSError:
            pass
        return ""

    def get_title(self, fullpath):
        """Get a display title for any file."""
        if fullpath.endswith(".md"):
            return self.get_md_title(fullpath)
        if fullpath.endswith(".txt"):
            try:
                with open(fullpath, "r", encoding="utf-8", errors="replace") as f:
                    return f.readline().strip()
            except OSError:
                pass
        return ""

    # -- Routing -------------------------------------------------------------

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/search":
            self._serve_search(qs.get("q", [""])[0].strip())
            return

        rel = urllib.parse.unquote(parsed.path)
        fullpath = os.path.normpath(os.path.join(ROOT, rel.lstrip("/")))

        if not fullpath.startswith(os.path.normpath(ROOT)):
            self.send_error(403)
            return

        if os.path.isfile(fullpath) and fullpath.endswith(".md"):
            self._serve_markdown(fullpath, parsed.path)
            return

        super().do_GET()

    # -- Markdown rendering --------------------------------------------------

    def _serve_markdown(self, fullpath, url_path):
        try:
            with open(fullpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            self.send_error(404)
            return

        md = markdown.Markdown(extensions=["fenced_code", "tables"])
        html_content = md.convert(content)
        title = self.get_md_title(fullpath) or os.path.basename(fullpath)
        breadcrumbs = make_breadcrumbs(url_path)
        page = page_shell(title, f"<article>{html_content}</article>", breadcrumbs=breadcrumbs)
        send_html(self, page)

    # -- Search --------------------------------------------------------------

    def _serve_search(self, q):
        breadcrumbs = make_breadcrumbs("/search")
        if not q:
            body = '<div class="search-results"><p>Enter a search term above.</p></div>'
            send_html(self, page_shell("Search", body, breadcrumbs=breadcrumbs))
            return

        results = self._do_search(q)
        items = ""
        for fullpath, title, snippet in results:
            url = "/" + os.path.relpath(fullpath, ROOT)
            display = title or os.path.relpath(fullpath, ROOT)
            rel_path = os.path.relpath(fullpath, ROOT)
            items += (
                f'<div class="result">'
                f'<a href="{escape(url)}">{escape(display)}</a>'
                f'<div class="path">{escape(rel_path)}</div>'
                f'<div class="snippet">{escape(snippet)}</div>'
                f'</div>\n'
            )
        if not items:
            items = "<p>No results found.</p>"

        count = len(results)
        body = (
            f'<div class="search-results">'
            f'<h2>{count} result{"s" if count != 1 else ""} for &ldquo;{escape(q)}&rdquo;</h2>'
            f'{items}</div>'
        )
        send_html(self, page_shell(f"Search: {q}", body, breadcrumbs=breadcrumbs))

    def _do_search(self, q):
        results = []
        q_lower = q.lower()
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for fname in filenames:
                if not fname.endswith(".md"):
                    continue
                fullpath = os.path.join(dirpath, fname)
                try:
                    with open(fullpath, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except OSError:
                    continue
                for line in lines:
                    if q_lower in line.lower():
                        snippet = line.strip()[:140]
                        title = self.get_md_title(fullpath)
                        results.append((fullpath, title, snippet))
                        break  # one result per file
        results.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
        return results

    # -- Directory listing ---------------------------------------------------

    def list_directory(self, path):
        try:
            listing = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None

        listing.sort(key=lambda a: a.lower())
        url_path = urllib.parse.unquote(self.path)
        breadcrumbs = make_breadcrumbs(url_path)
        is_root = os.path.normpath(path) == os.path.normpath(ROOT)

        items = ""
        for name in listing:
            if name.startswith("."):
                continue
            fullname = os.path.join(path, name)
            linkname = displayname = name
            mtime = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(fullname)))
            file_title = self.get_title(fullname)
            title_span = f'<span class="title">— {escape(file_title)}</span>' if file_title else '<span class="title"></span>'

            if os.path.isdir(fullname):
                linkname = name + "/"
                displayname = name + "/"
            elif os.path.islink(fullname):
                displayname = name + "@"

            items += (
                f'<li>'
                f'<a href="{urllib.parse.quote(linkname)}">{escape(displayname)}</a>'
                f'{title_span}'
                f'<span class="mtime">{mtime}</span>'
                f'</li>\n'
            )

        recent_html = self._recent_files_html() if is_root else ""
        tree_html = self._dir_tree_section_html() if is_root else ""
        heading = "Folio" if is_root else url_path.rstrip("/").split("/")[-1]

        body = (
            f'{recent_html}'
            f'{tree_html}'
            f'<h2>{escape(heading)}</h2>'
            f'<ul class="dirlist">{items}</ul>'
        )
        page = page_shell("Folio" if is_root else url_path, body, breadcrumbs=breadcrumbs)

        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        return BytesIO(data)

    # -- Directory tree ------------------------------------------------------

    def _get_readme_desc(self, dirpath):
        """Return first meaningful line from README.md or index.md in a directory."""
        for fname in ("README.md", "readme.md", "index.md"):
            fpath = os.path.join(dirpath, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                # Strip leading # markers so headings read as plain text
                                return re.sub(r"^#+\s*", "", line)[:100]
                except OSError:
                    pass
        return ""

    def _dir_tree_html(self, path, url_base, depth=0):
        """Recursively build a collapsible <details> tree for subdirectories."""
        try:
            entries = sorted(
                [e for e in os.scandir(path) if e.is_dir() and not e.name.startswith(".")],
                key=lambda e: e.name.lower()
            )
        except OSError:
            return ""

        if not entries:
            return ""

        items = ""
        for entry in entries:
            dir_url = url_base.rstrip("/") + "/" + urllib.parse.quote(entry.name) + "/"
            desc = self._get_readme_desc(entry.path)
            readme_span = f'<span class="readme">— {escape(desc)}</span>' if desc else ""
            children = self._dir_tree_html(entry.path, dir_url, depth + 1)
            open_attr = " open" if depth == 0 else ""

            if children:
                items += (
                    f'<details{open_attr}>'
                    f'<summary><a href="{escape(dir_url)}">{escape(entry.name)}</a> {readme_span}</summary>'
                    f'{children}'
                    f'</details>\n'
                )
            else:
                items += (
                    f'<div class="tree-leaf">'
                    f'<a href="{escape(dir_url)}">{escape(entry.name)}</a> {readme_span}'
                    f'</div>\n'
                )

        return f'<div class="tree-children">{items}</div>'

    def _dir_tree_section_html(self):
        inner = self._dir_tree_html(ROOT, "/")
        return f'<div class="dir-tree"><h2>Directories</h2>{inner}</div>'

    # -- Recently modified ---------------------------------------------------

    def _recent_files_html(self):
        md_files = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fname in filenames:
                if fname.endswith(".md"):
                    md_files.append(os.path.join(dirpath, fname))

        md_files.sort(key=os.path.getmtime, reverse=True)

        items = ""
        for fullpath in md_files[:15]:
            url = "/" + os.path.relpath(fullpath, ROOT)
            title = self.get_md_title(fullpath) or os.path.relpath(fullpath, ROOT)
            mtime = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(fullpath)))
            items += (
                f'<li>'
                f'<a href="{escape(url)}">{escape(title)}</a>'
                f'<span class="mtime">{mtime}</span>'
                f'</li>\n'
            )

        return f'<div class="recent"><h2>Recently Modified</h2><ul>{items}</ul></div>'

    # -- Logging -------------------------------------------------------------

    def log_message(self, format, *args):
        print(f"  {self.command} {self.path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Folio — personal knowledge base navigator")
    parser.add_argument("--port", type=int, default=PORT, help="Port to serve on (default: 8081)")
    parser.add_argument("--root", type=str, default=os.getcwd(), help="Root directory to serve (default: cwd)")
    args = parser.parse_args()

    ROOT = os.path.abspath(args.root)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", args.port), FolioHandler)
    print(f"Folio serving {ROOT}")
    print(f"Open http://localhost:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
