<script lang="ts">
  let tracks = $state(Array.from({ length: 48 }, (_, id) => ({ id, title: "Song " + id })));
  let order = $state(tracks.map(song => song.id));
  let accent = $state("#8b5cf6");

  export function updateTitle(index: number, value: string) {
    tracks[index].title = value;
  }
  export function changeTheme(value: string) {
    accent = value;
  }
  export function rotate() {
    order = [...order.slice(1), order[0]];
  }
</script>

<div class="screen" style:--accent={accent}>
  {#each order as id (id)}
    <div class="row">
      <text class="song">{tracks[id].title}</text>
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
