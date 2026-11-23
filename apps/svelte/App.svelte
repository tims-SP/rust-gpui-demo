<svelte:options customRenderer="../../renderers/svelte.js" />
<script>
  let count=$state(0);
  let start=$state(0);
  let theme=$state("light");
  let rows=$derived(Array.from({length:48},(_,i)=>({id:start+i,title:"Track "+(start+i)})));
  globalThis.__gpuiDrive=(op,value)=>{
    if(op==="counter")count=value;
    else if(op==="window")start=value;
    else if(op==="theme")theme=value;
    else throw Error("Unknown operation "+op);
  };
</script>
<panel id="app" {theme}>
  <label id="counter">Count: {count}</label>
  <list id="tracks">{#each rows as item (item.id)}<row id={"track-"+item.id}>{item.title}</row>{/each}</list>
</panel>
