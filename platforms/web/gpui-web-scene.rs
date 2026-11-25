// Official GPUI Web backend rendering Hermes scene updates (live WASM bridge or fallback replay).
use std::{borrow::Cow, cell::RefCell, collections::VecDeque, rc::Rc, time::Duration};
// web-time uses browser Performance.now() on wasm32; std::time::Instant panics.
use web_time::Instant;
use gpui::{
  ApplicationHandle, App, Bounds, Context, Window, WindowBounds, WindowOptions,
  div, prelude::*, px, rgb, size,
};
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

#[derive(Default)]
struct BridgeQueue {
  batches: VecDeque<String>,
  live_batches_seen: u64,
}

thread_local! {
  static APPLICATION: RefCell<Option<ApplicationHandle>> = RefCell::new(None);
  static BRIDGE_QUEUE: RefCell<BridgeQueue> = RefCell::new(BridgeQueue::default());
}

#[wasm_bindgen]
pub fn gpui_web_push_hermes_batch(payload: &str) {
  BRIDGE_QUEUE.with(|slot| {
    let mut q = slot.borrow_mut();
    if q.batches.len() < 4096 {
      q.batches.push_back(payload.to_owned());
      q.live_batches_seen += 1;
    }
  });
}

fn drain_hermes_batches() -> (Vec<String>, u64) {
  BRIDGE_QUEUE.with(|slot| {
    let mut q = slot.borrow_mut();
    let drained: Vec<String> = q.batches.drain(..).collect();
    (drained, q.live_batches_seen)
  })
}

fn percentile(sorted: &[u64], fraction: f64) -> Option<u64> {
  if sorted.is_empty() {
    return None;
  }
  Some(sorted[(((sorted.len() - 1) as f64) * fraction).ceil() as usize])
}

struct BenchView {
  stats: Rc<RefCell<FrameStats>>,
  framework: String,
  count: u64,
  theme: String,
  rows: Vec<String>,
}

impl BenchView {
  fn apply_mutation_payload(&mut self, raw_json: &str, cx: &mut Context<Self>) -> bool {
    let Ok(val) = serde_json::from_str::<Value>(raw_json) else {
      return false;
    };
    let mut changed = false;
    if let Some(arr) = val.as_array() {
      for op in arr {
        let Some(items) = op.as_array() else { continue; };
        match items.first().and_then(Value::as_str) {
          Some("text") => {
            if let Some(txt) = items.get(2).and_then(Value::as_str) {
              if let Some(first_row) = self.rows.first_mut() {
                *first_row = txt.to_owned();
              }
            }
            self.count += 1;
            changed = true;
          }
          Some("attr") => {
            if items.get(1).and_then(Value::as_str) == Some("theme") {
              if let Some(th) = items.get(2).and_then(Value::as_str) {
                self.theme = th.to_owned();
                changed = true;
              }
            }
          }
          Some("reorder") | Some("move") => {
            if !self.rows.is_empty() {
              self.rows.rotate_left(1);
              changed = true;
            }
          }
          _ => {}
        }
      }
    }
    if changed {
      if let Ok(mut stats) = self.stats.try_borrow_mut() {
        if stats.driver_start.is_none() {
          stats.driver_start = Some(Instant::now());
        }
        stats.applied_updates += 1;
        stats.pending_at = Some(Instant::now());
      }
      cx.notify();
    }
    changed
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
    if idx % 15 == 0 {
      self.theme = if self.theme == "dark" { "light" } else { "dark" }.to_owned();
    }
    self.rows.rotate_left(1);
    cx.notify();
  }
}

