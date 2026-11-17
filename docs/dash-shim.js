// A small stand-in for the dashboard runtime: serves the demo data, runs calcs and redraws marked elements.
(function () {
  const raw = window.DEMO_DATA || {};
  const calcs = new Map();
  const cache = new Map();
  const draws = new Map();
  const mounted = new Map();
  const ok = (data) => ({ status: 'ok', data, message: null, refreshing: false, truncated: false, meta: null, columns: data && data[0] ? Object.keys(data[0]) : [] });

  const dash = {
    colors: ['#2f6fb5', '#8e5bb5', '#c98a1b', '#7a5cc4', '#2a9d8f', '#d17a9e', '#5f7d95', '#9a7b4f'],
    loader() {},
    calc(id, spec) { calcs.set(id, spec); cache.delete(id); },
    data(id) {
      if (cache.has(id)) return cache.get(id);
      let out;
      if (calcs.has(id)) {
        const spec = calcs.get(id);
        try { out = ok(spec.fn(...spec.inputs.map((i) => dash.data(i).data || []))); }
        catch (e) { console.error(id, e); out = { status: 'error', data: null, message: String(e) }; }
      } else if (id in raw) out = ok(raw[id]);
      else out = { status: 'missing', data: [], message: 'No such source' };
      cache.set(id, out);
      return out;
    },
    onData(fn) { fn(); },
    draw(name, fn) {
      if (fn !== undefined) { draws.set(name, fn); if (dash._ready) run(name); return; }
      run(name);
    },
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) { /* file:// */ } },
    params: () => ({}), setParams() {}, resetParams() {}, refresh() {}
  };

  function run(name) {
    const fn = draws.get(name);
    if (!fn) return;
    document.querySelectorAll(`[data-draw="${CSS.escape(name)}"]`).forEach((el) => {
      if (typeof fn === 'function') {
        try { fn(el); } catch (e) { console.error('draw', name, e); }
      } else if (fn && fn.mount && !mounted.has(el)) {
        mounted.set(el, fn.mount(el));
      }
    });
  }
  dash._ready = false;
  dash._runAll = () => { dash._ready = true; draws.forEach((_, n) => run(n)); };
  window.dash = dash;

  let w = window.innerWidth, t = null;
  window.addEventListener('resize', () => {
    if (Math.abs(window.innerWidth - w) < 8) return;
    w = window.innerWidth; clearTimeout(t);
    t = setTimeout(() => draws.forEach((fn, n) => { if (typeof fn === 'function') run(n); }), 150);
  });
})();
