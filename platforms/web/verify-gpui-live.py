#!/usr/bin/env python3
"""Verify GPUI Web after REAL-TIME Chromium/Wasm execution, not virtual-time HTML.

GPU Canvas screenshot and result DOM are captured from the same browser session.
The benchmark's <pre data-status=pass> is written only by Rust/Wasm after 120
GPUI entity updates and measured Render callbacks. No fabricated measurements.
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",required=True)
    ap.add_argument("--screenshot",type=Path,required=True)
    ap.add_argument("--dom",type=Path,required=True)
    ap.add_argument("--log",type=Path,required=True)
    ap.add_argument("--timeout-ms",type=int,default=90000)
    args=ap.parse_args()
    for path in (args.screenshot,args.dom,args.log):
        path.parent.mkdir(parents=True,exist_ok=True)
    executable=shutil.which("google-chrome")
    if not executable:
        raise SystemExit("missing system google-chrome")
    events=[]
    with sync_playwright() as engine:
        browser=engine.chromium.launch(
            executable_path=executable,
            headless=True,
            args=["--no-sandbox","--enable-unsafe-swiftshader","--use-gl=angle",
                  "--use-angle=swiftshader","--disable-dev-shm-usage",
                  "--disable-background-timer-throttling",
                  "--disable-renderer-backgrounding"],
        )
        page=browser.new_page(viewport={"width":1200,"height":950},
                              device_scale_factor=1)
        page.on("console",lambda item: events.append(f"console:{item.type}:{item.text}"))
        page.on("pageerror",lambda exc: events.append(f"pageerror:{exc}"))
        page.on("requestfailed",lambda req: events.append(f"requestfailed:{req.url}:{req.failure}"))
        ok=False
        try:
            page.goto(args.url,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_function(
                "() => ['pass', 'fail'].includes(document.querySelector('#gpui-bench-result')?.getAttribute('data-status'))",
                timeout=args.timeout_ms,polling=150)
            status=page.locator("#gpui-bench-result").get_attribute("data-status")
            ok=(status == "pass")
            if ok:
                print("GPUI_WEB_REALTIME_WASM_REPLAY_DOM_PASS",flush=True)
            else:
                events.append("explicit-fail:"+str(page.locator("#gpui-bench-result").text_content())[:1500])
        except PlaywrightTimeoutError as exc:
            events.append(f"timeout:{exc}")
        finally:
            args.dom.write_text(page.content(),encoding="utf-8")
            page.screenshot(path=str(args.screenshot),animations="disabled",
                            timeout=30000)
            events.append("result-status:"+str(page.locator("#gpui-bench-result").get_attribute("data-status")))
            events.append("result-text:"+str(page.locator("#gpui-bench-result").text_content())[:1500])
            args.log.write_text("\n".join(events)+"\n",encoding="utf-8")
            browser.close()
        if not ok:
            raise SystemExit("GPUI_WEB_REALTIME_WASM_REPLAY_NOT_COMPLETED (diagnostics in "+str(args.log)+")")

if __name__=="__main__":
    main()
