# C07 · 外层列宽正确，内部最小宽度仍溢出

适用：表格或 flex 内选择器超出容器、设置 width 后无效、短值正常但长标签撑开、只改截图红框而未验证完整状态。尺寸和选择器均为重构示例。

## 最小错误模型

```css
.cell { width: 160px; }
.picker { width: 100%; }
.picker__wrapper { min-width: 184px; }
```

外层宽度不自动覆盖后代最小宽度。还需检查父项 flex 的自动最小尺寸、padding、border、box-sizing 与内容不可折行约束；不能仅凭这段 CSS 推断真实页面根因。

## 如何确认

在真实 DOM 中取得 cell、组件根和内部 wrapper 的 `getBoundingClientRect()`，同时查看 computed width/min-width、padding 和 flex 属性。比较实际左右边界并定位第一个超出的盒子。

```js
// 页面诊断示意：选择器必须换成实际观察到的 DOM。
const nodes = ['.cell', '.picker', '.picker__wrapper'].map(s => document.querySelector(s));
if (nodes.some(el => !el)) throw Error('请先确认实际选择器');
const boxes = nodes.map(el => {
  const r = el.getBoundingClientRect(), c = getComputedStyle(el);
  return { left: r.left, right: r.right, width: r.width, minWidth: c.minWidth,
    padding: c.padding, boxSizing: c.boxSizing };
});
```

先修实际限制收缩的局部盒子；若公共组件契约已有尺寸参数优先使用。需要样式覆盖时限定到本页面/列和真实内部结构，不全局取消组件 min-width，也不盲目加 overflow:hidden 掩盖不可操作内容。`min-width:0` 应放到真正的约束点，不保证只改外层就有效。

## 回归与反例

测空值、短/长文案、多选标签、增删最后项、窄宽容器、缩放和校验提示。记录边界数值并核对邻列及其他页面无变化。另检验固定宽度本就是设计要求、弹层允许越过容器、字体未加载等正常或不同原因场景。

本页没有自动浏览器验证。Node 中比较假矩形不能证明真实 CSS 布局正确；需要当前页面或隔离浏览器夹具的测量结果。
