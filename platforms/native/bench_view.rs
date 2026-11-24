#[path = "example_support/fonts.rs"]
mod example_support;

// Live GPUI benchmark: framework HBC -> in-process Hermes -> JSI gpuiEmit ->
// Rust Scene -> GPUI root-window update -> real Render callback.
// GPU Present is intentionally not claimed by this measurement.
use gpui::{App,Bounds,Context,Window,WindowBounds,WindowOptions,div,prelude::*,px,rgb,size};
use gpui_hermes_live_spike::SceneRuntime;
use serde_json::Value;
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
    runtime: Rc<RefCell<SceneRuntime>>,
    stats: Rc<RefCell<FrameStats>>,
}

fn find_id<'a>(node:&'a Value,id:&str)->Option<&'a Value>{
    if node.get("attrs").and_then(|v|v.get("id")).and_then(Value::as_str)==Some(id){return Some(node);}
    for child in node.get("children").and_then(Value::as_array).into_iter().flatten(){
        if let Some(found)=find_id(child,id){return Some(found);}
    }
    None
}

fn text_content(node:&Value)->String{
    if node.get("type").and_then(Value::as_str)==Some("text"){
        return node.get("text").and_then(Value::as_str).unwrap_or("").to_string();
    }
    node.get("children").and_then(Value::as_array)
        .map(|children|children.iter().map(text_content).collect::<Vec<_>>().join(""))
        .unwrap_or_default()
}

fn scene_rows(snapshot:&Value)->Vec<String>{
    let tracks=find_id(snapshot,"tracks").expect("live Rust scene missing tracks");
    tracks["children"].as_array().expect("track rows").iter()
        .filter(|node|node.get("name").and_then(Value::as_str)==Some("row"))
        .map(text_content).collect()
}

fn assert_live_scene(snapshot:&Value,expected_clicks:usize){
    let panel=find_id(snapshot,"app").expect("live app panel missing");
    assert_eq!(panel["attrs"]["theme"],"light");
    assert_eq!(text_content(find_id(snapshot,"counter").expect("live counter missing")),"Count: 256");
    assert_eq!(text_content(find_id(snapshot,"event-button").expect("live event button missing")),format!("Clicks: {expected_clicks}"));
    let rows=scene_rows(snapshot);
    assert_eq!(rows.len(),48);
    assert_eq!(rows.first().map(String::as_str),Some("Track 40"));
    assert_eq!(rows.last().map(String::as_str),Some("Track 87"));
}

fn percentile(sorted:&[u64],p:f64)->Option<u64>{
    if sorted.is_empty(){None}else{
       let idx=(((sorted.len()-1) as f64)*p).ceil() as usize;
       Some(sorted[idx])
    }
}

impl Render for BenchView {
    fn render(&mut self,window:&mut Window,_cx:&mut Context<Self>)->impl IntoElement {
        #[cfg(target_os = "macos")]
        window.request_animation_frame();
        if let Ok(mut stats)=self.stats.try_borrow_mut(){
            stats.actual_render_calls+=1;
            if let Some(issued)=stats.pending_at.take(){
                stats.render_lag_us.push(issued.elapsed().as_micros() as u64);
            }
        }
        let snapshot=self.runtime.borrow().snapshot().expect("snapshot live Rust scene");
        let panel=find_id(&snapshot,"app").expect("panel");
        let theme=panel["attrs"]["theme"].as_str().unwrap_or("light");
        let counter=text_content(find_id(&snapshot,"counter").expect("counter"));
        let clicks=text_content(find_id(&snapshot,"event-button").expect("event button"));
        let rows=scene_rows(&snapshot);
        let bg=if theme=="dark"{rgb(0x132132)}else{rgb(0xf1f5fb)};
        let fg=if theme=="dark"{rgb(0xffffff)}else{rgb(0x122333)};
        div().size_full().bg(bg).text_color(fg).flex().flex_col().p_6().gap_1()
            .child(div().text_xl().child(format!("Live Hermes + GPUI : {}",self.framework)))
            .child(div().text_lg().child(counter))
            .child(div().child(clicks))
            .child(div().child(format!("48 live scene rows / theme: {}",theme)))
            .child(div().flex().flex_col().gap_1().children(rows.into_iter().map(|row|{
                div().h(px(15.)).text_sm().child(row)
            })))
    }
}