impl Render for BenchView {
  fn render(&mut self, _window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
    if let Ok(mut stats) = self.stats.try_borrow_mut() {
      stats.render_calls += 1;
      if let Some(issued) = stats.pending_at.take() {
        stats.render_lag_us.push(issued.elapsed().as_micros() as u64);
      }
    }
    let bg = if self.theme == "dark" { rgb(0x132132) } else { rgb(0xf1f5fb) };
    let fg = if self.theme == "dark" { rgb(0xffffff) } else { rgb(0x122333) };
    div()
      .size_full()
      .bg(bg)
      .text_color(fg)
      .flex()
      .flex_col()
      .p_6()
      .gap_1()
      .child(div().text_xl().child(format!("Hermes + GPUI Web : {}", self.framework)))
      .child(div().text_lg().child(format!("Count: {}", self.count)))
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

fn text(node: &Value) -> String {
  if node.get("type").and_then(Value::as_str) == Some("text") {
    return node.get("text").and_then(Value::as_str).unwrap_or("").to_string();
  }
  node
    .get("children")
    .and_then(Value::as_array)
    .map(|v| v.iter().map(text).collect::<Vec<_>>().join(""))
    .unwrap_or_default()
}

fn choose_scene() -> (&'static str, &'static str) {
  let query = web_sys::window()
    .and_then(|w| w.location().search().ok())
    .unwrap_or_default();
  if query.contains("f=solid") {
    ("solid", include_str!("scene-solid.json"))
  } else {
    ("svelte", include_str!("scene-svelte.json"))
  }
}

fn main() {
  gpui_platform::web_init();
  let (framework, json) = choose_scene();
  let doc: Value = serde_json::from_str(json).expect("Invalid Hermes scene JSON");
  let scene = &doc["scene"];
  let list = find_id(scene, "tracks").expect("Missing Hermes tracks");
  let rows: Vec<String> = list["children"]
    .as_array()
    .unwrap()
    .iter()
    .filter(|n| n.get("name").and_then(Value::as_str) == Some("row"))
    .map(text)
    .collect();
  assert_eq!(rows.len(), 48);
  assert_eq!(rows.first().map(String::as_str), Some("Track 40"));
  assert_eq!(rows.last().map(String::as_str), Some("Track 87"));

  let stats = Rc::new(RefCell::new(FrameStats::default()));
  let view = BenchView {
    stats: stats.clone(),
    framework: framework.to_owned(),
    count: doc["final"]["count"].as_u64().unwrap(),
    theme: doc["final"]["theme"].as_str().unwrap().to_string(),
    rows,
  };

  let handle = gpui_platform::application_with_web_backend(
    gpui_platform::WebBackendPreference::WebGl,
  )
  .run_embedded(move |cx: &mut App| {
    if let Err(err) = cx.text_system().add_fonts(vec![Cow::Borrowed(
      include_bytes!("../../../../assets/fonts/ibm-plex-sans/IBMPlexSans-Regular.ttf"),
    )]) {
      web_sys::console::error_1(&format!("Font load failed: {err}").into());
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
    web_sys::console::log_1(&"GPUI_WEB_IMPORT_SCENE_WINDOW_CREATED".into());

    let executor = cx.background_executor().clone();
    let framework = framework.to_owned();
    let stats_for_async = stats.clone();
    cx.spawn(async move |async_cx| {
      executor.timer(Duration::from_millis(300)).await;
      let mut idx: u64 = 0;
      let mut live_mode = false;
      loop {
        executor.timer(Duration::from_millis(16)).await;
        let (batches, seen_live) = drain_hermes_batches();
        if seen_live > 0 {
          live_mode = true;
        }
        if !batches.is_empty() {
          for batch in batches {
            let _ = entity.update(async_cx, |view, cx| {
              let _ = view.apply_mutation_payload(&batch, cx);
            });
            idx += 1;
          }
        } else if !live_mode && idx < 120 {
          let step_idx = idx;
          let _ = entity.update(async_cx, |view, cx| {
            view.apply_synthetic_step(step_idx, cx);
          });
          idx += 1;
        }

        let applied_now = stats_for_async.borrow().applied_updates;
        if applied_now >= 120 {
          break;
        }
      }

      executor.timer(Duration::from_millis(250)).await;
      let measured = stats_for_async.borrow();
      let mut values = measured.render_lag_us.clone();
      values.sort_unstable();
      let payload = json!({
        "schema": "gpui-render-replay/v1",
        "platform": "web",
        "framework": framework,
        "driver": if live_mode { "hermes-wasm-bridge" } else { "gpui-timer-internal" },
        "source": if live_mode { "live-Hermes-WASM-in-browser" } else { "precomputed-Hermes-scene" },
        "live_hermes_vm": live_mode,
        "live_jsi_to_gpui": live_mode,
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
        web_sys::console::error_1(
          &format!("GPUI_WEB_REPLAY_INSUFFICIENT:{}:{}", framework, values.len()).into(),
        );
      }
    })
    .detach();
  });
  APPLICATION.with(|slot| *slot.borrow_mut() = Some(handle));
}
