// Official GPUI Web backend rendering Hermes scene updates (live WASM bridge or fallback replay).
use std::{borrow::Cow, cell::RefCell, collections::VecDeque, rc::Rc, time::Duration};
// web-time uses browser Performance.now() on wasm32; std::time::Instant panics.
use web_time::Instant;
use gpui::{
  ApplicationHandle, App, Bounds, Context, Window, WindowBounds, WindowOptions,
  div, prelude::*, px, rgb, size,
};
use gpui_ui_mutation::Scene;
use serde_json::{Value, json};
use wasm_bindgen::prelude::*;

#[derive(Default)]
struct FrameStats {
  pending_at: Option<Instant>,
  render_lag_us: Vec<u64>,
  applied_updates: u64,
  render_calls: u64,
  driver_start: Option<Instant>,
}

struct BridgeState {
  batches: VecDeque<(Instant, String)>,
  ready: bool,
  phase: &'static str,
  applied_updates: u64,
  render_samples: usize,
  error: Option<String>,
}

impl Default for BridgeState {
  fn default() -> Self {
    Self {
      batches: VecDeque::new(),
      ready: false,
      phase: "waiting_init",
      applied_updates: 0,
      render_samples: 0,
      error: None,
    }
  }
}

thread_local! {
  static APPLICATION: RefCell<Option<ApplicationHandle>> = RefCell::new(None);
  static BRIDGE: RefCell<BridgeState> = RefCell::new(BridgeState::default());
}

#[wasm_bindgen]
pub fn gpui_web_push_hermes_batch(payload: &str) {
  let received_at = Instant::now();
  BRIDGE.with(|slot| {
    let mut state = slot.borrow_mut();
    if state.batches.len() < 4096 {
      state.batches.push_back((received_at, payload.to_owned()));
    }
  });
}

#[wasm_bindgen]
pub fn gpui_web_get_state() -> String {
  BRIDGE.with(|slot| {
    let state = slot.borrow();
    json!({
      "ready": state.ready,
      "phase": state.phase,
      "applied_updates": state.applied_updates,
      "render_samples": state.render_samples,
      "error": state.error,
    })
    .to_string()
  })
}

fn drain_hermes_batches() -> Vec<(Instant, String)> {
  BRIDGE.with(|slot| slot.borrow_mut().batches.drain(..).collect())
}

fn set_bridge_phase(phase: &'static str) {
  BRIDGE.with(|slot| slot.borrow_mut().phase = phase);
}

fn set_bridge_ready() {
  BRIDGE.with(|slot| slot.borrow_mut().ready = true);
}

fn set_bridge_progress(applied_updates: u64, render_samples: usize) {
  BRIDGE.with(|slot| {
    let mut state = slot.borrow_mut();
    state.applied_updates = applied_updates;
    state.render_samples = render_samples;
  });
}

fn set_bridge_error(msg: String) {
  BRIDGE.with(|slot| {
    let mut state = slot.borrow_mut();
    state.phase = "error";
    state.error = Some(msg.clone());
  });
  if let Some(element) = web_sys::window()
    .and_then(|w| w.document())
    .and_then(|d| d.get_element_by_id("gpui-bench-result"))
  {
    element.set_text_content(Some(&json!({ "error": msg }).to_string()));
    let _ = element.set_attribute("data-status", "fail");
  }
}

fn percentile(sorted: &[u64], fraction: f64) -> Option<u64> {
  if sorted.is_empty() {
    return None;
  }
  Some(sorted[(((sorted.len() - 1) as f64) * fraction).ceil() as usize])
}

fn find_id<'a>(node: &'a Value, id: &str) -> Option<&'a Value> {
  if node.get("attrs").and_then(|v| v.get("id")).and_then(Value::as_str) == Some(id) {
    return Some(node);
  }
  for child in node.get("children").and_then(Value::as_array).into_iter().flatten() {
    if let Some(found) = find_id(child, id) {
      return Some(found);
    }
  }
  None
}

