# C05 · 分页筛选、有效零值与失效状态

适用：列表按状态筛选后人数异常、第二页遗漏、版本为 0 无法更新、开关关闭后隐藏条件仍影响查询。字段名为重构示例，实际参数以接口为准。

## 识别与定位

检查 `records.filter(...)` 是否只筛当前页，却沿用服务端总数。一般 `filter(paginate(S))` 不等于 `paginate(filter(S))`。完整本地数据集的纯前端分页是正常反例，不能看到 filter 就判错。

接口的状态和版本应按行读取；`if (!version)` 可能把有效的 0 当缺失。明确版本字段存在，也不能直接推断服务端实现了并发校验。

```js verify
const assert = require('node:assert/strict');
const rows = [{ id: 'a', active: false }, { id: 'b', active: true }, { id: 'c', active: true }];
const page = (xs, index) => xs.slice((index - 1) * 2, index * 2);
assert.equal(page(rows, 1).filter(x => x.active).length, 1);
assert.equal(page(rows.filter(x => x.active), 1).length, 2);
const hasVersion = row => row.version != null;
assert.equal(hasVersion({ version: 0 }), true);
assert.equal(hasVersion({ version: null }), false);
assert.equal(hasVersion({}), false);
const query = { pageIndex: 3, activeStates: ['active'], department: 'dept-a' };
function clearInactiveFilter(q) { return { ...q, pageIndex: 1, activeStates: [] }; }
assert.deepEqual(clearInactiveFilter(query), { pageIndex: 1, activeStates: [], department: 'dept-a' });
```

## 修复选择与边界

全量筛选应由有完整数据的查询端处理，前端传过滤条件、重置页码并消费对应总数。接口暂不支持时反馈契约限制，不擅自抓取整库伪装精确分页。

关闭控制开关时同步清除已经无效的筛选并重新查询；保留部门等无关条件。行更新使用查询得到的有效版本，成功/失败后的回查按当前协议恢复状态和人数。换页、换条件、组件卸载后，旧请求不能覆盖新列表；异步保护按 [C03](async-validation.md) 在命中该风险时选读。

## 回归证据

准备匹配项横跨两页的数据，核显示项、总数、页码与权限范围；测试版本 0、null、缺失、旧版本冲突。再测关闭开关、有旧筛选、查询失败及连续切换。受控分页样本通过不能证明后端真实统计、权限和并发控制通过。
