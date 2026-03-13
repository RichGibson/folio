#!/usr/bin/env python3
"""
Folio - Personal Knowledge Base Navigator
"""

import markdown
import re
import os
import time
import argparse
from io import BytesIO
from html import escape
import urllib.parse

from http.server import SimpleHTTPRequestHandler
import socketserver

from jinja2 import Environment, FileSystemLoader

PORT = 8081
ROOT = os.getcwd()
FOLIO_DIR = os.path.dirname(os.path.abspath(__file__))

jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(FOLIO_DIR, "templates")),
    autoescape=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_breadcrumbs(url_path):
    parts = [p for p in url_path.strip("/").split("/") if p]
    crumbs = ['<a href="/">home</a>']
    for i, part in enumerate(parts):
        href = "/" + "/".join(urllib.parse.quote(p) for p in parts[:i + 1])
        crumbs.append(f'<a href="{href}">{escape(urllib.parse.unquote(part))}</a>')
    return " / ".join(crumbs)


def render(template_name, **ctx):
    return jinja_env.get_template(template_name).render(**ctx)


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

    # -- Path translation (makes --root work) --------------------------------

    def translate_path(self, path):
        """Map URL path to filesystem under ROOT, except /static/ which stays in FOLIO_DIR."""
        parsed = path.split("?", 1)[0].split("#", 1)[0]
        decoded = urllib.parse.unquote(parsed)
        parts = [p for p in decoded.split("/") if p and p not in (".", "..")]

        if parts and parts[0] == "static":
            return os.path.join(FOLIO_DIR, *parts)

        return os.path.join(ROOT, *parts) if parts else ROOT

    # -- Sidebar tree --------------------------------------------------------

    def _get_readme_desc(self, dirpath):
        for fname in ("README.md", "readme.md", "index.md"):
            fpath = os.path.join(dirpath, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                return re.sub(r"^#+\s*", "", line)[:80]
                except OSError:
                    pass
        return ""

    def _dir_tree_html(self, path, url_base, depth=0, current_path=""):
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
            desc_span = f'<span class="readme-desc">{escape(desc)}</span>' if desc else ""
            children = self._dir_tree_html(entry.path, dir_url, depth + 1, current_path)
            mtime_raw = entry.stat().st_mtime
            data = f'data-name="{escape(entry.name.lower())}" data-mtime="{mtime_raw}"'

            is_current = current_path == dir_url
            is_ancestor = current_path.startswith(dir_url) and not is_current
            current_class = ' class="current"' if is_current else ""
            # Open if: top-level, currently selected, or ancestor of current path
            force_open = depth == 0 or is_current or is_ancestor
            open_attr = " open" if force_open else ""

            if children:
                items += (
                    f'<details {data}{open_attr}>'
                    f'<summary>'
                    f'<span class="toggle-icon"></span>'
                    f'<a href="{escape(dir_url)}"{current_class}>{escape(entry.name)}</a>'
                    f'{desc_span}'
                    f'</summary>'
                    f'<div class="tree-children">{children}</div>'
                    f'</details>\n'
                )
            else:
                items += (
                    f'<div class="tree-leaf" {data}>'
                    f'<a href="{escape(dir_url)}"{current_class}>{escape(entry.name)}</a>'
                    f'{desc_span}'
                    f'</div>\n'
                )
        return items

    def _sidebar_html(self, current_path=""):
        return self._dir_tree_html(ROOT, "/", current_path=current_path)

    # -- Title extraction ----------------------------------------------------

    def get_md_title(self, fullpath):
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

        # Allow /static/ to fall through to translate_path (served from FOLIO_DIR)
        if not rel.startswith("/static/") and not fullpath.startswith(os.path.normpath(ROOT)):
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

        # Highlight the parent directory in the sidebar
        parent_url = "/" + urllib.parse.quote(
            os.path.dirname(url_path).strip("/")
        ).rstrip("/") + "/"
        send_html(self, render("article.html",
            title=title,
            content=html_content,
            breadcrumbs=make_breadcrumbs(url_path),
            sidebar=self._sidebar_html(parent_url),
            search_query="",
        ))

    # -- Search --------------------------------------------------------------

    def _serve_search(self, q):
        results = []
        if q:
            for fullpath, title, snippet in self._do_search(q):
                results.append({
                    "url": "/" + os.path.relpath(fullpath, ROOT),
                    "title": title or os.path.relpath(fullpath, ROOT),
                    "path": os.path.relpath(fullpath, ROOT),
                    "snippet": snippet,
                })

        send_html(self, render("search.html",
            title=f"Search: {q}" if q else "Search",
            query=q,
            results=results,
            count=len(results),
            breadcrumbs=make_breadcrumbs("/search"),
            sidebar=self._sidebar_html(),
            search_query=q,
        ))


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
                        break
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
        is_root = os.path.normpath(path) == os.path.normpath(ROOT)

        dirs, files = [], []
        for name in listing:
            if name.startswith("."):
                continue
            fullname = os.path.join(path, name)
            mtime_raw = os.path.getmtime(fullname)
            entry = {
                "name": name,
                "fullname": fullname,
                "mtime": time.strftime("%Y-%m-%d", time.localtime(mtime_raw)),
                "mtime_raw": mtime_raw,
                "title": self.get_title(fullname),
            }
            if os.path.isdir(fullname):
                entry["link"] = urllib.parse.quote(name) + "/"
                entry["display"] = name + "/"
                dirs.append(entry)
            else:
                entry["link"] = urllib.parse.quote(name)
                entry["display"] = name + ("@" if os.path.islink(fullname) else "")
                files.append(entry)

        recent = self._recent_files() if is_root else []
        title = "Folio" if is_root else url_path.rstrip("/").split("/")[-1]

        current_dir_url = "/" + urllib.parse.quote(url_path.strip("/")).rstrip("/") + "/"
        html = render("directory.html",
            title=title,
            dirs=dirs,
            files=files,
            recent=recent,
            breadcrumbs=make_breadcrumbs(url_path),
            sidebar=self._sidebar_html(current_dir_url),
            search_query="",
        )

        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        return BytesIO(data)

    # -- Recently modified ---------------------------------------------------

    def _recent_files(self):
        md_files = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fname in filenames:
                if fname.endswith(".md"):
                    md_files.append(os.path.join(dirpath, fname))

        md_files.sort(key=os.path.getmtime, reverse=True)

        recent = []
        for fullpath in md_files[:15]:
            recent.append({
                "url": "/" + os.path.relpath(fullpath, ROOT),
                "title": self.get_md_title(fullpath) or os.path.relpath(fullpath, ROOT),
                "mtime": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(fullpath))),
            })
        return recent

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
