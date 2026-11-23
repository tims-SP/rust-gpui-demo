#!/usr/bin/env python3
"""Verify real Chromium result node, not a fake PASS string in script source."""
from html.parser import HTMLParser
from pathlib import Path
import sys

EXPECTED = "PASS HERMES_SHARED_OK=479820"

class ResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == "p" and dict(attrs).get("id") == "result":
            assert self.active is None, "Nested result nodes"
            node = {"attributes": dict(attrs), "content": ""}
            self.nodes.append(node)
            self.active = node

    def handle_data(self, data):
        if self.active is not None:
            self.active["content"] += data

    def handle_endtag(self, tag):
        if tag == "p" and self.active is not None:
            self.active = None

def verify(source):
    parser = ResultParser()
    parser.feed(source)
    return (
        len(parser.nodes) == 1
        and parser.nodes[0]["attributes"].get("data-status") == "pass"
        and parser.nodes[0]["content"].strip() == EXPECTED
    )

# Ensure a literal marker in a JS <script> block never passes validation.
negative = (
    "<p id='result' data-status='fail'>FAIL RuntimeError</p>"
    "<script>state.textContent = 'PASS HERMES_SHARED_OK=479820';</script>"
)
assert not verify(negative), "Browser verifier accepted a source-code string"
positive = "<p id='result' data-status='pass'>PASS HERMES_SHARED_OK=479820</p>"
assert verify(positive), "Browser verifier rejected an actual DOM result node"

document = Path(sys.argv[1]).read_text()
if not verify(document):
    raise SystemExit("Browser DOM has no genuine successful Hermes result node")
print("HERMES_BROWSER_DOM_PROOF=479820")
