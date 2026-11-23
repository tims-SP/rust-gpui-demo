#!/usr/bin/env python3
"""Require a live Chromium DOM status after Hermes VM work, not a string in script."""
from html.parser import HTMLParser
from pathlib import Path
import sys

class Nodes(HTMLParser):
    KEYS = ("result-svelte","result-solid","interactive-svelte","interactive-solid")
    def __init__(self):
        super().__init__()
        self.nodes={}
        self.active=None
    def handle_starttag(self,tag,attrs):
        if tag=="p" and dict(attrs).get("id") in self.KEYS:
            key=dict(attrs)["id"]
            if key in self.nodes: raise SystemExit("Duplicate result "+key)
            self.active=key
            self.nodes[key]={"attrs":dict(attrs),"text":""}
    def handle_data(self,text):
        if self.active is not None:self.nodes[self.active]["text"]+=text
    def handle_endtag(self,tag):
        if tag=="p":self.active=None

def valid(html):
    p=Nodes();p.feed(html)
    expected={}
    for framework in ("svelte","solid"):
        expected["result-"+framework]="PASS_HERMES_HBC_"+framework.upper()
        expected["interactive-"+framework]="PASS_HERMES_INTERACTIVE_"+framework.upper()
    return all(p.nodes.get(key,{}).get("attrs",{}).get("data-status")=="pass"
      and p.nodes[key]["text"].strip()==text for key,text in expected.items())

assert not valid('<script>PASS_HERMES_INTERACTIVE_SVELTE</script>')
assert not valid(''.join(
   f'<p id="result-{f}" data-status="pass">PASS_HERMES_HBC_{f.upper()}</p>'
   for f in ("svelte","solid")))
assert valid(''.join(
    f'<p id="{kind}-{f}" data-status="pass">PASS_HERMES_{label}_{f.upper()}</p>'
    for f in ("svelte","solid")
    for kind,label in (("result","HBC"),("interactive","INTERACTIVE"))))
if not valid(Path(sys.argv[1]).read_text()):
    raise SystemExit("Real Chromium did not verify BOTH HBC + interactive JSI events")
print("CHROMIUM_HERMES_WASM_SVELTE_AND_SOLID_PASS")
print("CHROMIUM_HERMES_WASM_INTERACTIVE_EVENT_PASS")
