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

<div>
  {#each visibleRows as track (track.id)}
    <div><text>{track.title}</text></div>
  {/each}
</div>
