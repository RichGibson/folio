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

PORT = 8081
ROOT = os.getcwd()

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

STYLES = """
<style>
*, *::before, *::after { box-sizing: border-box; }

:root {
  --bg: #f5f5f5;
  --surface: #ffffff;
  --surface-alt: #f3f3f3;
  --surface-hover: #e8e8e8;
  --border: #dddddd;
  --border-light: #eeeeee;
  --text: #222222;
  --text-dim: #444444;
  --text-muted: #888888;
  --text-faint: #aaaaaa;
  --nav-bg: #ffffff;
  --sidebar-bg: #fafafa;
  --accent: #1a5cbe;
  --accent-bg: #e8f0fe;
  --shadow: rgba(0,0,0,0.09);
  --nav-height: 52px;
}

[data-theme="dark"] {
  --bg: #18181b;
  --surface: #27272a;
  --surface-alt: #3f3f46;
  --surface-hover: #3f3f46;
  --border: #3f3f46;
  --border-light: #333336;
  --text: #f4f4f5;
  --text-dim: #d4d4d8;
  --text-muted: #a1a1aa;
  --text-faint: #71717a;
  --nav-bg: #1c1c1f;
  --sidebar-bg: #1c1c1f;
  --accent: #7eb7ff;
  --accent-bg: #1e3a5f;
  --shadow: rgba(0,0,0,0.3);
}

body {
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.5;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Top nav ── */
.topnav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--nav-bg);
  border-bottom: 1px solid var(--border);
  height: var(--nav-height);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  box-shadow: 0 1px 4px var(--shadow);
}

.topnav .brand {
  font-weight: 700;
  font-size: 17px;
  color: var(--text);
  text-decoration: none;
  white-space: nowrap;
}

.topnav .search-wrap {
  flex: 1;
  display: flex;
  max-width: 440px;
}

.topnav input[type=search] {
  flex: 1;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-right: none;
  border-radius: 6px 0 0 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  outline: none;
}
.topnav input[type=search]:focus { border-color: var(--accent); }

.topnav .search-btn {
  padding: 6px 14px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 0 6px 6px 0;
  cursor: pointer;
  font-size: 13px;
}

.nav-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 9px;
  cursor: pointer;
  color: var(--text);
  font-size: 14px;
  line-height: 1;
}
.nav-btn:hover { background: var(--surface-hover); }

/* ── Layout ── */
.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: calc(100vh - var(--nav-height));
}
.layout.sidebar-hidden { grid-template-columns: 0 1fr; }
.layout.sidebar-hidden .sidebar { display: none; }

/* ── Sidebar ── */
.sidebar {
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  position: sticky;
  top: var(--nav-height);
  height: calc(100vh - var(--nav-height));
  overflow-y: auto;
  padding-bottom: 20px;
}

.sidebar-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  padding: 14px 14px 6px;
}

/* ── Sidebar tree ── */
.tree { }
.tree details { }
.tree details summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 14px;
  font-size: 13px;
  user-select: none;
  border-radius: 0;
}
.tree details summary::-webkit-details-marker { display: none; }
.tree details summary:hover { background: var(--surface-hover); }

.tree .toggle-icon {
  font-size: 8px;
  color: var(--text-faint);
  width: 10px;
  flex-shrink: 0;
}
.tree details[open] > summary .toggle-icon::before { content: "▼"; }
.tree details:not([open]) > summary .toggle-icon::before { content: "▶"; }

.tree details summary a {
  color: var(--text-dim);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree details summary a:hover { color: var(--accent); text-decoration: none; }

.tree .readme-desc {
  font-size: 11px;
  color: var(--text-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100px;
  flex-shrink: 0;
}

.tree .tree-children { padding-left: 14px; border-left: 1px solid var(--border-light); margin-left: 19px; }

.tree .tree-leaf {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 14px 4px 14px;
  font-size: 13px;
}
.tree .tree-leaf:hover { background: var(--surface-hover); }
.tree .tree-leaf a { color: var(--text-dim); }
.tree .tree-leaf a:hover { color: var(--accent); text-decoration: none; }

/* ── Main content ── */
.main {
  padding: 22px 32px;
  min-width: 0;
}

/* ── Breadcrumbs ── */
nav.breadcrumb {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 16px;
}
nav.breadcrumb a { color: var(--text-muted); }
nav.breadcrumb a:hover { color: var(--accent); }

/* ── Section headings ── */
.section-head {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 5px;
  margin: 22px 0 10px;
}
.section-head:first-child { margin-top: 0; }

/* ── File / directory list ── */
ul.filelist { list-style: none; padding: 0; margin: 0; }
ul.filelist li {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid var(--border-light);
}
ul.filelist li a { font-weight: 500; font-size: 13px; }
ul.filelist li .item-title { color: var(--text-muted); flex: 1; font-size: 12px; }
ul.filelist li .mtime { color: var(--text-faint); font-size: 11px; white-space: nowrap; }

/* ── Recently modified ── */
.recent { margin-bottom: 6px; }

/* ── Search results ── */
.result {
  margin: 10px 0;
  padding: 10px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
}
.result a { font-size: 14px; font-weight: 600; }
.result .path { color: var(--text-faint); font-size: 11px; margin-top: 2px; }
.result .snippet {
  color: var(--text-dim);
  font-size: 12px;
  margin-top: 6px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── Markdown article ── */
article { line-height: 1.75; font-size: 15px; max-width: 760px; }
article h1 { border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
article h2 { margin-top: 1.8em; }
article code {
  background: var(--surface-alt);
  padding: 0.15em 0.35em;
  border-radius: 3px;
  font-size: 0.88em;
}
article pre {
  background: var(--surface-alt);
  padding: 1em 1.2em;
  overflow-x: auto;
  border-radius: 6px;
  font-size: 0.88em;
  border: 1px solid var(--border-light);
}
article pre code { background: none; padding: 0; }
article blockquote {
  border-left: 3px solid var(--border);
  margin-left: 0;
  padding-left: 1em;
  color: var(--text-muted);
}
article table { border-collapse: collapse; width: 100%; }
article th, article td { border: 1px solid var(--border); padding: 0.4em 0.7em; text-align: left; }
article th { background: var(--surface-alt); }

/* ── Responsive ── */
@media (max-width: 680px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .main { padding: 14px 16px; }
  .topnav .search-wrap { max-width: none; }
}
</style>
"""

# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------

SCRIPTS = """
<script>
(function () {
  var THEME_KEY   = 'folio-theme';
  var SIDEBAR_KEY = 'folio-sidebar';

  // Apply saved theme immediately (before DOMContentLoaded) to avoid flash
  var savedTheme = localStorage.getItem(THEME_KEY) || 'light';
  document.documentElement.dataset.theme = savedTheme;

  window.toggleTheme = function () {
    var t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = t;
    localStorage.setItem(THEME_KEY, t);
    updateThemeBtn();
  };

  function updateThemeBtn() {
    var btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = document.documentElement.dataset.theme === 'dark' ? '☀' : '🌙';
  }

  window.toggleSidebar = function () {
    var layout = document.getElementById('layout');
    if (!layout) return;
    var hidden = layout.classList.toggle('sidebar-hidden');
    localStorage.setItem(SIDEBAR_KEY, hidden ? 'closed' : 'open');
  };

  document.addEventListener('DOMContentLoaded', function () {
    updateThemeBtn();
    var layout = document.getElementById('layout');
    if (layout && localStorage.getItem(SIDEBAR_KEY) === 'closed') {
      layout.classList.add('sidebar-hidden');
    }
  });
}());
</script>
"""

# ---------------------------------------------------------------------------
# Page structure
# ---------------------------------------------------------------------------

def page_shell(title, body, breadcrumbs="", sidebar="", search_query=""):
    crumbs = f'<nav class="breadcrumb">{breadcrumbs}</nav>' if breadcrumbs else ""
    q_val = escape(search_query)
    return (
        f'<!DOCTYPE html>\n<html>\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{escape(title)} — Folio</title>\n'
        f'{STYLES}\n{SCRIPTS}\n'
        f'</head>\n<body>\n'
        f'<nav class="topnav">\n'
        f'  <button class="nav-btn" onclick="toggleSidebar()" title="Toggle sidebar">☰</button>\n'
        f'  <a class="brand" href="/">Folio</a>\n'
        f'  <div class="search-wrap">\n'
        f'    <form method="get" action="/search" style="display:flex;flex:1">\n'
        f'      <input type="search" name="q" placeholder="Search notes…" value="{q_val}" />\n'
        f'      <button type="submit" class="search-btn">Search</button>\n'
        f'    </form>\n'
        f'  </div>\n'
        f'  <button class="nav-btn" id="theme-btn" onclick="toggleTheme()" title="Toggle theme">🌙</button>\n'
        f'</nav>\n'
        f'<div class="layout" id="layout">\n'
        f'  <aside class="sidebar">\n'
        f'    <div class="sidebar-label">Directories</div>\n'
        f'    <nav class="tree">{sidebar}</nav>\n'
        f'  </aside>\n'
        f'  <main class="main">\n'
        f'    {crumbs}\n'
        f'    {body}\n'
        f'  </main>\n'
        f'</div>\n'
        f'</body>\n</html>\n'
    )