fn main(){
    let framework=env::var("HERMES_FRAMEWORK").expect("Missing HERMES_FRAMEWORK");
    let bootstrap=fs::read(env::var("HERMES_BOOTSTRAP_HBC").expect("Missing bootstrap HBC path")).expect("read bootstrap HBC");
    let framework_hbc=fs::read(env::var("HERMES_FRAMEWORK_HBC").expect("Missing framework HBC path")).expect("read framework HBC");
    let click_hbc=fs::read(env::var("HERMES_CLICK_HBC").expect("Missing click HBC path")).expect("read click HBC");

    let mut engine=SceneRuntime::new().expect("create in-process Hermes VM and JSI Rust sink");
    engine.eval_hbc(&bootstrap).expect("install Hermes host globals");
    engine.eval_hbc(&framework_hbc).unwrap_or_else(|error|panic!("{framework} HBC execution failed: {error}"));
    let initial=engine.snapshot().expect("initial live Rust scene");
    assert_live_scene(&initial,1000);
    let initial_batches=engine.batches();
    let initial_operations=engine.operations();
    engine.take_pending_at();
    println!("GPUI_LIVE_HERMES_VM_READY:{framework}:batches={initial_batches}:ops={initial_operations}");

    let runtime=Rc::new(RefCell::new(engine));
    let stats=Rc::new(RefCell::new(FrameStats::default()));
    let state=BenchView{framework:framework.clone(),runtime:runtime.clone(),stats:stats.clone()};
    gpui_platform::application().run(move|cx:&mut App|{
        if !example_support::load_fonts(cx){return;}
        let bounds=Bounds::centered(None,size(px(1000.),px(880.)),cx);
        let entity=cx.new(|_|state);
        let visible_entity=entity.clone();
        let window_handle=cx.open_window(WindowOptions{
            window_bounds:Some(WindowBounds::Windowed(bounds)),..Default::default()
        },move|_,_|visible_entity).expect("Native GPUI window creation failed");
        cx.activate(true);
        println!("GPUI_WINDOW_CREATED");
        let executor=cx.background_executor().clone();
        cx.spawn(async move|async_cx|{
            executor.timer(Duration::from_millis(300)).await;
            stats.borrow_mut().driver_start=Some(Instant::now());
            for _ in 0..120 {
                executor.timer(Duration::from_millis(16)).await;
                let pending={
                    let mut engine=runtime.borrow_mut();
                    engine.eval_hbc(&click_hbc).expect("execute persistent framework click HBC");
                    engine.take_pending_at().expect("JSI gpuiEmit did not deliver a mutation batch")
                };
                window_handle.update(async_cx,|view,window,cx|{
                    {
                        let mut measured=view.stats.borrow_mut();
                        measured.ui_updates+=1;
                        measured.pending_at=Some(pending);
                    }
                    cx.notify();
                    window.refresh();
                }).expect("update GPUI root window from live Hermes mutation");
            }
            executor.timer(Duration::from_millis(250)).await;
            let final_snapshot=runtime.borrow().snapshot().expect("final live scene");
            assert_live_scene(&final_snapshot,1120);
            let engine=runtime.borrow();
            let measured=stats.borrow();
            let mut samples=measured.render_lag_us.clone();
            samples.sort_unstable();
            let result=serde_json::json!({
                "schema":"gpui-render-replay/v1",
                "framework":framework,
                "driver":"gpui-timer-repeated-framework-click-hbc",
                "source":"live-Hermes-HBC-in-process",
                "live_hermes_vm":true,
                "live_jsi_to_gpui":true,
                "metric":"jsi_mutation_to_render_callback_us_NOT_GPU_present",
                "target_interval_ms":16,
                "scheduled_updates":120,
                "applied_updates":measured.ui_updates,
                "render_callbacks_with_pending_update":samples.len(),
                "render_callback_count":measured.actual_render_calls,
                "p50_us":percentile(&samples,0.50),
                "p95_us":percentile(&samples,0.95),
                "p99_us":percentile(&samples,0.99),
                "hermes_mutation_batches":engine.batches(),
                "scene_operations":engine.operations(),
                "elapsed_ms":measured.driver_start.map(|at|at.elapsed().as_millis() as u64),
                "gpu_present_latency_ms":null,
                "end_to_end_latency_ms":null
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
