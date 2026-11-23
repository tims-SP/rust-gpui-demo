// Executed by the Hermes VM from compiler-matched HBC, never by Node or V8.
(function() {
  var demo = globalThis.__gpuiDemo;
  if (!demo || !demo.control || !demo.control.increment) throw Error("no component mounted");
  function collect(node, id, out) {
    if (node && typeof node === "object") {
      if (node.attrs && node.attrs.id === id) out.push(node);
      for (var i = 0; i < (node.children || []).length; i++) collect(node.children[i], id, out);
    }
  }
  function first(id) { var arr=[]; collect(demo.snapshot(), id, arr); return arr[0]; }
  function content(node) {
    return (node.children || []).map(function(x) {return typeof x === "string" ? x : content(x);}).join("");
  }
  demo.settle().then(function() {
    demo.flush();
    if (!first("counter") || content(first("counter")).trim() !== "Counter 0") throw Error("bad mount");
    demo.dispatch("counter", "click");
    for (var i=0;i<100;i++) demo.control.increment();
    for (var j=0;j<30;j++) demo.control.move();
    demo.control.theme();
    return demo.settle();
  }).then(function() {
    demo.flush();
    if (content(first("counter")).trim() !== "Counter 101") throw Error("bad counter");
    if (!first("track-00030") || first("app").attrs.theme !== "dark") throw Error("bad window/theme");
    demo.control.reorder();
    return demo.settle();
  }).then(function() {
    demo.flush();
    if (!first("reorder-999") || !first("reorder-000")) {
      // IDs are numeric in the demo: 'reorder-0' through 'reorder-999'.
      if (!first("reorder-999") || !first("reorder-0")) throw Error("bad keyed reorder");
    }
    if (!(globalThis.__receivedMutations > 1000)) throw Error("mutation callback missing");
    print("HERMES_HBC_CUSTOM_RENDERER_PASS=" + globalThis.__framework);
  }).catch(function(error) { print("HERMES_HBC_CUSTOM_RENDERER_FAIL " + error); });
})();
