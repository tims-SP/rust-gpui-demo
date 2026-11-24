//! In-process Hermes HBC → JSI → Rust Scene → GPUI Mobile Render acceptance view.
//!
//! The HBC paths and framework are fixed at build time by CI so each APK or
//! Simulator app contains the exact tested bytecode. This file is copied into
//! the pinned GPUI Mobile example only by the mobile live-Hermes CI job.

use gpui::{
    div, prelude::*, rgb, px, App, Context, Window, WindowOptions,
};
use gpui_hermes_live_spike::SceneRuntime;
use serde_json::Value;
use std::{
    cell::RefCell,
    rc::Rc,
    time::{Duration, Instant},
};

const FRAMEWORK: &str = env!("GPUI_LIVE_HERMES_FRAMEWORK");
const BOOTSTRAP_HBC: &[u8] = include_bytes!(env!("GPUI_LIVE_HERMES_BOOTSTRAP_HBC"));
const CLICK_HBC: &[u8] = include_bytes!(env!("GPUI_LIVE_HERMES_CLICK_HBC"));
const FRAMEWORK_HBC: &[u8] = include_bytes!(env!("GPUI_LIVE_HERMES_FRAMEWORK_HBC"));

#[derive(Default)]
struct FrameStats {
    pending_at: Option<Instant>,
    render_lag_us: Vec<u64>,
    applied_updates: u64,
    render_callbacks: u64,
    driver_start: Option<Instant>,
}

struct LiveHermesView {
    runtime: Rc<RefCell<SceneRuntime>>,
    stats: Rc<RefCell<FrameStats>>,
}

fn find_id<'a>(node: &'a Value, id: &str) -> Option<&'a Value> {
    if node
        .get("attrs")
        .and_then(|attrs| attrs.get("id"))
        .and_then(Value::as_str)
        == Some(id)
    {
        return Some(node);
    }
    node.get("children")?
        .as_array()?
        .iter()
        .find_map(|child| find_id(child, id))
}

fn text_content(node: &Value) -> String {
    if node.get("type").and_then(Value::as_str) == Some("text") {
        return node
            .get("text")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned();
    }
    node.get("children")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .map(text_content)
        .collect()
}

fn scene_rows(snapshot: &Value) -> Vec<String> {
    let tracks = find_id(snapshot, "tracks").expect("live Rust scene missing tracks");
    tracks["children"]
        .as_array()
        .expect("track children")
        .iter()
        .filter(|node| node.get("name").and_then(Value::as_str) == Some("row"))
        .map(text_content)
        .collect()
}

fn assert_scene(snapshot: &Value, expected_clicks: usize) {
    let panel = find_id(snapshot, "app").expect("live app panel missing");
    assert_eq!(panel["attrs"]["theme"], "light");
    assert_eq!(
        text_content(find_id(snapshot, "counter").expect("live counter missing")),
        "Count: 256"
    );
    assert_eq!(
        text_content(find_id(snapshot, "event-button").expect("live event button missing")),
        format!("Clicks: {expected_clicks}")
    );
    let rows = scene_rows(snapshot);
    assert_eq!(rows.len(), 48);
    assert_eq!(rows.first().map(String::as_str), Some("Track 40"));
    assert_eq!(rows.last().map(String::as_str), Some("Track 87"));
}

fn percentile(sorted: &[u64], p: f64) -> Option<u64> {
    if sorted.is_empty() {
        None
    } else {
        let index = (((sorted.len() - 1) as f64) * p).ceil() as usize;
        Some(sorted[index])
    }
}

impl Render for LiveHermesView {
    fn render(&mut self, window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        // Keep the mobile frame source active while the 120 mutation events run.
        window.request_animation_frame();
        if let Ok(mut stats) = self.stats.try_borrow_mut() {
            stats.render_callbacks += 1;
            if let Some(issued) = stats.pending_at.take() {
                stats.render_lag_us.push(issued.elapsed().as_micros() as u64);
            }
        }
        let snapshot = self
            .runtime
            .borrow()
            .snapshot()
            .expect("snapshot live Rust scene");
        let panel = find_id(&snapshot, "app").expect("live panel");
        let theme = panel["attrs"]["theme"].as_str().unwrap_or("light");
        let counter = text_content(find_id(&snapshot, "counter").expect("counter"));
        let clicks = text_content(find_id(&snapshot, "event-button").expect("event button"));
        let rows = scene_rows(&snapshot);
        let (background, foreground) = if theme == "dark" {
            (rgb(0x132132), rgb(0xffffff))
        } else {
            (rgb(0xf1f5fb), rgb(0x122333))
        };

        div()
            .size_full()
            .bg(background)
            .text_color(foreground)
            .flex()
            .flex_col()
            .p_4()
            .gap_1()
            .child(div().text_xl().child(format!("Live Hermes + GPUI Mobile: {FRAMEWORK}")))
            .child(div().text_lg().child(counter))
            .child(div().child(clicks))
            .child(div().child(format!("48 live scene rows / theme: {theme}")))
            .child(
                div()
                    .flex()
                    .flex_col()
                    .gap_1()
                    .children(rows.into_iter().map(|row| {
                        div().h(px(15.)).text_sm().child(row)
                    })),
            )
    }
}