fn text_content(node: &Value) -> String {
  if node.get("type").and_then(Value::as_str) == Some("text") {
    return node.get("text").and_then(Value::as_str).unwrap_or("").to_string();
  }
  node
    .get("children")
    .and_then(Value::as_array)
    .map(|v| v.iter().map(text_content).collect::<Vec<_>>().join(""))
    .unwrap_or_default()
}

fn extract_rows(snapshot: &Value) -> Result<Vec<String>, String> {
  let list = find_id(snapshot, "tracks").ok_or_else(|| "missing tracks node".to_owned())?;
  let children = list["children"].as_array().ok_or_else(|| "tracks missing children".to_owned())?;
  Ok(
    children
      .iter()
      .filter(|n| n.get("name").and_then(Value::as_str) == Some("row"))
      .map(text_content)
      .collect(),
  )
}

fn validate_live_scene(snapshot: &Value, expected_clicks: usize) -> Result<(String, String, String, Vec<String>), String> {
  let panel = find_id(snapshot, "app").ok_or_else(|| "live app panel missing".to_owned())?;
  let theme = panel["attrs"]["theme"].as_str().unwrap_or("light").to_owned();
  if theme != "light" {
    return Err(format!("unexpected theme: {theme}"));
  }
  let counter = text_content(find_id(snapshot, "counter").ok_or_else(|| "live counter missing".to_owned())?);
  if counter != "Count: 256" {
    return Err(format!("unexpected counter: {counter}"));
  }
  let clicks = text_content(find_id(snapshot, "event-button").ok_or_else(|| "live event-button missing".to_owned())?);
  let expected_label = format!("Clicks: {expected_clicks}");
  if clicks != expected_label {
    return Err(format!("unexpected clicks: got '{clicks}', expected '{expected_label}'"));
  }
  let rows = extract_rows(snapshot)?;
  if rows.len() != 48 {
    return Err(format!("unexpected row count: {}", rows.len()));
  }
  if rows.first().map(String::as_str) != Some("Track 40") || rows.last().map(String::as_str) != Some("Track 87") {
    return Err(format!("unexpected row bounds: {:?}..{:?}", rows.first(), rows.last()));
  }
  Ok((theme, counter, clicks, rows))
}

struct BenchView {
  stats: Rc<RefCell<FrameStats>>,
  live_mode: bool,
  framework: String,
  scene: Option<Scene>,
  counter_label: String,
  clicks_label: String,
  count: u64,
  theme: String,
  rows: Vec<String>,
}

impl BenchView {
  fn sync_from_live_scene(&mut self) -> Result<(), String> {
    let scene = self.scene.as_ref().ok_or_else(|| "live scene not initialized".to_owned())?;
    let snapshot = scene.snapshot()?;
    let panel = find_id(&snapshot, "app").ok_or_else(|| "missing app panel".to_owned())?;
    self.theme = panel["attrs"]["theme"].as_str().unwrap_or("light").to_owned();
    self.counter_label = text_content(find_id(&snapshot, "counter").ok_or_else(|| "missing counter".to_owned())?);
    self.clicks_label = text_content(find_id(&snapshot, "event-button").ok_or_else(|| "missing event-button".to_owned())?);
    self.rows = extract_rows(&snapshot)?;
    Ok(())
  }

  fn apply_live_batch(&mut self, raw_json: &str, received_at: Option<Instant>, cx: &mut Context<Self>) -> Result<(), String> {
    let parsed: Value = serde_json::from_str(raw_json).map_err(|e| format!("invalid batch JSON: {e}"))?;
    let ops = parsed.as_array().ok_or_else(|| "batch payload must be JSON array".to_owned())?;
    let scene = self.scene.as_mut().ok_or_else(|| "live scene missing".to_owned())?;
    scene.apply_batch(ops)?;
    if let Some(ts) = received_at {
      self.sync_from_live_scene()?;
      if let Ok(mut stats) = self.stats.try_borrow_mut() {
        if stats.driver_start.is_none() {
          stats.driver_start = Some(ts);
        }
        stats.applied_updates += 1;
        stats.pending_at = Some(ts);
        set_bridge_progress(stats.applied_updates, stats.render_lag_us.len());
      }
      cx.notify();
    }
    Ok(())
  }

