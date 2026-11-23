// Official GPUI Web backend rendering imported real Hermes scenes.
// Native Svelte/Solid HBC execution is verified separately in Chromium.
use std::{borrow::Cow,cell::RefCell};
use gpui::{
  ApplicationHandle,App,Bounds,Context,Window,WindowBounds,WindowOptions,
  div,prelude::*,px,rgb,size,
};
use serde_json::Value;

struct BenchView{
  framework:String,
  count:u64,
  theme:String,
  rows:Vec<String>,
}
impl Render for BenchView{
  fn render(&mut self,_window:&mut Window,_cx:&mut Context<Self>)->impl IntoElement{
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
  let view=BenchView{
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
    cx.open_window(WindowOptions{
      window_bounds:Some(WindowBounds::Windowed(bounds)),..Default::default()
    },move|_,cx|cx.new(|_|view)).expect("GPUI Web window creation failed");
    cx.activate(true);
    web_sys::console::log_1(&"GPUI_WEB_IMPORT_SCENE_WINDOW_CREATED".into());
  });
  APPLICATION.with(|slot|*slot.borrow_mut()=Some(handle));
}