/// Starts the single-window mobile acceptance app and drives real framework HBC.
pub fn open_main_window(cx: &mut App) {
    log::info!("GPUI_LIVE_HERMES_BOOT:{FRAMEWORK}");
    let mut engine = SceneRuntime::new().expect("create in-process Hermes VM and JSI Rust sink");
    engine
        .eval_hbc(BOOTSTRAP_HBC)
        .expect("install Hermes bootstrap host globals");
    engine
        .eval_hbc(FRAMEWORK_HBC)
        .unwrap_or_else(|error| panic!("{FRAMEWORK} framework HBC failed: {error}"));
    let initial = engine.snapshot().expect("initial live Rust scene");
    assert_scene(&initial, 1000);
    let initial_batches = engine.batches();
    let initial_operations = engine.operations();
    engine.take_pending_at();
    log::info!(
        "GPUI_LIVE_HERMES_VM_READY:{FRAMEWORK}:batches={initial_batches}:ops={initial_operations}"
    );

    let runtime = Rc::new(RefCell::new(engine));
    let stats = Rc::new(RefCell::new(FrameStats::default()));
    let state = LiveHermesView {
        runtime: runtime.clone(),
        stats: stats.clone(),
    };
    let window_handle = cx
        .open_window(WindowOptions::default(), move |_, _| state)
        .expect("open live Hermes GPUI Mobile window");
    cx.activate(true);

    let executor = cx.background_executor().clone();
    cx.spawn(async move |async_cx| {
        executor.timer(Duration::from_millis(300)).await;
        stats.borrow_mut().driver_start = Some(Instant::now());
        for _ in 0..120 {
            executor.timer(Duration::from_millis(16)).await;
            let pending = {
                let mut engine = runtime.borrow_mut();
                engine
                    .eval_hbc(CLICK_HBC)
                    .expect("execute persistent framework click HBC");
                engine
                    .take_pending_at()
                    .expect("JSI gpuiEmit did not deliver a mobile mutation batch")
            };
            window_handle
                .update(async_cx, |view, window, cx| {
                    {
                        let mut measured = view.stats.borrow_mut();
                        measured.applied_updates += 1;
                        measured.pending_at = Some(pending);
                    }
                    cx.notify();
                    window.refresh();
                })
                .expect("update mobile GPUI root window from live Hermes mutation");
        }

        executor.timer(Duration::from_millis(300)).await;
        let final_snapshot = runtime.borrow().snapshot().expect("final live mobile scene");
        assert_scene(&final_snapshot, 1120);
        let engine = runtime.borrow();
        let measured = stats.borrow();
        let mut samples = measured.render_lag_us.clone();
        samples.sort_unstable();
        let result = serde_json::json!({
            "schema":"gpui-render-replay/v1",
            "platform":std::env::consts::OS,
            "framework":FRAMEWORK,
            "driver":"gpui-mobile-timer-repeated-framework-click-hbc",
            "source":"live-Hermes-HBC-in-process",
            "live_hermes_vm":true,
            "live_jsi_to_gpui":true,
            "metric":"jsi_mutation_to_render_callback_us_NOT_GPU_present",
            "target_interval_ms":16,
            "scheduled_updates":120,
            "applied_updates":measured.applied_updates,
            "render_callbacks_with_pending_update":samples.len(),
            "render_callback_count":measured.render_callbacks,
            "p50_us":percentile(&samples,0.50),
            "p95_us":percentile(&samples,0.95),
            "p99_us":percentile(&samples,0.99),
            "initial_hermes_mutation_batches":initial_batches,
            "interactive_hermes_mutation_batches":engine.batches().saturating_sub(initial_batches),
            "hermes_mutation_batches":engine.batches(),
            "scene_operations":engine.operations(),
            "elapsed_ms":measured.driver_start.map(|at|at.elapsed().as_millis() as u64),
            "gpu_present_latency_ms":null,
            "end_to_end_latency_ms":null
        });
        log::info!("GPUI_REPLAY_BENCH_RESULT:{result}");
        if measured.applied_updates == 120
            && samples.len() >= 20
            && engine.batches().saturating_sub(initial_batches) == 120
        {
            log::info!("GPUI_LIVE_HERMES_PASS:{FRAMEWORK}");
            log::info!("GPUI_REPLAY_BENCH_PASS:{FRAMEWORK}");
        } else {
            log::error!("GPUI_LIVE_HERMES_INSUFFICIENT_SAMPLES:{FRAMEWORK}");
            log::error!("GPUI_REPLAY_BENCH_INSUFFICIENT_SAMPLES:{FRAMEWORK}");
        }
        // The app remains open for screenshot capture after the acceptance marker.
    })
    .detach();
}