  fn apply_synthetic_step(&mut self, idx: u64, cx: &mut Context<Self>) {
    if let Ok(mut stats) = self.stats.try_borrow_mut() {
      if stats.driver_start.is_none() {
        stats.driver_start = Some(Instant::now());
      }
      stats.applied_updates += 1;
      stats.pending_at = Some(Instant::now());
    }
    self.count += 1;
    self.counter_label = format!("Count: {}", self.count);
    if idx % 15 == 0 {
      self.theme = if self.theme == "dark" { "light" } else { "dark" }.to_owned();
    }
    if !self.rows.is_empty() {
      self.rows.rotate_left(1);
    }
    cx.notify();
  }
}

impl Render for BenchView {
  fn render(&mut self, _window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
    if let Ok(mut stats) = self.stats.try_borrow_mut() {
      stats.render_calls += 1;
      if let Some(issued) = stats.pending_at.take() {
        stats.render_lag_us.push(issued.elapsed().as_micros() as u64);
        set_bridge_progress(stats.applied_updates, stats.render_lag_us.len());
      }
    }
    let bg = if self.theme == "dark" { rgb(0x132132) } else { rgb(0xf1f5fb) };
    let fg = if self.theme == "dark" { rgb(0xffffff) } else { rgb(0x122333) };
    let title = if self.live_mode {
      format!("Live Hermes WASM + GPUI Web : {}", self.framework)
    } else {
      format!("Hermes + GPUI Web : {}", self.framework)
    };
    div()
      .size_full()
      .bg(bg)
      .text_color(fg)
      .flex()
      .flex_col()
      .p_6()
      .gap_1()
      .child(div().text_xl().child(title))
      .child(div().text_lg().child(self.counter_label.clone()))
      .child(div().child(self.clicks_label.clone()))
      .child(div().child(format!("48 scene rows | {}", self.theme)))
      .child(
        div()
          .flex()
          .flex_col()
          .gap_1()
          .children(self.rows.iter().map(|row| div().h(px(15.)).text_sm().child(row.clone()))),
      )
  }
}

fn choose_mode_and_framework() -> (bool, &'static str) {
  let query = web_sys::window()
    .and_then(|w| w.location().search().ok())
    .unwrap_or_default();
  let live_mode = query.contains("mode=live");
  let framework = if query.contains("f=solid") { "solid" } else { "svelte" };
  (live_mode, framework)
}

fn load_precomputed_scene(framework: &str) -> (u64, String, Vec<String>) {
  let json = if framework == "solid" {
    include_str!("scene-solid.json")
  } else {
    include_str!("scene-svelte.json")
  };
  let doc: Value = serde_json::from_str(json).expect("Invalid Hermes scene JSON");
  let rows = extract_rows(&doc["scene"]).expect("Missing Hermes tracks");
  assert_eq!(rows.len(), 48);
  assert_eq!(rows.first().map(String::as_str), Some("Track 40"));
  assert_eq!(rows.last().map(String::as_str), Some("Track 87"));
  let count = doc["final"]["count"].as_u64().unwrap();
  let theme = doc["final"]["theme"].as_str().unwrap().to_string();
  (count, theme, rows)
}

