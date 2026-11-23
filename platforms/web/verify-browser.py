#!/usr/bin/env python3
"""Require actual live Chromium result DOM, not PASS strings in JS source."""
from html.parser import HTMLParser
from pathlib import Path
import sys

class Nodes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.p={}
        self.active=None
    def handle_starttag(self,tag,attrs):
        if tag=="p" and dict(attrs).get("id") in ("result-svelte","result-solid"):
            key=dict(attrs)["id"]
            if key in self.p: raise SystemExit("Duplicate result "+key)
            self.active=key
            self.p[key]={"attrs":dict(attrs),"text":""}
    def handle_data(self,text):
        if self.active is not None:self.p[self.active]["text"]+=text
    def handle_endtag(self,tag):
        if tag=="p":self.active=None
def valid(html):
    p=Nodes();p.feed(html)
    return all(p.p.get("result-"+f,{}).get("attrs",{}).get("data-status")=="pass"
        and p.p["result-"+f]["text"].strip()=="PASS_HERMES_HBC_"+f.upper()
        for f in ("svelte","solid"))
assert not valid('<p id="result-svelte">PENDING</p><script>PASS_HERMES_HBC_SVELTE</script>')
assert valid(''.join(f'<p id="result-{f}" data-status="pass">PASS_HERMES_HBC_{f.upper()}</p>'
       for f in ("svelte","solid")))
if not valid(Path(sys.argv[1]).read_text()):
    raise SystemExit("Actual browser DOM does not show BOTH Hermes HBC frameworks passing")
print("CHROMIUM_HERMES_WASM_SVELTE_AND_SOLID_PASS")
