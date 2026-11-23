<svelte:options customRenderer="../../renderers/svelte.js" />
<script>
  let count=$state(0);
  let clicks=$state(0);
  let start=$state(0);
  let theme=$state("light");
  let expanded=$state(false);
  let order=$state(Array.from({length:1000},(_,i)=>i));
  let rows=$derived(Array.from({length:48},(_,i)=>({id:start+i,title:"Track "+(start+i)})));
  globalThis.__gpuiDrive=(op,value)=>{
    if(op==="counter")count=value;
    else if(op==="window")start=value;
    else if(op==="theme")theme=value;
    else if(op==="reorder"){expanded=true;order=[...order].reverse();}
    else if(op==="collapse")expanded=false;
    else throw Error("Unknown operation "+op);
  };
</script>
<panel id="app" {theme}>
  <label id="counter">Count: {count}</label>
  <button id="event-button" onclick={()=>clicks+=1}>Clicks: {clicks}</button>
  {#if expanded}
    <list id="reorder">{#each order as id (id)}<row id={"order-"+id}>Row {id}</row>{/each}</list>
  {:else}
    <list id="tracks">{#each rows as item (item.id)}<row id={"track-"+item.id}>{item.title}</row>{/each}</list>
  {/if}
</panel>
