# C02 · 嵌套草稿、标签名称与提交边界

适用：外层改名或排序，内层编辑子项，最后页面统一保存；确认后重开名称丢失；未编辑配置被清空。字段名和数据均为重构示例，先核当前接口的保存语义。

## 识别与定位

画出状态流：服务端查询结果 → 页面草稿 → 外层弹窗草稿 → 内层草稿 → 确认合并 → 页面提交 DTO。

- 对已约定统一保存的页面，弹窗确认不应擅自写后台或重拉列表，避免覆盖其他未保存编辑。
- 浅拷贝后编辑嵌套数组可能污染上层；为了保存而提前删除展示名称，则可能使未提交重开丢名。
- `detail.tasks || []` 把未返回字段与明确清空混为一谈。只有契约明确省略保留、空数组清空时，才使用本页的示例规则。

## 修复选择

编辑层使用隔离草稿，确认才合并到父草稿；页面提交时单独序列化白名单。展示节点留在草稿，不能随 DTO 清理一起提前丢弃。保存失败保留编辑，取消按该层边界恢复。

示例使用普通对象；真实框架的响应式代理不一定能直接 structuredClone。沿工程已有克隆方式处理，并验证嵌套引用隔离，不为复制示例而替换工程工具。

名称优先读取配置接口提供的展示信息，按已选标识匹配；不要从名称列表新增选择范围。缺名称时保留原标识或明确占位，不能自动扩大为全部范围；动态标签也不能展开为当前成员再永久保存。

```js verify
const assert = require('node:assert/strict');
const page = { id: 'rule-a', title: 'draft', selectedTagIds: ['tag-b'],
  labelNodes: [{ id: 'tag-b', name: 'Group B' }], tasksEdited: false };
const editor = structuredClone(page);
editor.labelNodes[0].name = 'Edited label';
assert.equal(page.labelNodes[0].name, 'Group B');
const confirmed = structuredClone(editor);
function toWrite(rule) {
  const dto = { id: rule.id, title: rule.title, tagIds: [...rule.selectedTagIds] };
  if (rule.tasksEdited) dto.tasks = rule.tasks.map(t => ({ id: t.id, title: t.title }));
  return dto;
}
const dto = toWrite(confirmed);
assert.equal('tasks' in dto, false); // 此示例契约：省略表示未编辑
assert.equal('labelNodes' in dto, false);
assert.equal(confirmed.labelNodes[0].name, 'Edited label'); // 重开仍可回显
assert.deepEqual(toWrite({ ...confirmed, tasksEdited: true, tasks: [] }).tasks, []);
const buggy = { tasks: page.tasks || [] };
assert.deepEqual(buggy.tasks, []); // 重现未编辑被误清空的风险
assert.deepEqual(dto.tagIds, ['tag-b']);
```

## 不可直接套用

即时保存的页面不必改成统一草稿；删除接口的语义也不能从“提交时省略字段”推断。临时草稿 key 与正式 ID 分开。并发用户写入仍需真实服务端版本控制，深拷贝不提供事务能力。前端补名称只作已确认过渡；有后端名称后检查并移除多余补查，不删除仍有调用者的公共能力。

## 回归证据

改 A 再改 B、两层确认、重开、取消、删除最后项、未返回任务字段、显式清空、失败重试都要覆盖。检查确认期间的写请求数、最终载荷字段及标识范围；有后端名称时观察是否仍额外请求名称列表。受控载荷通过不能替代真实保存回查。