fn main() {
  gpui_platform::web_init();
  let (live_mode, framework) = choose_mode_and_framework();
  let stats = Rc::new(RefCell::new(FrameStats::default()));

  let view = if live_mode {
    BenchView {
      stats: stats.clone(),
      live_mode: true,
      framework: framework.to_owned(),
      scene: Some(Scene::default()),
      counter_label: "Count: 0".to_owned(),
      clicks_label: "Clicks: 0".to_owned(),
      count: 0,
      theme: "light".to_owned(),
      rows: Vec::new(),
    }
  } else {
    let (count, theme, rows) = load_precomputed_scene(framework);
    BenchView {
      stats: stats.clone(),
      live_mode: false,
      framework: framework.to_owned(),
      scene: None,
      counter_label: format!("Count: {}", count),
      clicks_label: "Clicks: 1000".to_owned(),
      count,
      theme,
      rows,
    }
  };

  let handle = gpui_platform::application_with_web_backend(
    gpui_platform::WebBackendPreference::WebGl,
  )
  .run_embedded(move |cx: &mut App| {
    if let Err(err) = cx.text_system().add_fonts(vec![Cow::Borrowed(
      include_bytes!("../../../../assets/fonts/ibm-plex-sans/IBMPlexSans-Regular.ttf"),
    )]) {
      set_bridge_error(format!("Font load failed: {err}"));
      return;
    }
    let bounds = Bounds::centered(None, size(px(1100.), px(980.)), cx);
    let entity = cx.new(|_| view);
    let for_window = entity.clone();
    cx.open_window(
      WindowOptions {
        window_bounds: Some(WindowBounds::Windowed(bounds)),
        ..Default::default()
      },
      move |_, _| for_window,
    )
    .expect("GPUI Web window creation failed");
    cx.activate(true);
    set_bridge_ready();
    web_sys::console::log_1(&"GPUI_WEB_IMPORT_SCENE_WINDOW_CREATED".into());

    let executor = cx.background_executor().clone();
    let framework = framework.to_owned();
    let stats_for_async = stats.clone();

    cx.spawn(async move |async_cx| {
      if live_mode {
        let mut initial_batches: u64 = 0;
        let mut interactive_batches: u64 = 0;
        let mut init_verified = false;
        loop {
          executor.timer(Duration::from_millis(4)).await;
          let batches = drain_hermes_batches();
          for (received_at, batch) in batches {
            if !init_verified {
              let res = entity.update(async_cx, |view, cx| {
                view.apply_live_batch(&batch, None, cx)
              });
              match res {
                Ok(()) => initial_batches += 1,
                Err(err) => {
                  set_bridge_error(format!("init batch #{initial_batches} failed: {err}"));
                  return;
                }
              }
              if initial_batches == 7 {
                let verify = entity.update(async_cx, |view, cx| -> Result<(), String> {
                  let snap = view.scene.as_ref().ok_or("missing scene")?.snapshot()?;
                  let (theme, counter, clicks, rows) = validate_live_scene(&snap, 1000)?;
                  view.theme = theme;
                  view.counter_label = counter;
                  view.clicks_label = clicks;
                  view.rows = rows;
                  cx.notify();
                  Ok(())
                });
                match verify {
                  Ok(()) => {
                    init_verified = true;
                    set_bridge_phase("interactive");
                  }
                  Err(err) => {
                    set_bridge_error(format!("initial live scene validation failed: {err}"));
                    return;
                  }
                }
              }
            } else {
              let res = entity.update(async_cx, |view, cx| {
                view.apply_live_batch(&batch, Some(received_at), cx)
              });
              match res {
                Ok(()) => interactive_batches += 1,
                Err(err) => {
                  set_bridge_error(format!("interactive batch #{interactive_batches} failed: {err}"));
                  return;
                }
              }
            }
          }
          if init_verified && stats_for_async.borrow().applied_updates >= 120 {
            break;
          }
        }

        executor.timer(Duration::from_millis(250)).await;
        let final_check = entity.update(async_cx, |view, _cx| -> Result<usize, String> {
          let scene = view.scene.as_ref().ok_or("missing scene")?;
          let snap = scene.snapshot()?;
          let _ = validate_live_scene(&snap, 1120)?;
          Ok(scene.operations())
        });
        let scene_operations = match final_check {
          Ok(ops) => ops,
          Err(err) => {
            set_bridge_error(format!("final live scene validation failed: {err}"));
            return;
          }
        };

        let measured = stats_for_async.borrow();
        let mut values = measured.render_lag_us.clone();
        values.sort_unstable();
        let payload = json!({
          "schema": "gpui-render-replay/v1",
          "platform": "web",
          "framework": framework,
          "driver": "hermes-wasm-emscripten-print-bridge",
          "source": "live-Hermes-WASM-in-browser",
          "live_hermes_vm": true,
          "live_jsi_to_gpui": true,
          "metric": "jsi_mutation_to_render_callback_us_NOT_GPU_present",
          "gpu_present_latency_ms": Value::Null,
          "end_to_end_latency_ms": Value::Null,
          "scheduled_updates": 120,
          "applied_updates": measured.applied_updates,
          "initial_hermes_mutation_batches": initial_batches,
          "interactive_hermes_mutation_batches": interactive_batches,
          "total_hermes_mutation_batches": initial_batches + interactive_batches,
          "scene_operations": scene_operations,
          "render_callbacks_with_pending_update": values.len(),
          "render_callback_count": measured.render_calls,
          "p50_us": percentile(&values, 0.50),
          "p95_us": percentile(&values, 0.95),
          "p99_us": percentile(&values, 0.99),
          "elapsed_ms": measured.driver_start.map(|at| at.elapsed().as_millis() as u64)
        });
        if measured.applied_updates == 120 && values.len() >= 20 {
          set_bridge_phase("done");
          web_sys::console::log_1(&format!("GPUI_WEB_LIVE_PASS:{}", framework).into());
          if let Some(element) = web_sys::window()
            .and_then(|w| w.document())
            .and_then(|d| d.get_element_by_id("gpui-bench-result"))
          {
            element.set_text_content(Some(&payload.to_string()));
            let _ = element.set_attribute("data-status", "pass");
          }
        } else {
          set_bridge_error(format!(
            "insufficient live samples: applied={} render_samples={}",
            measured.applied_updates,
            values.len()
          ));
        }
      } else {
        executor.timer(Duration::from_millis(300)).await;
        for step_idx in 0..120u64 {
          executor.timer(Duration::from_millis(16)).await;
          let _ = entity.update(async_cx, |view, cx| {
            view.apply_synthetic_step(step_idx, cx);
          });
        }
        executor.timer(Duration::from_millis(250)).await;
        let measured = stats_for_async.borrow();
        let mut values = measured.render_lag_us.clone();
        values.sort_unstable();
        let payload = json!({
          "schema": "gpui-render-replay/v1",
          "platform": "web",
          "framework": framework,
          "driver": "gpui-timer-internal",
          "source": "precomputed-Hermes-scene",
          "live_hermes_vm": false,
          "live_jsi_to_gpui": false,
          "metric": "jsi_mutation_to_render_callback_us_NOT_GPU_present",
          "gpu_present_latency_ms": Value::Null,
          "end_to_end_latency_ms": Value::Null,
          "scheduled_updates": 120,
          "applied_updates": measured.applied_updates,
          "render_callbacks_with_pending_update": values.len(),
          "render_callback_count": measured.render_calls,
          "p50_us": percentile(&values, 0.50),
          "p95_us": percentile(&values, 0.95),
          "p99_us": percentile(&values, 0.99),
          "elapsed_ms": measured.driver_start.map(|at| at.elapsed().as_millis() as u64)
        });
        if measured.applied_updates >= 120 && values.len() >= 20 {
          web_sys::console::log_1(&format!("GPUI_WEB_REPLAY_PASS:{}", framework).into());
          if let Some(element) = web_sys::window()
            .and_then(|w| w.document())
            .and_then(|d| d.get_element_by_id("gpui-bench-result"))
          {
            element.set_text_content(Some(&payload.to_string()));
            let _ = element.set_attribute("data-status", "pass");
          }
        } else {
          set_bridge_error(format!(
            "insufficient replay samples: applied={} render_samples={}",
            measured.applied_updates,
            values.len()
          ));
        }
      }
    })
    .detach();
  });
  APPLICATION.with(|slot| *slot.borrow_mut() = Some(handle));
}
