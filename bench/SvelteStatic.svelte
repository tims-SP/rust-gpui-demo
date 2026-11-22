<script lang="ts">
  let tracks = $state(Array.from({ length: 10000 }, (_, id) => ({ id, title: "Song " + id })));
  let order = $state(Array.from({ length: 48 }, (_, id) => id));
  let windowStart = $state(0);
  let visibleRows = $derived(windowStart === 0
    ? order.map(id => tracks[id])
    : tracks.slice(windowStart, windowStart + 48));

  export function updateTitle(index: number, value: string) { tracks[index].title = value; }
  export function rotate() { order = [...order.slice(1), order[0]]; }
  export function shiftWindow(index: number) { windowStart = index; }
</script>

<!-- Immutable layout and text color only: no class rules, CSS vars or dynamic styling. -->
<div style="display:flex;flex-direction:column;width:100%;height:100%;padding:20px;gap:2px;background-color:#101620">
  {#each visibleRows as track (track.id)}
    <div style="display:flex;flex-direction:row;height:12px;padding:3px">
      <text style="color:#8b5cf6;font-size:12px">{track.title}</text>
    </div>
  {/each}
</div>
