//! The exact array-based mutation semantics used by shared/scene.js.
//! The scene is independent of any GPU, transport or platform; this is the
//! Rust boundary before a GPUI adapter accepts live Hermes JSI mutations.
use serde_json::{Map, Value};
use std::collections::BTreeMap;

#[derive(Clone, Debug)]
struct Node {
    kind: String,
    name: String,
    data: String,
    attrs: Map<String, Value>,
    parent: Option<u64>,
    children: Vec<u64>,
}

#[derive(Clone, Debug, Default)]
pub struct Scene {
    nodes: BTreeMap<u64, Node>,
    root: Option<u64>,
    operations: usize,
}

fn field<'a>(arr: &'a [Value], index: usize) -> Result<&'a Value, String> {
    arr.get(index).ok_or_else(|| format!("missing field #{index}"))
}
fn id(arr: &[Value], index: usize) -> Result<u64, String> {
    field(arr, index)?.as_u64().ok_or_else(|| format!("field #{index} is not a node id"))
}
fn string(arr: &[Value], index: usize) -> Result<&str, String> {
    field(arr, index)?.as_str().ok_or_else(|| format!("field #{index} is not a string"))
}
impl Scene {
    pub fn apply_batch(&mut self, batch: &[Value]) -> Result<(), String> {
        // No half-applied visible batch on malformed bridge input.
        let mut candidate = self.clone();
        for mutation in batch {
            candidate.apply(mutation)?;
        }
        *self = candidate;
        Ok(())
    }
    fn apply(&mut self, mutation: &Value) -> Result<(), String> {
        let a = mutation.as_array().ok_or("mutation must be JSON array")?;
        match string(a, 0)? {
            "create" => {
                let (id, kind, name, data) =
                    (id(a, 1)?, string(a, 2)?, string(a, 3)?, string(a, 4)?);
                if self.nodes.contains_key(&id) {
                    return Err(format!("duplicate create id={id}"));
                }
                if !matches!(kind, "fragment" | "element" | "text" | "comment") {
                    return Err(format!("unsupported kind={kind}"));
                }
                if kind == "fragment" && self.root.is_none() {
                    self.root = Some(id);
                }
                self.nodes.insert(id, Node {
                    kind: kind.to_owned(), name: name.to_owned(), data: data.to_owned(),
                    attrs: Map::new(), parent: None, children: vec![],
                });
            }
            "insert" => {
                let parent = id(a, 1)?;
                let child = id(a, 2)?;
                let before = field(a, 3)?.as_u64();
                if !self.nodes.contains_key(&parent) || !self.nodes.contains_key(&child) {
                    return Err(format!("missing parent/child in insert {parent}/{child}"));
                }
                if Some(child) == before && self.nodes[&child].parent == Some(parent) {
                    self.operations += 1;
                    return Ok(());
                }
                if parent == child { return Err("self-parenting".to_owned()); }
                if let Some(anchor) = before {
                    if self.nodes.get(&anchor).and_then(|n| n.parent) != Some(parent) {
                        return Err(format!("invalid insert anchor {anchor}"));
                    }
                }
                let mut ancestor = Some(parent);
                while let Some(value) = ancestor {
                    if value == child { return Err(format!("parenting cycle {child}")); }
                    ancestor = self.nodes.get(&value).and_then(|n| n.parent);
                }
                if let Some(old_parent) = self.nodes[&child].parent {
                    self.nodes.get_mut(&old_parent).unwrap().children.retain(|v| *v != child);
                }
                let siblings = &mut self.nodes.get_mut(&parent).unwrap().children;
                let position = match before {
                    None => siblings.len(),
                    Some(anchor) => siblings.iter().position(|v| *v == anchor)
                        .ok_or_else(|| format!("anchor vanished {anchor}"))?,
                };
                siblings.insert(position, child);
                self.nodes.get_mut(&child).unwrap().parent = Some(parent);
            }
            "remove" => {
                let (parent, child) = (id(a, 1)?, id(a, 2)?);
                if self.nodes.get(&child).and_then(|n| n.parent) != Some(parent) {
                    return Err(format!("remove parent mismatch {parent}/{child}"));
                }
                self.nodes.get_mut(&parent).unwrap().children.retain(|v| *v != child);
                self.nodes.get_mut(&child).unwrap().parent = None;
            }
            "text" => {
                let target = id(a, 1)?;
                let text = string(a, 2)?.to_owned();
                let node = self.nodes.get_mut(&target)
                    .ok_or_else(|| format!("text missing node {target}"))?;
                if node.kind != "text" && node.kind != "comment" {
                    return Err(format!("text target type invalid {target}"));
                }
                node.data = text;
            }
            "attr" => {
                let target = id(a, 1)?;
                let key = string(a, 2)?.to_owned();
                let value = field(a, 3)?;
                let attrs = &mut self.nodes.get_mut(&target)
                    .ok_or_else(|| format!("attribute missing node {target}"))?.attrs;
                if value.is_null() { attrs.remove(&key); }
                else { attrs.insert(key, value.clone()); }
            }
            "event" => {
                let target = id(a, 1)?;
                let _event_name = string(a, 2)?;
                let _enabled = field(a, 3)?.as_bool().ok_or("invalid event toggle")?;
                if !self.nodes.contains_key(&target) {
                    return Err(format!("event target missing {target}"));
                }
                // Event callbacks remain in Hermes; only serializable toggle crosses JSI.
            }
            op => return Err(format!("unsupported mutation {op}")),
        }
        self.operations += 1;
        Ok(())
    }
    pub fn operations(&self) -> usize { self.operations }
    pub fn node_count(&self) -> usize { self.nodes.len() }

    fn snapshot_node(&self, id: u64) -> Result<Value, String> {
        let node = self.nodes.get(&id).ok_or_else(|| format!("snapshot missing {id}"))?;
        let mut result = Map::new();
        result.insert("type".into(), Value::String(node.kind.clone()));
        if node.kind == "element" {
            result.insert("name".into(), Value::String(node.name.clone()));
            let attrs = node.attrs.iter().filter(|(key, _)| {
                !key.to_ascii_lowercase().starts_with("on")
            }).map(|(key, val)| (key.clone(), val.clone())).collect();
            result.insert("attrs".into(), Value::Object(attrs));
        }
        if node.kind == "text" {
            result.insert("text".into(), Value::String(node.data.clone()));
        }
        if !node.children.is_empty() {
            let children = node.children.iter().map(|child| self.snapshot_node(*child))
                .collect::<Result<Vec<_>, _>>()?;
            result.insert("children".into(), Value::Array(children));
        }
        Ok(Value::Object(result))
    }
    pub fn snapshot(&self) -> Result<Value, String> {
        let id = self.root.ok_or("no root fragment")?;
        self.snapshot_node(id)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn move_and_rollback() {
        let mut scene = Scene::default();
        scene.apply_batch(json!([
          ["create",1,"fragment","",""],["create",2,"element","list",""],
          ["create",3,"text","","A"],["create",4,"text","","B"],
          ["insert",1,2,null],["insert",2,3,null],["insert",2,4,null],
          ["remove",2,4],["insert",2,4,3]
        ]).as_array().unwrap()).unwrap();
        assert_eq!(scene.snapshot().unwrap()["children"][0]["children"][0]["text"], "B");
        let previous = scene.snapshot().unwrap();
        assert!(scene.apply_batch(json!([["insert",4,2,null]]).as_array().unwrap()).is_err());
        assert_eq!(previous, scene.snapshot().unwrap());
    }
}
