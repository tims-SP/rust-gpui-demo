import { createSignal, For, Show } from "solid-js";
export default function App(props) {
  const [count, setCount] = createSignal(0);
  const [start, setStart] = createSignal(0);
  const [theme, setTheme] = createSignal("light");
  const [expanded, setExpanded] = createSignal(false);
  const [ordering, setOrdering] = createSignal(Array.from({length: 1000}, (_, i) => i));
  const tracks = Array.from({length: 10000}, (_, i) => ({
    id: "track-" + String(i).padStart(5, "0"),
    title: "Track " + String(i).padStart(5, "0"),
    seconds: 120 + (i % 180)
  }));
  const visible = () => tracks.slice(start(), start() + 48);
  props.control.increment = () => setCount((v) => v + 1);
  props.control.move = () => setStart((v) => (v + 1) % (10000 - 48));
  props.control.theme = () => setTheme((v) => v === "light" ? "dark" : "light");
  props.control.reorder = () => { setExpanded(true); setOrdering((ids) => [...ids].reverse()); };
  props.control.collapse = () => setExpanded(false);
  return (
    <panel id="app" theme={theme()}>
      <label id="header">Hermes + GPUI Test</label>
      <button id="counter" onClick={() => setCount((v) => v + 1)}>Counter {count()}</button>
      <Show when={expanded()} fallback={
        <list id="tracks">
          <For each={visible()}>{(track) =>
            <item id={track.id} style={theme() === "dark" ? "color:white" : "color:black"}>
              <label>{track.title}</label><label>{track.seconds}s</label>
            </item>
          }</For>
        </list>
      }>
        <list id="reorder">
          <For each={ordering()}>{(id) => <item id={"reorder-" + id}>Entry {id}</item>}</For>
        </list>
      </Show>
    </panel>
  );
}
