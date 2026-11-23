from pathlib import Path
import json
base=Path("results/hermes")
for framework in ("svelte","solid"):
    logs=(base/f"{framework}-run.log").read_text()
    lines=[x[len("BENCH_RESULT:"):] for x in logs.splitlines() if x.startswith("BENCH_RESULT:")]
    if len(lines)!=1 or "GPUI_SCENE_OK:"+framework not in logs:
        raise SystemExit(f"Hermes missing valid output for {framework}")
    obj=json.loads(lines[0])
    assert obj["framework"]==framework
    assert obj["final"]=={"count":256,"start":40,"theme":"light","renderedRows":48}
    assert obj["mutations"]>100
    (base/f"{framework}.json").write_text(json.dumps(obj,indent=2))
    print(f"HERMES_SCENE_VERIFIED:{framework} mutations={obj['mutations']}")
