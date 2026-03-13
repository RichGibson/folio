# Folio

A personal knowledge base navigator — a lightweight local web server that makes a directory of Markdown files browsable, readable, and searchable in the browser.

Built for people who keep their notes, journals, and reference material as plain `.md` files and want a better way to navigate them than a file manager.

---

## Concept

Folio serves your local Markdown files as rendered HTML. Point it at a directory, open a browser, and your knowledge base becomes a navigable, searchable website — no cloud sync, no third-party app, no lock-in.

```
python folio.py --port 8081 --root ~/notes
```

---

## Planned Features

### 1. Markdown Rendering
`.md` files are rendered as HTML rather than served as raw text. Intercepts the standard file-serving path and pipes Markdown content through the `markdown` library before sending the response. Links between `.md` files continue to work.

### 2. Title Extraction from Markdown
Directory listings display the first `# H1` heading from each `.md` file as a human-readable title, rather than just the filename. Falls back to the filename if no heading is found.

### 3. Full-text Search
A `?q=term` query parameter triggers a search across all `.md` files under the served root. Results are returned as a simple HTML page with file titles, paths, and a snippet of matching context. No external dependencies — pure Python.

### 4. Breadcrumb Navigation
Every page includes a breadcrumb bar showing the current path from root, with each segment as a clickable link. Makes it easy to orient yourself and navigate back up the tree.

### 5. Recently Modified Files
The root index page shows the 15 most recently modified `.md` files, making it easy to pick up where you left off or see what's changed.

### 6. Basic CSS Styling
A minimal embedded stylesheet: readable font, constrained line width, clean link colors, and a simple nav bar. No external dependencies.

---

## Status

Early development. Currently a working Python 3 HTTP server (`mypage.py`) with a custom directory listing handler. The features above are the next milestones.

---

## Requirements

- Python 3.8+
- `markdown` (`pip install markdown`)

---

## Usage

```bash
pip install markdown
python folio.py
# then open http://localhost:8081
```

---

## License

MIT
