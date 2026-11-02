# C01 · 工程组件与统一异常

适用：业务页面新增按钮、表格、弹窗；一次失败出现两次提示；catch 后仍继续保存。先查实际组件和请求契约。本页代码为脱敏后的独立重构，不是可直接粘贴的工程 API。

## 识别与定位

- 新标签能渲染，但没有核对工程封装的权限、加载态、事件、插槽和选中值协议。
- 沿失败链查请求层是否已经展示错误，再看局部 catch 是否重复展示、吞掉失败或漏清 loading。
- 组件选型与异常职责分别判断；原生工具页不因业务工程使用封装组件就必须引入该组件库。

错误示意：请求层已提示失败，局部再弹一次，并返回表示成功的值。

```js
try {
  await saveRequest();
} catch (error) {
  showAnotherToast(error);
}
return true;
```

## 修复选择与边界

按当前工程复用组件，核对本次完整修改范围；不要靠名字猜 props，也不要仅替换标签名。无法访问在线资料时查本地实现、类型和成熟调用，并说明依据。

若统一层负责网络反馈，局部保留失败中断、业务结果校验和状态恢复。业务错误需要特定交互时按既有契约处理；不要盲删所有 catch 或强行增加新配置项。

下面只展示流程返回值的约定。真实工程用既有成功判定，HTTP resolve 不自动代表业务成功。

```js verify
const assert = require('node:assert/strict');
let pending = false;
async function save(request, isBusinessSuccess) {
  pending = true;
  try {
    const result = await request();
    return isBusinessSuccess(result);
  } catch {
    return false; // 网络展示由既有统一层负责
  } finally {
    pending = false;
  }
}
assert.equal(await save(async () => { throw Error('offline'); }, x => x.ok), false);
assert.equal(pending, false);
assert.equal(await save(async () => ({ ok: false }), x => x.ok), false);
assert.equal(await save(async () => ({ ok: true }), x => x.ok), true);
```

## 回归证据

检查失败反馈次数、保存请求次数、错误后的后续动作与 loading；再测成功、取消和业务拒绝。对组件验证真实事件、权限、回显、禁用及完整弹窗。上述 Node 示例不能证明组件交互或真实后端通过。
