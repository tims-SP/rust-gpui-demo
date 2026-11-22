import csv, json, math, pathlib, subprocess, time, sys
root=pathlib.Path('results')
def perc(values,q): return round(sorted(values)[math.ceil(len(values)*q)-1],3)
for w,h,fps in [(1280,720,30),(1920,1080,60)]:
    stem=root/f'gpui-{h}p{fps}'
    output=stem.with_suffix('.mp4')
    n=6*fps
    with stem.with_suffix('.log').open('w') as err:
        start=time.perf_counter()
        p=subprocess.Popen([sys.argv[1],str(w),str(h),str(fps),str(n),str(stem.with_suffix('.csv'))],stdout=subprocess.PIPE,stderr=err)
        ff=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pixel_format','rgba','-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0','-filter_threads','2','-c:v','libx264','-threads','4','-preset','veryfast','-tune','zerolatency','-bf','0','-g',str(fps*2),'-crf','22','-pix_fmt','yuv420p',str(output)],stdin=p.stdout)
        p.stdout.close()
        rc,enc=p.wait(),ff.wait()
        elapsed=time.perf_counter()-start
    if rc or enc: raise RuntimeError((rc,enc,stem.with_suffix('.log').read_text()))
    hashes=subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-f','framemd5','-'],text=True)
    hashes=[x.rsplit(',',1)[1].strip() for x in hashes.splitlines() if x and not x.startswith('#')]
    assert len(hashes)==n and len(set(hashes))>=n*.8,(len(hashes),len(set(hashes)))
    rows=list(csv.DictReader(stem.with_suffix('.csv').open()))
    ms=[float(r['scene_ms'])+float(r['capture_ms']) for r in rows]
    result=dict(frames=n,distinct_decoded_frames=len(set(hashes)),resolution=[w,h],target_fps=fps,elapsed_s=round(elapsed,3),offline_fps=round(n/elapsed,2),draw_and_capture_ms_p50=perc(ms,.5),draw_and_capture_ms_p95=perc(ms,.95),capture_ms_p95=perc([float(r['capture_ms']) for r in rows],.95),first_draw_and_capture_ms=ms[0])
    print('GPUI',json.dumps(result),flush=True)
    stem.with_suffix('.json').write_text(json.dumps(result,indent=2))
