# C06 · 状态来源与显式关闭值

适用：设置保存后同页仍显示旧值、关闭状态被回退为开启、多个开关被合并成一个布尔值、每个页面又各自创建缓存。

## 定位与根因

先标明每个状态来自哪里：登录时公共快照、该页最近服务端回查、未提交草稿。时间新旧和权威性不是同一回事：未提交草稿不能冒充其他页面已保存的服务端状态。

错误示意：

```js
const enabled = latestPageValue || sharedSnapshot.enabled;
```

当 0/false 是有效关闭值，该表达式会错误回退。使用 `??` 的前提是本接口明确只有 null/undefined 表示缺失；空字符串若也属于缺失，必须按契约单独处理。

```js verify
const assert = require('node:assert/strict');
const shared = { enabled: true };
const resolveEnabled = pageValue => pageValue ?? shared.enabled;
assert.equal(false || shared.enabled, true); // 复现错误
assert.equal(resolveEnabled(false), false);
assert.equal(resolveEnabled(0), 0);
assert.equal(resolveEnabled(null), true);
assert.equal(resolveEnabled(undefined), true);
assert.equal(resolveEnabled(''), ''); // ?? 不会替你定义空字符串语义
```

## 修复选择与边界

低频公共状态复用现有公共能力；设置页按已确认的数据来源顺序消费自身保存后的回查，缺失时才回退公共快照。若公共状态已负责统一更新，沿现有同步链处理，不另造逐页请求与缓存。

多项条件分别保留含义，明确组合关系；不要看到其中一个 flag 就推断整个功能已可用。保存失败或仅在弹窗确认时不发布“已保存”状态；草稿边界命中时选读 [C02](nested-drafts-and-labels.md)。

## 回归证据

列来源×取值的组合：新值 0/false、缺失、公共缓存为旧开启值、保存失败、取消、重新进入与其他入口。观察实际读取来源和请求次数，不以 UI 一次变化替代真实保存回查。
