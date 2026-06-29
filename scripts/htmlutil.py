"""Minimal stdlib HTML tree (bs4 subset) — zero external dependencies.

Implements just the BeautifulSoup API the KONI parsers need:
  parse(html) -> root Node
  Node.find_all(name, recursive=True, class_=None)
  Node.find(name, recursive=True, class_=None)
  Node.get_text(sep="", strip=False)
  Node.children   -> direct children (Node + Str), document order
  Node.name, Node.attrs, Node.get(k, default)
Str nodes carry raw text; isinstance(child, Str)/Tag via .name (None for Str).
Built on html.parser.HTMLParser (convert_charrefs=True -> decoded entities).
"""
from __future__ import annotations

from html.parser import HTMLParser

VOID = {
    "br", "hr", "img", "input", "meta", "link", "col", "area", "base",
    "embed", "source", "track", "wbr", "param",
}


class Str:
    """A text node (mirrors bs4 NavigableString)."""
    __slots__ = ("text",)
    name = None  # type: ignore[assignment]

    def __init__(self, text: str):
        self.text = text

    def __str__(self) -> str:
        return self.text


class Node:
    __slots__ = ("name", "attrs", "children", "parent")

    def __init__(self, name, attrs):
        self.name = name
        self.attrs = attrs
        self.children = []
        self.parent = None

    def get(self, k, default=None):
        return self.attrs.get(k, default)

    def _classes(self):
        return (self.attrs.get("class") or "").split()

    def _match(self, name, cls):
        if name is not None and self.name != name:
            return False
        if cls is not None and cls not in self._classes():
            return False
        return True

    def find_all(self, name=None, recursive=True, class_=None):
        out: list = []
        if recursive:
            stack = list(self.children)
            while stack:
                n = stack.pop(0)
                if isinstance(n, Node):
                    if n._match(name, class_):
                        out.append(n)
                    stack[:0] = n.children
        else:
            out = [c for c in self.children
                   if isinstance(c, Node) and c._match(name, class_)]
        return out

    def find(self, name=None, recursive=True, class_=None):
        r = self.find_all(name, recursive=recursive, class_=class_)
        return r[0] if r else None

    def get_text(self, sep="", strip=False):
        parts: list[str] = []
        stack = list(self.children)
        order: list = []
        # DFS document-order collection of text nodes
        def walk(n):
            for c in n.children:
                if isinstance(c, Str):
                    parts.append(c.text)
                else:
                    walk(c)
        walk(self)
        t = sep.join(parts)
        return t.strip() if strip else t


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node(None, {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, dict(attrs))
        n.parent = self.stack[-1]
        self.stack[-1].children.append(n)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        n = Node(tag, dict(attrs))
        n.parent = self.stack[-1]
        self.stack[-1].children.append(n)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].name == tag:
                del self.stack[i:]
                return
        # no matching open tag: ignore stray end tag

    def handle_data(self, data):
        self.stack[-1].children.append(Str(data))


def parse(html: str) -> Node:
    b = _Builder()
    b.feed(html)
    b.close()
    return b.root