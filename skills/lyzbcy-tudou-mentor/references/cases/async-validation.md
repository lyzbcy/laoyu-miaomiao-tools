# C03 · 两种异步校验竞态

适用：输入查重/远程校验、多个 await 后统一提交、快速切换或关闭重开。代码为独立重构，用受控 Promise 展示时序。

## 先区分两个窗口

1. **请求乱序**：A 请求先发后回，覆盖 B 的结果。记录请求代次，并核当前输入和编辑版本；只取消请求不足以保证旧回调不执行。
2. **校验后变化**：A 已校验通过，等待其他子表单时用户改成 B。即使第一种保护正确，也不能拿 A 的结论提交 B；最终写入前再次核完整输入快照或编辑版本。

错误示意：

```js
if (await validateName(form.name)) {
  await validateOtherFields();
  await save(form); // form 可能已不是被校验的版本
}
```

## 修复与边界

请求代次控制同类异步工作的先后；编辑版本在相关字段每次变化时递增，关闭、重开、换记录也要失效。若仅比较名字，还需考虑其他影响校验或载荷的字段。下面的版本回调模拟完整表单变化；真实实现必须覆盖所有相关修改入口。

```js verify
const assert = require('node:assert/strict');
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const state = { name: 'A', revision: 0, latest: 0, verdict: null, pending: false };
async function check(request) {
  const own = ++state.latest, revision = state.revision, name = state.name;
  state.pending = true;
  const current = () => own === state.latest && revision === state.revision && name === state.name;
  try {
    const ok = await request(name);
    if (!current()) return 'stale';
    state.verdict = ok;
    return ok;
  } catch {
    if (!current()) return 'stale';
    state.verdict = false;
    return false;
  } finally { if (own === state.latest) state.pending = false; }
}
const a = deferred(), b = deferred();
const oldCheck = check(() => a.promise);
state.name = 'B'; state.revision++;
const newCheck = check(() => b.promise);
b.resolve(true); assert.equal(await newCheck, true);
a.resolve(false); assert.equal(await oldCheck, 'stale');
assert.equal(state.verdict, true);
let writes = 0;
async function submit(otherValidation) {
  const revision = state.revision;
  if (await check(async () => true) !== true) return false;
  if (!await otherValidation()) return false;
  if (state.revision !== revision) return false;
  // 检查与复制之间没有新的 await；校验对象与本次载荷保持同一版本。
  const payload = structuredClone({ name: state.name });
  writes++; return payload;
}
assert.equal(await submit(async () => { state.name = 'C'; state.revision++; return true; }), false);
assert.equal(writes, 0);
assert.deepEqual(await submit(async () => true), { name: 'C' });
assert.equal(writes, 1);
assert.equal(await check(async () => { throw Error('unavailable'); }), false);
assert.equal(state.pending, false);
const c = deferred();
const obsolete = check(() => c.promise);
state.name = 'D'; state.revision++; // 只改值，尚未触发新请求
c.resolve(true);
assert.equal(await obsolete, 'stale');
assert.equal(state.pending, false); // 最新请求结束仍应收尾，不能把结果失效等同于loading归属失效
```

loading 按请求代次归属，结果是否可用还要核输入快照；不能由旧请求 finally 清掉新请求状态，也不能因最新请求对应输入已变就永远不收尾。关闭/切换时递增失效代次并清理该界面的 loading。不同业务请求不要无条件共用全局代次。

若产品明确允许保存点击时的快照，可从开始固定载荷并让所有校验与写入使用同一份载荷；不能机械要求界面任意变化都中断。禁用编辑也是可选策略，但必须覆盖真实修改入口。取消前端请求不等于撤回已到服务端的写入。

## 回归证据

用可控延迟分别测试旧成功/旧失败晚到、检查中改值、检查后等待其他校验时改值、关闭重开及网络失败。再测试无变化的正常提交和必需的独立请求。断言写请求次数、提交的字段快照与加载状态，而不只观察错误文案。
