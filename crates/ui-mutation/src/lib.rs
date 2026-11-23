//! Renderer-neutral JS -> Rust node graph and mutation operations.
//! No GPUI coupling: the adapter can safely be exercised before initializing a GPU.
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "lowercase")]
pub enum Mutation {
    Create { id: u64, kind: String, name: String, text: String },
    Insert { parent: u64, id: u64, before: Option<u64> },
    Remove { id: u64 },
    Text { id: u64, value: String },
    Attribute { id: u64, key: String, value: Option<String> },
    Event { id: u64, event: String, enabled: bool },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    pub id: u64,
    pub kind: String,
    pub name: String,
    pub text: String,
    pub attributes: BTreeMap<String, String>,
    pub events: BTreeMap<String, bool>,
    pub parent: Option<u64>,
    pub children: Vec<u64>,
}

#[derive(Debug, Default)]
pub struct Scene {
    pub nodes: HashMap<u64, Node>,
    pub operations: usize,
}

impl Scene {
    pub fn apply_batch(&mut self, batch: &[Mutation]) -> Result<(), String> {
        // Stage transactionally: a malformed batch must not half-mutate the visible graph.
        let mut working = Self { nodes: self.nodes.clone(), operations: self.operations };
        for op in batch {
            working.apply(op)?;
        }
        *self = working;
        Ok(())
    }

    fn apply(&mut self, op: &Mutation) -> Result<(), String> {
        match op {
            Mutation::Create { id, kind, name, text } => {
                if self.nodes.contains_key(id) { return Err(format!("duplicate id {id}")); }
                if !["fragment", "element", "text", "comment"].contains(&kind.as_str()) {
                    return Err(format!("invalid node kind {kind}"));
                }
                self.nodes.insert(*id, Node {
                    id: *id, kind: kind.clone(), name: name.clone(), text: text.clone(),
                    attributes: BTreeMap::new(), events: BTreeMap::new(),
                    parent: None, children: Vec::new()
                });
            }
            Mutation::Insert { parent, id, before } => {
                if !self.nodes.contains_key(parent) || !self.nodes.contains_key(id) {
                    return Err(format!("insert references missing parent={parent} node={id}"));
                }
                if parent == id { return Err("self-parenting".into()); }
                if Some(*id) == *before && self.nodes[id].parent == Some(*parent) {
                    self.operations += 1;
                    return Ok(());
                }
                if let Some(anchor) = before {
                    if self.nodes.get(anchor).and_then(|n| n.parent) != Some(*parent) {
                        return Err(format!("anchor {anchor} not under {parent}"));
                    }
                }
                let mut ancestor = Some(*parent);
                while let Some(a) = ancestor {
                    if a == *id { return Err("cycle".into()); }
                    ancestor = self.nodes.get(&a).and_then(|n| n.parent);
                }
                if let Some(old) = self.nodes[id].parent {
                    self.nodes.get_mut(&old).unwrap().children.retain(|v| v != id);
                }
                let siblings = &mut self.nodes.get_mut(parent).unwrap().children;
                let index = if let Some(anchor) = before {
                    siblings.iter().position(|v| v == anchor)
                        .ok_or_else(|| format!("missing anchor {anchor}"))?
                } else { siblings.len() };
                siblings.insert(index, *id);
                self.nodes.get_mut(id).unwrap().parent = Some(*parent);
            }
            Mutation::Remove { id } => {
                let parent = self.nodes.get(id).ok_or_else(|| format!("missing node {id}"))?.parent;
                if let Some(parent) = parent {
                    self.nodes.get_mut(&parent).unwrap().children.retain(|v| v != id);
                    self.nodes.get_mut(id).unwrap().parent = None;
                }
            }
            Mutation::Text { id, value } => {
                self.nodes.get_mut(id).ok_or_else(|| format!("missing text {id}"))?.text = value.clone();
            }
            Mutation::Attribute { id, key, value } => {
                let attrs = &mut self.nodes.get_mut(id)
                    .ok_or_else(|| format!("missing attribute node {id}"))?.attributes;
                if let Some(value) = value { attrs.insert(key.clone(), value.clone()); }
                else { attrs.remove(key); }
            }
            Mutation::Event { id, event, enabled } => {
                self.nodes.get_mut(id).ok_or_else(|| format!("missing event node {id}"))?
                    .events.insert(event.clone(), *enabled);
            }
        }
        self.operations += 1;
        Ok(())
    }

    pub fn root(&self) -> Option<&Node> {
        self.nodes.values().find(|n| n.kind == "fragment" && n.parent.is_none())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn insert_move_anchor_and_cycle() {
        let input = r#"[
          {"op":"create","id":1,"kind":"fragment","name":"","text":""},
          {"op":"create","id":2,"kind":"element","name":"list","text":""},
          {"op":"create","id":3,"kind":"text","name":"","text":"A"},
          {"op":"create","id":4,"kind":"text","name":"","text":"B"},
          {"op":"insert","id":2,"parent":1,"before":null},
          {"op":"insert","id":3,"parent":2,"before":null},
          {"op":"insert","id":4,"parent":2,"before":null},
          {"op":"insert","id":4,"parent":2,"before":3}
        ]"#;
        let ops: Vec<Mutation> = serde_json::from_str(input).unwrap();
        let mut scene = Scene::default();
        scene.apply_batch(&ops).unwrap();
        assert_eq!(scene.nodes[&2].children, vec![4, 3]);
        scene.apply_batch(&[Mutation::Insert { parent: 2, id: 4, before: Some(4) }]).unwrap();
        assert_eq!(scene.nodes[&2].children, vec![4, 3]);
        let before = scene.nodes.clone();
        assert!(scene.apply_batch(&[Mutation::Insert { parent: 4, id: 2, before: None }]).is_err());
        assert_eq!(scene.nodes, before);
    }
}
