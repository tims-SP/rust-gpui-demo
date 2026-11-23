#[path = "example_support/fonts.rs"]
mod example_support;

// Real GPUI frame-rebuild benchmark driven by the same imported Hermes scene.
// The internal timer is a GPUI test driver, NOT live Hermes/JSI integration.
// It measures scheduled mutation -> GPUI Render callback latency, not GPU present.
use gpui::{App,Bounds,Context,Window,WindowBounds,WindowOptions,div,prelude::*,px,rgb,size};
use serde_json::{Value, json};
use std::{cell::RefCell,env,fs,rc::Rc,time::{Duration,Instant}};

#[derive(Default)]
struct FrameStats {
    pending_at: Option<Instant>,
    render_lag_us: Vec<u64>,
    ui_updates: u64,
    actual_render_calls: u64,
    driver_start: Option<Instant>,
}

struct BenchView {
    framework: String,
    count: u64,
    theme: String,
    rows: Vec<String>,
    stats: Rc<RefCell<FrameStats>>,
}
impl Render for BenchView {
    fn render(&mut self,window:&mut Window,_cx:&mut Context<Self>)->impl IntoElement {
        // macOS CI's virtual display may park the window after its initial draw.
        // Explicitly request the next display-link frame so scheduled state updates
        // are observed by real Render callbacks rather than merely queued effects.
        #[cfg(target_os = "macos")]
        window.request_animation_frame();
        if let Ok(mut s)=self.stats.try_borrow_mut(){
            s.actual_render_calls += 1;
            if let Some(issued)=s.pending_at.take(){
                s.render_lag_us.push(issued.elapsed().as_micros() as u64);
            }
        }
        let bg=if self.theme=="dark"{rgb(0x132132)}else{rgb(0xf1f5fb)};
        let fg=if self.theme=="dark"{rgb(0xffffff)}else{rgb(0x122333)};
        div().size_full().bg(bg).text_color(fg).flex().flex_col().p_6().gap_1()
            .child(div().text_xl().child(format!("Hermes + GPUI : {}",self.framework)))
            .child(div().text_lg().child(format!("Count: {}",self.count)))
            .child(div().child(format!("48 scene rows / theme: {}",self.theme)))
            .child(div().flex().flex_col().gap_1().children(self.rows.iter().map(|row|{
                div().h(px(15.)).text_sm().child(row.clone())
            })))
    }
}
fn find_id<'a>(n:&'a Value,id:&str)->Option<&'a Value>{
    if n.get("attrs").and_then(|v|v.get("id")).and_then(Value::as_str)==Some(id){return Some(n);}
    for ch in n.get("children").and_then(Value::as_array).into_iter().flatten(){
        if let Some(found)=find_id(ch,id){return Some(found);}
    }
    None
}
fn text(n:&Value)->String{
    if n.get("type").and_then(Value::as_str)==Some("text"){
        return n.get("text").and_then(Value::as_str).unwrap_or("").to_string();
    }
    n.get("children").and_then(Value::as_array)
        .map(|children|children.iter().map(text).collect::<Vec<_>>().join("")).unwrap_or_default()
}
fn percentile(sorted:&[u64],p:f64)->Option<u64>{
    if sorted.is_empty(){None}else{
       let idx=(((sorted.len()-1) as f64)*p).ceil() as usize;
       Some(sorted[idx])
    }
}
fn main(){
    let input=env::var("HERMES_BENCH_JSON").expect("Missing Hermes scene path");
    let parsed:Value=serde_json::from_str(&fs::read_to_string(input).unwrap()).unwrap();
    let scene=parsed.get("scene").expect("Scene missing");
    let tracks=find_id(scene,"tracks").expect("Tracks missing");
    let rows:Vec<String>=tracks["children"].as_array().unwrap().iter()
        .filter(|n|n.get("name").and_then(Value::as_str)==Some("row"))
        .map(text).collect();
    assert_eq!(rows.len(),48);
    assert_eq!(rows.first().map(String::as_str),Some("Track 40"));
    assert_eq!(rows.last().map(String::as_str),Some("Track 87"));
    let framework=parsed["framework"].as_str().unwrap().to_string();
    let stats=Rc::new(RefCell::new(FrameStats::default()));
    let state=BenchView{
        framework:framework.clone(),
        count:parsed["final"]["count"].as_u64().unwrap(),
        theme:parsed["final"]["theme"].as_str().unwrap().to_string(),
        rows, stats:stats.clone()
    };
    println!("GPUI_IMPORTED_HERMES_SCENE_OK:{}",framework);
    gpui_platform::application().run(move|cx:&mut App|{
        if !example_support::load_fonts(cx){return;}
        let bounds=Bounds::centered(None,size(px(1000.),px(880.)),cx);
        let entity=cx.new(|_|state);
        let visible_entity=entity.clone();
        cx.open_window(WindowOptions{
            window_bounds:Some(WindowBounds::Windowed(bounds)),..Default::default()
        },move|_,_|visible_entity).expect("Native GPUI window creation failed");
        cx.activate(true);
        println!("GPUI_WINDOW_CREATED");
        if env::var("GPUI_REPLAY_BENCH").as_deref()==Ok("0"){return;}
        let executor=cx.background_executor().clone();
        cx.spawn(async move|async_cx|{
            executor.timer(Duration::from_millis(300)).await;
            stats.borrow_mut().driver_start=Some(Instant::now());
            for idx in 0..120 {
                executor.timer(Duration::from_millis(16)).await;
                entity.update(async_cx, |view, cx|{
                    {
                        let mut s=view.stats.borrow_mut();
                        s.ui_updates+=1;
                        s.pending_at=Some(Instant::now());
                    }
                    view.count+=1;
                    if idx%15==0 { view.theme=if view.theme=="dark"{"light"}else{"dark"}.to_owned(); }
                    view.rows.rotate_left(1);
                    cx.notify();
                });
                // AsyncApp::refresh flushes the queued refresh effect immediately.
                // Calling Context::refresh_windows inside entity.update can leave the
                // effect queued while the macOS virtual display loop is parked.
                #[cfg(target_os = "macos")]
                async_cx.refresh();
            }
            executor.timer(Duration::from_millis(250)).await;
            let measured=stats.borrow();
            let mut samples=measured.render_lag_us.clone();
            samples.sort_unstable();
            let result=json!({
                "schema":"gpui-render-replay/v1",
                "framework":framework,
                "driver":"gpui-timer-internal",
                "source":"precomputed-Hermes-scene",
                "live_hermes_vm":false,
                "live_jsi_to_gpui":false,
                "metric":"notify_to_render_callback_us_NOT_GPU_present",
                "target_interval_ms":16,
                "scheduled_updates":120,
                "applied_updates":measured.ui_updates,
                "render_callbacks_with_pending_update":samples.len(),
                "render_callback_count":measured.actual_render_calls,
                "p50_us":percentile(&samples,0.50),
                "p95_us":percentile(&samples,0.95),
                "p99_us":percentile(&samples,0.99),
                "elapsed_ms":measured.driver_start.map(|at|at.elapsed().as_millis() as u64),
            });
            println!("GPUI_REPLAY_BENCH_RESULT:{}",result);
            if measured.ui_updates==120 && samples.len()>=20 {
                println!("GPUI_REPLAY_BENCH_PASS:{}",framework);
            }else{
                println!("GPUI_REPLAY_BENCH_INSUFFICIENT_SAMPLES:{}",framework);
            }
        }).detach();
    });
}
