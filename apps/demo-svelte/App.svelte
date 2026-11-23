<svelte:options customRenderer="../../renderers/svelte/renderer.js" />
<script>
  let { control } = $props();
  let count = $state(0);
  let start = $state(0);
  let theme = $state("light");
  let expanded = $state(false);
  let ordering = $state(Array.from({ length: 1000 }, (_, i) => i));
  const tracks = Array.from({length: 10000}, (_, i) => ({
    id: "track-" + String(i).padStart(5, "0"),
    title: "Track " + String(i).padStart(5, "0"),
    seconds: 120 + (i % 180)
  }));
  let visible = $derived(tracks.slice(start, start + 48));
  control.increment = () => { count += 1; };
  control.move = () => { start = (start + 1) % (10000 - 48); };
  control.theme = () => { theme = theme === "light" ? "dark" : "light"; };
  control.reorder = () => { expanded = true; ordering = [...ordering].reverse(); };
  control.collapse = () => { expanded = false; };
</script>
<panel id="app" theme={theme}>
  <label id="header">Hermes + GPUI Test</label>
  <button id="counter" onclick={() => count += 1}>Counter {count}</button>
  {#if expanded}
    <list id="reorder">
      {#each ordering as id (id)}
        <item id={"reorder-" + id}>Entry {id}</item>
      {/each}
    </list>
  {:else}
    <list id="tracks">
      {#each visible as track (track.id)}
        <item id={track.id} style={theme === "dark" ? "color:white" : "color:black"}>
          <label>{track.title}</label>
          <label>{track.seconds}s</label>
        </item>
      {/each}
    </list>
  {/if}
</panel>