def make_breadcrumbs(url_path):
    parts = [p for p in url_path.strip("/").split("/") if p]
    crumbs = ['<a href="/">home</a>']
    for i, part in enumerate(parts):
        href = "/" + "/".join(urllib.parse.quote(p) for p in parts[:i + 1])
        crumbs.append(f'<a href="{href}">{escape(urllib.parse.unquote(part))}</a>')
    return " / ".join(crumbs)


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
        """Map URL path to filesystem path under ROOT (not cwd)."""
        path = urllib.parse.unquote(path.split("?", 1)[0].split("#", 1)[0])
        path = os.path.normpath(path)
        parts = [p for p in path.split("/") if p and p not in (".", "..")]
        return os.path.join(ROOT, *parts) if parts else ROOT

    # -- Sidebar tree --------------------------------------------------------

    def _get_readme_desc(self, dirpath):
        """First meaningful line from README.md or index.md."""
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

    def _dir_tree_html(self, path, url_base, depth=0):
        """Recursively build collapsible <details> tree for subdirectories."""
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
            children = self._dir_tree_html(entry.path, dir_url, depth + 1)
            open_attr = " open" if depth == 0 else ""

            if children:
                items += (
                    f'<details{open_attr}>'
                    f'<summary>'
                    f'<span class="toggle-icon"></span>'
                    f'<a href="{escape(dir_url)}">{escape(entry.name)}</a>'
                    f'{desc_span}'
                    f'</summary>'
                    f'<div class="tree-children">{children}</div>'
                    f'</details>\n'
                )
            else:
                items += (
                    f'<div class="tree-leaf">'
                    f'<a href="{escape(dir_url)}">{escape(entry.name)}</a>'
                    f'{desc_span}'
                    f'</div>\n'
                )

        return items

    def _sidebar_html(self):
        return self._dir_tree_html(ROOT, "/")

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
        sidebar = self._sidebar_html()
        page = page_shell(title, f"<article>{html_content}</article>",
                          breadcrumbs=breadcrumbs, sidebar=sidebar)
        send_html(self, page)

    # -- Search --------------------------------------------------------------

    def _serve_search(self, q):
        breadcrumbs = make_breadcrumbs("/search")
        sidebar = self._sidebar_html()

        if not q:
            body = '<p style="color:var(--text-muted)">Enter a search term above.</p>'
            send_html(self, page_shell("Search", body,
                                       breadcrumbs=breadcrumbs, sidebar=sidebar))
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
            items = '<p style="color:var(--text-muted)">No results found.</p>'

        count = len(results)
        body = (
            f'<div class="section-head">'
            f'{count} result{"s" if count != 1 else ""} for &ldquo;{escape(q)}&rdquo;'
            f'</div>'
            f'{items}'
        )
        send_html(self, page_shell(f"Search: {q}", body,
                                    breadcrumbs=breadcrumbs, sidebar=sidebar,
                                    search_query=q))

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
        breadcrumbs = make_breadcrumbs(url_path)
        is_root = os.path.normpath(path) == os.path.normpath(ROOT)
        sidebar = self._sidebar_html()

        # Separate dirs and files for cleaner listing
        dirs, files = [], []
        for name in listing:
            if name.startswith("."):
                continue
            fullname = os.path.join(path, name)
            entry = {
                "name": name,
                "fullname": fullname,
                "mtime": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(fullname))),
                "title": self.get_title(fullname),
            }
            if os.path.isdir(fullname):
                entry["link"] = name + "/"
                entry["display"] = name + "/"
                dirs.append(entry)
            else:
                entry["link"] = name
                entry["display"] = name + ("@" if os.path.islink(fullname) else "")
                files.append(entry)

        def render_list(entries):
            out = '<ul class="filelist">'
            for e in entries:
                title_span = f'<span class="item-title">— {escape(e["title"])}</span>' if e["title"] else '<span class="item-title"></span>'
                out += (
                    f'<li>'
                    f'<a href="{urllib.parse.quote(e["link"])}">{escape(e["display"])}</a>'
                    f'{title_span}'
                    f'<span class="mtime">{e["mtime"]}</span>'
                    f'</li>\n'
                )
            out += '</ul>'
            return out

        parts = []
        if is_root:
            parts.append(self._recent_files_html())

        if dirs:
            parts.append('<div class="section-head">Directories</div>')
            parts.append(render_list(dirs))

        if files:
            parts.append('<div class="section-head">Files</div>')
            parts.append(render_list(files))

        heading = "Folio" if is_root else url_path.rstrip("/").split("/")[-1]
        title = "Folio" if is_root else heading
        body = "\n".join(parts)
        page = page_shell(title, body, breadcrumbs=breadcrumbs, sidebar=sidebar)

        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        return BytesIO(data)

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

        return (
            f'<div class="recent">'
            f'<div class="section-head">Recently Modified</div>'
            f'<ul class="filelist">{items}</ul>'
            f'</div>'
        )

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
