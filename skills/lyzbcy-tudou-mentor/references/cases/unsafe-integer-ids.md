# C04 · 标识在 JSON 解析时丢失精度

适用：ID 看似相同却匹配失败、已选项回显或提交对象异常、服务端整型 ID 超出 JS 安全整数范围。数值是边界重构样本，不是业务记录。

## 定位顺序

比对原始响应文本、解析后值、状态/比较函数、保存载荷。开发者工具格式化展示与业务代码拿到的对象不一定处在同一解析阶段；后端错误和前端解析损失需分开。

错误：`String(JSON.parse(raw).id)`。普通解析已经舍入时，转换字符串或 JSON reviver 都无法恢复原数值。

```js verify
const assert = require('node:assert/strict');
const raw = '{"id":9007199254740993}';
const broken = JSON.parse(raw).id;
assert.equal(Number.isSafeInteger(broken), false);
assert.notEqual(String(broken), '9007199254740993');
const correctContract = JSON.parse('{"id":"9007199254740993","enabled":false,"version":0}');
assert.equal(correctContract.id, '9007199254740993');
assert.equal(correctContract.enabled, false);
assert.equal(correctContract.version, 0);
function normalizeId(value) {
  if (typeof value === 'string' && value.length) return value;
  if (typeof value === 'number' && Number.isSafeInteger(value)) return String(value);
  throw Error('Unreliable identifier');
}
assert.equal(normalizeId(7), '7');
assert.throws(() => normalizeId(broken));
```

## 修复选择

优先服务端把标识作为字符串返回。若短期只能兼容数字响应，确认当前请求适配器能获取未经默认解析的原始文本，再采用工程已有、经过审查的无损处理，限定到实际需要的接口。不能在已解析对象上补救。

不要据此复制“全局正则把所有数字加引号”：小数、负数、指数、字符串内数字、金额、版本和嵌套结构都有不同语义。原项目局部转换只能作为有条件经验，不能宣传为通用 JSON 解析器。缺少可靠解析能力时明确契约阻塞，不能编造丢失的末位。

## 回归证据

从原始文本到解析、比较、回显、保存逐层核对 ID 字符串；覆盖安全整数边界两侧、嵌套/数组、已是字符串、普通数值和空值。确认其他接口不受改动影响。示例仅证明精度机制及拒绝失真值，不代表已经验证某个请求库的原始响应钩子。
