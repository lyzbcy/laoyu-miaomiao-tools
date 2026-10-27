'use strict';
// The project supplies URLs, states and selectors; no project data lives here.
const comparison = (() => {
  let current, prdWindow, index = 0, cancelled = false, undo = [], timer, images = [];
  const state = text => { $('capabilityStatus').textContent = text; };
  const message = text => { $('demoStatus').textContent = text; };
  function stop() {
    cancelled = true;
    while (undo.length) { try { undo.pop()(); } catch (_) {} }
    index = 0;
    message('演示已停止；已恢复本次高亮和输入值。页面自身产生的变化需要按项目配置恢复。');
  }
  function reference() {
    const entry = $('entry').value, status = $('designState').value;
    const refs = (current.references || []).filter(r => (!r.entry || r.entry === entry) && (!r.state || r.state === status));
    $('refs').replaceChildren(...refs.map((r, i) => option(i, r.label || '参考资料')));
    function select() {
      const r = refs[Number($('refs').value)];
      $('refNote').textContent = r ? [r.note, r.source && '来源：' + r.source, r.version && '版本：' + r.version].filter(Boolean).join(' · ') : '当前入口和状态没有匹配资料';
      target($('refLink'), $('reference'), r?.url);
    }
    $('refs').onchange = select; select();
    clearTimeout(timer); images = [];
    if ($('preload').checked) timer = setTimeout(() => {
      images = refs.filter(r => r.type === 'image' && safe(r.url)).slice(0, 3).map(r => { const img = new Image(); img.src = safe(r.url); return img; });
    }, 500);
  }
  function entryChanged() {
    stop();
    const e = (current.entries || []).find(x => x.id === $('entry').value);
    target($('liveLink'), $('live'), e?.url || current.url);
    const refs = (current.references || []).filter(r => !r.entry || r.entry === $('entry').value);
    const states = [...new Set(refs.map(r => r.state).filter(Boolean))];
    $('designState').replaceChildren(option('', '默认'), ...states.map(s => option(s, s)));
    $('designState').value = states[0] || '';
    reference();
  }
  async function show(c) {
    stop(); current = c;
    const entries = c.entries?.length ? c.entries : [{id:'default', label:'默认入口', url:c.url}];
    $('entry').replaceChildren(...entries.map(e => option(e.id, e.label || e.id)));
    $('entry').value = entries[0].id;
    $('entry').onchange = entryChanged;
    $('designState').onchange = reference;
    entryChanged();
    state('图片按用例、入口和状态匹配；独立 PRD 定位仅支持同源可访问正文，跨站需项目适配器。系统置顶需另接本机窗口适配器。');
    message(c.demo?.length ? '就绪：' + c.demo.length + ' 步；演示结果不计入回归成绩。' : '当前用例未配置可执行演示。');
  }
  function prd() { return (current?.references || []).find(r => r.type === 'prd' && (!r.entry || r.entry === $('entry').value)); }
  $('openPrd').onclick = () => {
    const r = prd(), url = safe(r?.url);
    if (!url) return state('当前用例未配置 PRD 地址。');
    prdWindow = window.open(url, 'sharedRegressionPrd', 'popup,width=900,height=800');
    state(prdWindow ? '已打开或复用 PRD 窗口；浏览器不支持系统级置顶。' : 'PRD 窗口被浏览器拦截。');
  };
  $('locatePrd').onclick = () => {
    try {
      const text = prd()?.quote;
      if (!text) throw Error('未配置正文准确短句');
      if (!prdWindow || prdWindow.closed) throw Error('请先打开 PRD 窗口');
      const doc = prdWindow.document, walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
      const matches = []; let node;
      while ((node = walker.nextNode())) { let start = -1; while ((start = node.data.indexOf(text, start + 1)) !== -1) matches.push([node, start]); }
      if (matches.length !== 1) throw Error('正文短句命中 ' + matches.length + ' 次，不能确定唯一位置');
      const [n, start] = matches[0], range = doc.createRange(), selection = prdWindow.getSelection();
      range.setStart(n, start); range.setEnd(n, start + text.length); selection.removeAllRanges(); selection.addRange(range);
      n.parentElement?.scrollIntoView({block:'center'});
      if (selection.toString() !== text) throw Error('选区核验失败');
      state('已定位并选中正文：' + text);
    } catch (e) { state('无法定位正文：' + e.message + '。跨站文档需接入浏览器适配器。'); }
  };
  async function next() {
    const steps = current?.demo || [];
    if (index >= steps.length) { message('演示结束，未自动记为通过。'); return false; }
    const step = steps[index];
    try {
      const doc = $('live').contentDocument;
      if (!doc) throw Error('业务页面跨域，需项目浏览器适配器');
      const el = doc.querySelector(step.selector);
      if (!el) throw Error('未找到目标：' + step.selector);
      if (step.action === 'highlight') {
        const old = el.style.outline; el.style.outline = '3px solid #e33'; undo.push(() => { el.style.outline = old; }); el.scrollIntoView({block:'center'});
      } else if (step.action === 'input') {
        if (!('value' in el)) throw Error('目标不能输入');
        const old = el.value; undo.push(() => { el.value = old; el.dispatchEvent(new doc.defaultView.Event('input', {bubbles:true})); });
        el.value = String(step.value ?? ''); el.dispatchEvent(new doc.defaultView.Event('input', {bubbles:true}));
      } else if (step.action === 'click') el.click();
      else throw Error('不支持的演示动作');
      index++; message('已执行 ' + index + '/' + steps.length + '：' + (step.label || step.action)); return index < steps.length;
    } catch (e) { message('演示阻塞：' + e.message); return false; }
  }
  $('demoNext').onclick = () => { cancelled = false; next(); };
  $('demoAuto').onclick = async () => { cancelled = false; while (!cancelled && await next()) await new Promise(resolve => setTimeout(resolve, 500)); };
  $('demoStop').onclick = stop;
  $('preload').onchange = () => { clearTimeout(timer); images = []; if (current) reference(); };
  return {show};
})();
