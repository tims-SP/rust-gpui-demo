// Official GPUI Web backend rendering imported real Hermes scenes.
// Native Svelte/Solid HBC execution is verified separately in Chromium.
use std::{borrow::Cow,cell::RefCell,rc::Rc,time::Duration};
// web-time uses browser Performance.now() on wasm32; std::time::Instant panics.
use web_time::Instant;
use gpui::{
  ApplicationHandle,App,Bounds,Context,Window,WindowBounds,WindowOptions,
  div,prelude::*,px,rgb,size,
};
use serde_json::{Value,json};

#[derive(Default)]
struct FrameStats{
 pending_at:Option<Instant>,
 render_lag_us:Vec<u64>,
 applied_updates:u64,
 render_calls:u64,
 driver_start:Option<Instant>,
}
fn percentile(sorted:&[u64],fraction:f64)->Option<u64>{
 if sorted.is_empty(){return None;}
 Some(sorted[(((sorted.len()-1) as f64)*fraction).ceil() as usize])
}
struct BenchView{
 stats:Rc<RefCell<FrameStats>>,
  framework:String,
  count:u64,
  theme:String,
  rows:Vec<String>,
}
impl Render for BenchView{
  fn render(&mut self,_window:&mut Window,_cx:&mut Context<Self>)->impl IntoElement{
    if let Ok(mut stats)=self.stats.try_borrow_mut(){
      stats.render_calls+=1;
      if let Some(issued)=stats.pending_at.take(){
        stats.render_lag_us.push(issued.elapsed().as_micros() as u64);
      }
    }
    let bg=if self.theme=="dark"{rgb(0x132132)}else{rgb(0xf1f5fb)};
    let fg=if self.theme=="dark"{rgb(0xffffff)}else{rgb(0x122333)};
    div().size_full().bg(bg).text_color(fg).flex().flex_col().p_6().gap_1()
     .child(div().text_xl().child(format!("Hermes + GPUI Web : {}",self.framework)))
     .child(div().text_lg().child(format!("Count: {}",self.count)))
     .child(div().child(format!("48 scene rows | {}",self.theme)))
     .child(div().flex().flex_col().gap_1().children(self.rows.iter().map(|row|{
       div().h(px(15.)).text_sm().child(row.clone())
     })))
  }
}
fn find_id<'a>(node:&'a Value,id:&str)->Option<&'a Value>{
  if node.get("attrs").and_then(|v|v.get("id")).and_then(Value::as_str)==Some(id){return Some(node);}
  for child in node.get("children").and_then(Value::as_array).into_iter().flatten(){
    if let Some(found)=find_id(child,id){return Some(found);}
  }
  None
}
fn text(node:&Value)->String{
  if node.get("type").and_then(Value::as_str)==Some("text"){
    return node.get("text").and_then(Value::as_str).unwrap_or("").to_string();
  }
  node.get("children").and_then(Value::as_array)
    .map(|v|v.iter().map(text).collect::<Vec<_>>().join("")).unwrap_or_default()
}
fn choose_scene()->(&'static str,&'static str){
  let query=web_sys::window()
    .and_then(|w|w.location().search().ok()).unwrap_or_default();
  if query.contains("f=solid"){
    ("solid",include_str!("scene-solid.json"))
  }else{
    ("svelte",include_str!("scene-svelte.json"))
  }
}
thread_local!{
  static APPLICATION:RefCell<Option<ApplicationHandle>>=RefCell::new(None);
}
fn main(){
  gpui_platform::web_init();
  let (framework,json)=choose_scene();
  let doc:Value=serde_json::from_str(json).expect("Invalid Hermes scene JSON");
  let scene=&doc["scene"];
  let list=find_id(scene,"tracks").expect("Missing Hermes tracks");
  let rows:Vec<String>=list["children"].as_array().unwrap().iter()
    .filter(|n|n.get("name").and_then(Value::as_str)==Some("row"))
    .map(text).collect();
  assert_eq!(rows.len(),48);
  assert_eq!(rows.first().map(String::as_str),Some("Track 40"));
  assert_eq!(rows.last().map(String::as_str),Some("Track 87"));
  let stats=Rc::new(RefCell::new(FrameStats::default()));
  let view=BenchView{
    stats:stats.clone(),
    framework:framework.to_owned(),
    count:doc["final"]["count"].as_u64().unwrap(),
    theme:doc["final"]["theme"].as_str().unwrap().to_string(),
    rows
  };
  let handle=gpui_platform::application_with_web_backend(
    gpui_platform::WebBackendPreference::WebGl
  ).run_embedded(move|cx:&mut App|{
    if let Err(err)=cx.text_system().add_fonts(vec![Cow::Borrowed(
       include_bytes!("../../../../assets/fonts/ibm-plex-sans/IBMPlexSans-Regular.ttf")
    )]){
      web_sys::console::error_1(&format!("Font load failed: {err}").into());
      return;
    }
    let bounds=Bounds::centered(None,size(px(1100.),px(980.)),cx);
    let entity=cx.new(|_|view);
    let for_window=entity.clone();
    cx.open_window(WindowOptions{
      window_bounds:Some(WindowBounds::Windowed(bounds)),..Default::default()
    },move|_,_|for_window).expect("GPUI Web window creation failed");
    cx.activate(true);
    web_sys::console::log_1(&"GPUI_WEB_IMPORT_SCENE_WINDOW_CREATED".into());
    let executor=cx.background_executor().clone();
    let framework=framework.to_owned();
    cx.spawn(async move|async_cx|{
      executor.timer(Duration::from_millis(300)).await;
      stats.borrow_mut().driver_start=Some(Instant::now());
      for idx in 0..120{
        executor.timer(Duration::from_millis(16)).await;
        entity.update(async_cx, |view,cx|{
          {
            let mut measured=view.stats.borrow_mut();
            measured.applied_updates+=1;
            measured.pending_at=Some(Instant::now());
          }
          view.count+=1;
          if idx%15==0{view.theme=if view.theme=="dark"{"light"}else{"dark"}.to_owned();}
          view.rows.rotate_left(1);
          cx.notify();
        });
      }
      executor.timer(Duration::from_millis(250)).await;
      let measured=stats.borrow();
      let mut values=measured.render_lag_us.clone();
      values.sort_unstable();
      let payload=json!({
        "schema":"gpui-render-replay/v1","platform":"web", "framework":framework,
        "driver":"gpui-timer-internal","source":"precomputed-Hermes-scene",
        "live_hermes_vm":false,"live_jsi_to_gpui":false,
        "metric":"notify_to_render_callback_us_NOT_GPU_present",
        "scheduled_updates":120,"applied_updates":measured.applied_updates,
        "render_callbacks_with_pending_update":values.len(),
        "render_callback_count":measured.render_calls,
        "p50_us":percentile(&values,0.50),
        "p95_us":percentile(&values,0.95),
        "p99_us":percentile(&values,0.99),
        "elapsed_ms":measured.driver_start.map(|at|at.elapsed().as_millis() as u64)
      });
      if measured.applied_updates==120 && values.len()>=20{
        web_sys::console::log_1(&format!("GPUI_WEB_REPLAY_PASS:{}",framework).into());
        if let Some(element)=web_sys::window()
          .and_then(|w|w.document())
          .and_then(|d|d.get_element_by_id("gpui-bench-result")){
            element.set_text_content(Some(&payload.to_string()));
            let _=element.set_attribute("data-status","pass");
        }
      }else{
        web_sys::console::error_1(&format!("GPUI_WEB_REPLAY_INSUFFICIENT:{}:{}",framework,values.len()).into());
      }
    }).detach();
  });
  APPLICATION.with(|slot|*slot.borrow_mut()=Some(handle));
}
