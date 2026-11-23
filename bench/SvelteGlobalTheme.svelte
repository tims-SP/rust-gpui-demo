<script lang="ts">
  import { set_css_vars } from "gpuix-svelte";
  let tracks = $state(Array.from({ length: 10000 }, (_, id) => ({ id, title: "Song " + id })));
  let order = $state(Array.from({ length: 48 }, (_, id) => id));
  let windowStart = $state(0);
  let visibleRows = $derived(windowStart === 0
    ? order.map(id => tracks[id])
    : tracks.slice(windowStart, windowStart + 48));
  let accent = $state("#8b5cf6");
  // Keep the same Svelte CSS rules, but move the theme token out of a local scope
  // so gpuix-svelte's rule_style() generation cache can be shared by all 48 rows.
  $effect(() => set_css_vars({ accent }));

  export function updateTitle(index: number, value: string) {
    tracks[index].title = value;
  }
  export function changeTheme(value: string) {
    accent = value;
  }
  export function rotate() {
    order = [...order.slice(1), order[0]];
  }
  export function shiftWindow(index: number) {
    windowStart = index;
  }
</script>

<div class="screen">
  {#each visibleRows as track (track.id)}
    <div class="row">
      <text class="song">{track.title}</text>
    </div>
  {/each}
</div>

<style>
  .screen {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    padding: 20px;
    gap: 2px;
    background-color: #101620;
  }
  .row {
    display: flex;
    flex-direction: row;
    height: 12px;
    padding: 3px;
  }
  .song {
    color: var(--accent);
    font-size: 12px;
  }
</style>
