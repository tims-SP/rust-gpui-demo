//! Mobile compatibility renderer for actual Hermes-produced Svelte/Solid scenes.
//! This gpui-mobile adapter consumes the same semantic JSON as desktop/Web.
//! It is NOT an embedded Hermes runtime: live JSI -> GPUI is a separate gate.
use gpui::{div, prelude::*, rgb};
use serde_json::Value;
use super::Router;

// G1 auto-test only: building the Home node tree is NOT a presented frame.
// The Actions screenshot probe alone emits BENCH_G1_RENDER_PASS.
#[cfg(feature = "bench-auto")]
static BOOT_SCENE_MARKER: std::sync::Once = std::sync::Once::new();

#[cfg(feature = "solid-demo")]
const FRAMEWORK: &str = "solid";
#[cfg(not(feature = "solid-demo"))]
const FRAMEWORK: &str = "svelte";
#[cfg(feature = "solid-demo")]
const SCENE: &str = include_str!("hermes-solid.json");
#[cfg(not(feature = "solid-demo"))]
const SCENE: &str = include_str!("hermes-svelte.json");

fn find_id<'a>(node: &'a Value, id: &str) -> Option<&'a Value> {
    if node.get("attrs").and_then(|a| a.get("id")).and_then(Value::as_str) == Some(id) {
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
        return node.get("text").and_then(Value::as_str).unwrap_or("").to_owned();
    }
    node.get("children").and_then(Value::as_array)
        .map(|items| items.iter().map(text).collect::<Vec<_>>().join(""))
        .unwrap_or_default()
}

/// GPUI Mobile's Home screen renders the exact final Hermes scene fields.
/// Never infer correctness from an APK compiling; runtime screenshot is separate.
pub fn render(_router: &Router, _cx: &mut gpui::Context<Router>) -> impl IntoElement {
    let payload: Value = serde_json::from_str(SCENE).expect("Hermes scene JSON invalid");
    assert_eq!(payload["framework"].as_str(), Some(FRAMEWORK));
    let final_state = &payload["final"];
    let scene = &payload["scene"];
    let tracks = find_id(scene, "tracks").expect("Hermes tracks node missing");
    let rows: Vec<String> = tracks["children"].as_array().expect("tracks not an array")
        .iter()
        .filter(|child| child.get("name").and_then(Value::as_str) == Some("row"))
        .map(text).collect();

    assert_eq!(final_state["count"].as_u64(), Some(256));
    assert_eq!(final_state["start"].as_u64(), Some(40));
    assert_eq!(final_state["theme"].as_str(), Some("light"));
    assert_eq!(rows.len(), 48, "Not all virtualized Hermes rows rendered");
    assert_eq!(rows.first().map(String::as_str), Some("Track 40"));
    assert_eq!(rows.last().map(String::as_str), Some("Track 87"));

    #[cfg(feature = "bench-auto")]
    BOOT_SCENE_MARKER.call_once(|| {
        log::info!("BENCH_G1_SCENE_BUILT:{FRAMEWORK}:count=256:rows=48");
    });

    div().size_full().flex().flex_col().gap_1().p_4()
        .bg(rgb(0xf1f5fb)).text_color(rgb(0x122333))
        .child(div().text_xl().child(format!("Hermes + GPUI Mobile : {FRAMEWORK}")))
        .child(div().text_lg().child("Count: 256"))
        .child(div().child("48 scene rows / theme: light"))
        .children(rows.into_iter().map(|row| {
            div().text_sm().child(row)
        }))
}
