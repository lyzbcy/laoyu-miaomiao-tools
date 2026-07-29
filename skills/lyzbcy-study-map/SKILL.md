---
name: lyzbcy-study-map
description: 把难度较高、跨领域的文稿拆成一份 source-grounded 的交互式 HTML 理解地图；也适用于课程章节、真题精讲、计算题手把手演示等学习场景。适合想真正学懂复杂文章、访谈、论文、技术长文或跨学科材料，以及备考复习的人。核心是保真拆解、原文依据、概念关系、论证结构和苏格拉底式追问；课程/真题场景另带手把手计算演示、真题蒸馏、表情包种草和自推广入口。默认用中文输出，除非用户明确指定其他语言。
---

# lyzbcy-study-map

> 把难啃的干货，拆成一张有原文依据、能追问、能复述、能继续学的交互式理解地图。文稿理解 + 课程/真题精讲双能。

## 一句话目标

lyzbcy 的目标不是把难内容“讲简单”，而是把难内容拆成一张**有原文依据、能追问、能复述、能继续学习**的 HTML 理解地图。

lyzbcy 的内核是：

- 知识拆解报告
- 研究笔记
- 苏格拉底式阅读
- source-grounded（原文依据）理解地图

lyzbcy 的外壳可以是：

- 闯关式学习路径
- 关卡
- 进度条
- 小任务
- 即时反馈

但优先级必须是：

**保真 > 结构清楚 > 理解友好 > 趣味包装**

---

## 适用场景

适合：

- 技术长文
- 跨领域访谈
- 投资、商业、AI、设计、社会科学类深度文稿
- 论文或研究型文章
- 用户想真正理解，而不是只要摘要

不适合：

- 纯新闻快讯
- API 参数手册
- 只需要行动步骤的教程
- 原文本身没有观点或结构的碎片材料

---

## 核心原则


### 首屏表达规则

第一屏不要写方法论说明或免责声明。

不要出现这类句子：

- “先补最少背景，再读原文判断。”
- “每个核心判断都带原文依据。”
- “背景补充不会伪装成作者原话。”

这些是生成规则，不是读者需要在首屏阅读的内容。

第一屏只保留：

- 主题标题
- 读者会学会什么
- 阅读路径

### 统计数字禁止写死（数据驱动规则）

页面里任何"X 章 / Y 题 / Z 个模块"这类**统计性数字，必须从已有的数据结构（如 `SEARCH_INDEX`、章节列表）动态计算，禁止手写成固定数字**。

坏味道（不可维护）：

```html
<!-- 写死：后来加了第7章、第20题，这行就成了错误信息 -->
<p>6 章 · 48 道互动题 · 每章含 11 个学习模块</p>
```

正确做法（数据驱动）：

```html
<!-- 占位，由 JS 从 SEARCH_INDEX 算出来，内容增减自动同步 -->
<p><span id="siteStats">加载中…</span> · 业务场景故事 + 对比表 + 硬数字卡片</p>
<script>
var chCount = SEARCH_INDEX.length;
var moduleCount = SEARCH_INDEX.reduce(function(s,ch){return s+ch.sections.length;},0);
document.getElementById('siteStats').textContent = chCount + ' 章 · ' + moduleCount + ' 个学习模块';
</script>
```

判断标准：**如果用户后来加了一章/一题/一个模块，这个数字会不会自动变？** 不会 = 写死了，必须改成数据驱动。

注意：

- 如果某个统计项的数据不在当前页（如各章互动题数只在 chapter*.html 里），不要在首页硬编一份易错的副本——要么用 JS 异步读取各章页，要么干脆不在首页展示这个数（交给各章页内进度条显示）。
- 标题里的「第 N 章」、导航里的章节名是**实体标识**，不是统计数字，可以正常写死。

### 闭环题目规则

lyzbcy 的互动题必须全部是闭环题。

允许题型：

- 单选题
- 多选题
- 判断题
- 匹配题
- 排序题

禁止题型：

- 开放式文本题
- 长段落自由回答
- 需要读者自己写一段话再由脚本模糊判断的题

如果需要训练“复述”，也要做成选择题：给 3 个复述版本，让读者选择哪个最不改变原意。

### 0. 零基础入口

lyzbcy 面向的是跨领域深度学习，不是假设读者已经懂这个领域。

正式拆原文之前，必须先补一个“最小背景包”。

最小背景包只解释读懂本文必须知道的 3 到 5 件事。

要求：

- 背景解释必须和原文问题直接相关
- 可以拓展原文没有展开的基础知识，但必须标注为“背景补充”
- 背景补充不能替代原文判断
- 每个背景概念最多 120 字

格式：

```text
背景补充：……
为什么现在需要知道：……
它不是本文的主张，只是帮助你读懂原文。
```

### 1. 保真优先

不要为了好懂而改写作者意思。

每个核心判断后面必须标注“原文依据”。

格式：

```text
核心判断：……
原文依据：……
解释：……
```

如果是你为了帮助理解做出的推论，必须明确标注：

```text
我的解释：……
注意：这不是原文原句，而是基于前后文的理解。
```

### 2. 区分四类信息

每个重要内容都要尽量标注类型：

- 事实：原文明确说了什么
- 判断：作者认为怎样
- 推论：从原文可以推出什么
- 例子：作者用什么案例说明

不要把判断写成事实。

不要把推论写成作者原话。

### 3. 不强行套因果链

不是所有文章都是因果链。

先判断原文结构，再选择合适地图：

- 机制型文章：用流程图
- 观点型文章：用论证图
- 访谈型文章：用主题簇 + 观点线索
- 历史型文章：用时间线
- 商业分析：用问题 → 判断 → 证据 → 风险

如果原文是并列结构，不要硬凑成单一主线。

### 4. 比喻可用，但不能替代定义

比喻只是辅助理解，不是知识本身。

比喻必须标注：

```text
类比：……
它帮助理解：……
它不能代表：……
```

如果比喻会扭曲原文，宁可不用。

### 5. 苏格拉底式引导

关键处不要直接给结论，要用问题帮助读者自己发现结构。

推荐问题：

- 作者真正想回答的问题是什么？
- 这句话是事实、判断，还是推论？
- 作者为什么要在这里引入这个概念？
- 如果删掉这个条件，结论还成立吗？
- 这个例子支持了哪个主张？
- 有没有另一个可能解释？
- 我能不能复述这句话，但不改变原意？

### 6. 闯关式包装，但不游戏化过度

可以使用：

- 学习路径
- 关卡
- 进度条
- 小测
- 即时反馈
- 错题回流
- 学习报告

但所有任务必须服务理解原文。

不要出为了互动而互动的题。

不要把复杂观点压成过度简单的选择题。

---

## 输出要求

- 输出一个自包含的 `.html` 文件
- 默认保存到当前工作目录
- 如果用户要求放到下载目录，保存到 `~/Downloads/`
- 文件名格式：`<原文标题> - 理解地图.html`（默认中文；仅当用户明确要求英文或其他语言时，才使用对应语言的文件名后缀，例如 `<Title> - Understanding Map.html`）
- HTML 可直接双击打开
- 可以使用少量原生 JavaScript
- 不依赖后端
- **默认输出中文**：无论原文是中文、英文还是其他语言，默认都用中文生成理解地图；原文依据可以保留原文原句，并在必要时附中文解释。只有用户明确指定英文或其他语言时，才按用户指定语言输出。

### 页脚署名（默认开启 · lyzbcy 推广）

每个生成的 HTML 在页脚放一行 lyzbcy 推广署名（**默认开启**）：

```html
由 <a href="https://lyzbcy.github.io/" target="_blank" rel="noopener"
  style="color:#1d70b8;text-decoration:underline;font-weight:700">捞鱼</a> 制作
```

要求：
- 「捞鱼」做成指向 `https://lyzbcy.github.io/` 的可见链接（蓝色 + 下划线，`target="_blank" rel="noopener"`）
- 另可保留一句友好的学习提醒（默认中文，除非用户指定其他语言），例如：「这个工具能帮你预习难啃的干货，但不能代替完整学习。学习愉快」

---

## 自推广体系（默认开启 · lyzbcy）

> 任何生成的页面（文稿或课程）都默认挂上 lyzbcy 自推广入口，把学习流量沉淀成粉丝。这是 os-study 项目验证过的成熟体系。

### 四大导流入口（都要有）

页面引入外部 `promo.css` + `promo.js`（独立文件，便于一处改全站生效）。参考实现见 os-study 仓库的 `promo.js`/`promo.css`。入口：
1. **右下浮条**：常驻「🐟关于捞鱼」按钮，点击弹模态框
2. **作者介绍区**（模态框顶部）：作者头像（圆形 72px）+ 工作室 tag + 名字 + 一句话签名 + 「了解更多」跳作者主页按钮
3. **三栏二维码 grid**（模态框下半）：QQ群、赞赏、表情包，各一个二维码图 + 文案
4. **页脚署名**：见上方「页脚署名」段

### 表情包种草（5 触点，默认开启）

"多多使用成品表情"≠ 挂个下载码——要把捞鱼/周三涵/星星布丁的真实表情图**铺进页面触点**做 IP 种草。表情图复制进项目 `img/sticker/` 自托管（与项目同仓，不用图床外链，永不变外链）。

5 个触点（按触达优先级）：
1. **答题反馈贴**（最高触达）：交互题答对贴 `ok.png`、答错贴 `no.png`，替换原 emoji ✅/❌。在 setFb 拼接处改一行全站生效
2. **解题通关贴**：手把手解题的 `.wt-final` 结果条开头贴 `final.png`（大笑/通关）
3. **module 标题轮换贴**：每个章节小节标题（`.sec-id` 编号旁）按语义映射贴不同表情。用**运行时 IIFE 注入**（按 sec-id 文本查 MAP 表），不要手改 N 处 HTML
4. **首页 hero/关于作者区**：放主形象大贴（`mascot.png`，96px，透明免抠）
5. **模态框表情包格预览**：导流模态框的「表情包」cell 顶部加一组三连小贴预览

### 默认配置块（照抄改文案即可）

```
工作室名：捞鱼工作室（作者：捞鱼）
作者头像（固定 URL）：https://s41.ax1x.com/2025/12/05/pZmPZPH.png
作者一句话签名：「一个弱小但有梦想的开发者」
作者主页：https://lyzbcy.github.io/about/
表情包成品源：E:\星星布丁\微信表情包（周三涵/周五涵/捞鱼/星星布丁系列）
微信表情包下载二维码：自托管 img/sticker/sticker-qr.png。**获取方式（必须执行，不要留空格）**：从线上仓库直接下载 ——
  curl -s "https://lyzbcy.github.io/weshoto-study/img/sticker/sticker-qr.png" -o img/sticker/sticker-qr.png
  （文件 444×444 PNG，约 28KB。⚠️ 旧图床链接 s41.ax1x.com/.../pmtdMWV.png 已失效，不要用）
QQ群/赞赏二维码：源文件在 E:\短视频创作\项目\如果今年高考 你当初的院校选择值多少分\img\ui\（文件名 qq-group.jpg / reward-qr.jpg，部署到 Pages 必须复制进仓库 img/ 一起推）
```

> 详细规则（4 入口标准布局、网页表情种草语义映射模板、.nojekyll 红线）与 `lyzbcy-测试题制作` skill 保持一致，两个 skill 共用同一套推广体系。

---

## 页面结构

必须包含下面 11 个模块。
### 页面框架建议

lyzbcy 默认采用这个顺序：

1. 学习目标与阅读路径
2. 零基础背景包
3. 原文问题定位
4. 原文结构地图
5. 核心判断与依据
6. 关键概念拆解
7. 苏格拉底式阅读关卡
8. 闯关式任务包装
9. 误解与边界
10. 背景知识缺口
11. 复盘与学习报告

第一屏不要放抽象说明，不要放“学习契约”。读者一进来应该立刻知道：我要学会什么，为什么要先补哪些背景。


### 1. 学习目标与阅读路径

第一屏直接告诉读者：

- 这篇内容要学会什么
- 为什么需要先补背景
- 接下来会按什么顺序学习

不要把“学习契约”单独做成一个大模块。保真原则可以放在页脚或小提示里，不要占据第一屏。

### 2. 零基础背景包

列出 3 到 5 个可检查目标。

目标必须是动作，不是口号。

好目标：

- 能说出作者在回答什么问题
- 能区分 3 个核心判断和它们的原文依据
- 能解释 4 个关键概念之间的关系
- 能指出至少 2 个容易误解的地方
- 能提出 1 个后续追问

差目标：

- 理解全文
- 掌握思想
- 学会技术


### 2. 零基础背景包

在进入原文拆解前，先解释读懂本文必须知道的基础概念。

要求：

- 只补 3 到 5 个概念
- 每个概念都说明“为什么读本文需要它”
- 明确标注为“背景补充”
- 不能把背景补充写成作者原文观点

### 3. 原文问题定位

回答：

- 这篇文稿表面在讲什么？
- 它深层在回答什么问题？
- 作者为什么要写这篇？
- 读者如果只记一个问题，应该记哪个？

每个判断都要带原文依据。

### 4. 原文结构地图

先判断文章结构类型，再画地图。

可选结构：

- 时间线
- 机制流程
- 论证结构
- 主题簇
- 问题树
- 冲突结构

要求：

- 不强行改造成因果链
- 每个节点标注原文依据
- 节点之间的关系要写清楚：因果、并列、递进、对比、例证、转折

### 5. 核心判断与依据

提取 3 到 7 个核心判断。

每个判断必须包含：

- 核心判断
- 原文依据
- 这是事实 / 判断 / 推论 / 例子
- 为什么重要
- 可能的误读

### 6. 关键概念拆解

选择最多 6 个关键概念。

每个概念包含：

- 原文术语
- 作者在文中怎么使用它
- 人话解释
- 它和其他概念的关系
- 原文依据
- 不要误解成什么

注意：

概念解释不能只靠比喻。

先给定义，再给辅助理解。

### 7. 苏格拉底式阅读关卡

设计 5 到 8 个问题。

问题按难度递进：

1. 这段在回答什么？
2. 这句话属于事实、判断还是推论？
3. 这个例子支持哪个主张？
4. 这里少了哪个隐含前提？
5. 如果反过来看，作者可能忽略了什么？
6. 我如何不改变原意地复述？
7. 这个观点能迁移到哪里？

每题必须有：

- 问题
- 输入或选择区
- 参考答案
- 原文依据
- 反馈

### 8. 闯关式任务包装

把严肃阅读包装成任务，但任务必须保真。

推荐任务类型：

- 标注题：这句话是事实、判断还是推论？
- 匹配题：把判断和原文依据配对
- 补全题：补全概念关系
- 复述题：用自己的话重写，但不能改变原意
- 纠错题：指出一个错误理解哪里错了
- 迁移题：把观点迁移到新场景

禁止任务：

- 只考生僻词拼写
- 答案明显到不用思考
- 为了好玩而脱离原文
- 用比喻替代原文概念

### 9. 误解与边界

列出至少 3 个容易误解的地方。

每条包含：

- 可能误解
- 为什么容易误解
- 原文真正说了什么
- 原文没有说什么
- 如何避免这个误解

### 10. 背景知识缺口

告诉读者：

- 要完全理解这篇，还需要补哪些背景
- 哪些背景现在可以先不补
- 每个背景知识为什么重要
- 推荐下一步学习问题

不要把背景知识展开成另一门课。

### 11. 复盘与学习报告

最后生成学习报告。

包括：

- 我现在理解了什么
- 哪些判断有原文依据
- 哪些地方仍不确定
- 我容易误解什么
- 下一步该追问什么

如果使用 JS，可以生成可复制的学习报告。

---

## 手把手计算演示契约（课程/真题/计算题场景专用）

> ⚠️ **适用判断**：本节仅当材料是**课程章节、真题精讲、计算题（调度/银行家/页面置换/磁盘/地址变换/PV 同步等）**时使用。**纯文稿理解地图场景跳过本节**，用上面的 11 模块即可。

计算题要让学生"看懂每一步怎么算"，不能只给结论。os-study 项目验证过一套 walkthrough 样式契约，直接照抄即可保证风格一致。

### walkthrough 容器结构（5 件套）

每道计算大题用一个 `.walkthrough` 包起来，内部固定顺序：

```html
<div class="walkthrough">
  <div class="wt-tag">真题 / 提纲原题</div>           <!-- 红底黄字小标签，标来源 -->
  <div class="wt-title">题目标题</div>                <!-- 绿字加粗大标题 -->
  <div class="wt-given">题干原文…（mono 字体，纸色底）</div>
  <div class="wt-step">…逐步推演…</div>               <!-- 可多个，见下 -->
  <div class="wt-step">…</div>
  <div class="wt-final">…最终答案…</div>              <!-- 黄底绿字结果条 -->
</div>
```

### wt-step（每一步）的写法规范

每个 `.wt-step` 必含一个 `.step-no`（步骤小标题），然后是正文：

- **步骤编号格式**：`<div class="step-no">第 N 步 · 标题</div>`（中文间隔号 `·`）
- **列点**用全角 `•` 开头，`<br>` 换行
- **强调**用 `<strong>`，不斜体
- **大于号**写 `&gt;`，小于号直接用 `≤`（unicode）
- **多步骤之间**用 `<br><br>` 空一行

### 解题内容三件套（嵌在 wt-step 里）

| class | 用途 | 典型场景 |
|---|---|---|
| `.calc-table` | 解题表格（含 `.hit`绿底/.miss`红底 高亮列） | 调度时间表、页面置换对比、银行家 Work 累加 |
| `.formula` | 公式块（深绿底黄字 mono 居中） | 平均周转 = (T1+T2+...)/n |
| `.code-block` | 伪代码块（深底 mono，PV/算法题用，含 `.kw`关键字/`.cmt`注释高亮） | PV 操作伪代码、信号量声明 |

### wt-final 结果条规范

每题 walkthrough 末尾必收一个 `.wt-final`：
- 开头**固定贴通关章**：`<img class="wt-stamp" src="img/sticker/final.png" alt="">`（与表情包种草联动，见自推广体系）
- 内容套路：`答：` + 结论 + `<br>` + 核心要点 + 易错提醒
- 标注易错点用 `<span class="badge eg">易错</span>` 小标签

### 计算演示的完整示例骨架

```html
<div class="walkthrough">
  <div class="wt-tag">2025 真题</div>
  <div class="wt-title">银行家算法 · 请求判定</div>
  <div class="wt-given">系统有 A/B/C 三类资源…现在 P1 请求 (1,0,2)…</div>
  <div class="wt-step">
    <div class="step-no">第 1 步 · 请求判定三步审查</div>
    ① Request ≤ Need? …<br>
    ② Request ≤ Available? …<br>
    ③ 两关都过，进入试探分配。
  </div>
  <div class="wt-step">
    <div class="step-no">第 2 步 · 试探分配</div>
    <table class="calc-table">
      <tr><th>进程</th><th>Need</th><th>Allocation</th></tr>
      <tr><td>P1</td><td class="miss">不满足</td><td>2</td></tr>
    </table>
  </div>
  <div class="wt-final"><img class="wt-stamp" src="img/sticker/final.png" alt=""> 答：不能满足…<span class="badge eg">易错</span>必须做第三步安全性重判。</div>
</div>
```

---

## 真题蒸馏与课程扩展（课程/真题场景专用）

> ⚠️ 同上，纯文稿场景跳过。

### 核心方法论：真题 = 提纲改数据

os-study 项目最硬的经验：**老师的出题方式是"从复习提纲习题库挑一道母题，改个数字或条件直接考"**。这不是猜题，是 6 道真题里有 5 道能在提纲找到母题的铁证。所以最稳的策略不是背答案，是把每类母题的方法吃透——换数字也能做。

### 真题三向对照法（找缺口）

拿到真题后，做三向对照找出章节页缺口：
1. **真题考点**：每道真题考什么知识点
2. **提纲母题**：提纲里有没有同题型（通常数据略不同）
3. **现有章节页**：有没有演示这种考法

→ 三向对照后，补齐"真题考了但章节页没演示"的题型（手把手演示 + 检验选择题）。

### 真题标注规范

每道真题演示的出处行统一写：
```html
<p style="color:var(--brick);font-size:.85rem">📎 真题来源：YYYY 年期末 · 第 X 题（原题数据）｜题型：xxx ★必考</p>
```
- 提纲原题用 `📎 提纲出处：第 NNN 行`
- 难度标记：`★必考` / `★可能考` / `★第N章必考`

### 真题 → 手把手演示的转换模板

每道真题按固定结构转成可交互演示：
1. **题干**（wt-given，原题数据一字不改）
2. **分步推演**（多个 wt-step，每步算清，用 calc-table/formula/code-block）
3. **wt-final 答案条**（结论 + 核心 + 易错）
4. **末尾检验选择题**（task 契约，data-task 用 `qN`，测本题最易错的点）

### 课程页 vs 押题页的分工

如果做的是整套课程复习站（多个 HTML），按职能分页：
- **章节页**（每章一个 HTML）：练概念 + 交互选择题（data-task 用 `chN-mX`），module 8 放该章高频考法的手把手演示
- **押题页**（一个 HTML）：集中放真题/提纲大题的手把手解题（data-task 用 `qN`），按"题1、题2…"编号
- 两者用同一套 CSS 变量、walkthrough 样式、表情种草、promo 导流，保持视觉统一

---

## 互动规则

HTML 可以使用原生 JavaScript。

推荐功能：

- 进度条
- 掌握状态
- 错题回流
- 答案折叠
- 原文依据展开
- 学习报告生成

所有互动必须服务理解，不服务炫技。


### 交互实现稳定性

互动题必须真的可用。

生成 HTML 时优先使用稳定的 `data-*` 题目系统，而不是把复杂逻辑都写进 `onclick` 字符串。

每道题至少包含：

- `data-task`
- `data-answer`
- `data-goal`
- `.feedback` 反馈区域


交互反馈必须出现在按钮附近，并且默认占位可见。

反馈区不能使用 `display:none` 作为默认状态。默认状态应该显示“选择后点击检查，这里会显示反馈”。点击后只改变文案和正确/错误样式。

生成后必须检查：

- 所有按钮都能触发反馈
- 答对和答错都有不同反馈
- 错题能进入错题回流区
- 刷新页面后进度不会破坏页面
- JS 语法检查通过

### 答题反馈

反馈必须包含：

- 为什么这个答案合理
- 它对应哪条原文依据
- 如果答错，可能误解了什么
- 回到哪个模块复习

### 错题回流

答错后不要只显示“错误”。

必须告诉读者：

- 你错在事实、判断、推论，还是概念关系
- 应该回到哪个原文依据
- 哪个模块可以复习

---

## 互动引擎（固定脚本 · 跨模型保证）

> 这是为了保证在不同模型（Opus、Codex、其他）下互动题都能正常工作。
> 不同模型自己手写互动 JS 时，常出现“点了检查没反应”的 bug（绑定时机错、选择器错、脚本中途报错）。
> 解决办法：逻辑不交给模型写，统一用下面这段固定引擎。

### 必须遵守

1. 下面的 `<script>` 引擎必须**原样复制粘贴**到 HTML 最末尾（`</body>` 前），**不许改写其中逻辑**。
2. 模型只负责写题目 HTML，并把答案与反馈全部放进 `data-*` 属性里（不要再单独维护一个 JS 答案对象，避免和题目对不上）。
3. 引擎采用 **事件委托**（在 document 上监听），所以无论 DOM 何时生成、脚本放在哪里都能工作——这是跨模型稳定的关键，不要改成逐个元素提前绑定。
4. 生成后仍要抽取 script 跑 `node --check` 确认语法。

### 题目 HTML 契约（模型只填这些）

```html
<!-- 单选：data-answer 填正确项的 data-val -->
<div class="task" data-task="q1" data-answer="B"
     data-ok="为什么对 + 原文依据" data-no="答错可能误解了什么"
     data-src="原文：……" data-review="回到「第X模块」复习">
  <div class="q">题干</div>
  <div class="opts">
    <button class="opt" data-val="A">A. ……</button>
    <button class="opt" data-val="B">B. ……</button>
  </div>
  <button class="check">检查</button>
  <div class="feedback" aria-live="polite">选择后点击检查，这里会显示反馈。</div>
</div>

<!-- 多选：data-multi="true"，data-answer 用逗号，如 "A,C" -->
<!-- 匹配/排序：data-type="selects"，每个 <select class="match" data-correct="x"> -->
```

字段说明：`data-answer` 答案；`data-multi` 多选；`data-type="selects"` 下拉匹配；`data-ok/-no/-src/-review` 是反馈文案。引擎只读这些属性，不依赖任何外部 JS 对象。

> 默认输出中文，因此契约与引擎里的中文界面文案通常保持中文即可。只有用户明确要求输出为非中文时，才把少量中文界面文案（如“选择后点击检查”“请先选择一个选项再检查”“学习报告”等）翻译成对应语言；逻辑代码不要改。

### 固定引擎（原样粘贴）

```html
<script>
(function(){
  "use strict";
  function $all(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s));}
  function selectedVals(t){return $all('.opt.selected',t).map(function(o){return o.getAttribute('data-val');}).sort();}
  function setFb(t,state,html){var fb=t.querySelector('.feedback');if(!fb)return;fb.className='feedback'+(state?(' '+state):'');fb.innerHTML=html;}
  function updateBar(){
    var all=$all('.task'),done=$all('.task[data-answered="1"]');
    var fill=document.getElementById('barFill'),num=document.getElementById('barNum');
    if(fill)fill.style.width=all.length?(done.length/all.length*100)+'%':'0%';
    if(num)num.textContent=done.length+' / '+all.length;
  }
  function renderWrong(){
    var box=document.getElementById('wrongBox');if(!box)return;
    var wrong=$all('.task[data-answered="1"][data-correct="0"]');
    if(!wrong.length){box.innerHTML='<li style="color:#888">还没有错题。答错的题会自动收集到这里。</li>';return;}
    box.innerHTML='';
    wrong.forEach(function(t){var li=document.createElement('li');li.textContent='【'+(t.getAttribute('data-task')||'')+'】'+(t.getAttribute('data-review')||'回到对应模块复习');box.appendChild(li);});
  }
  function check(t){
    var type=t.getAttribute('data-type'),ok=false;
    if(type==='selects'){
      var sels=$all('select.match',t),allok=true,empty=false;
      sels.forEach(function(s){if(!s.value)empty=true;if(s.value!==s.getAttribute('data-correct'))allok=false;});
      if(empty){setFb(t,'no','请先把每一项都选好再检查。');return;}
      ok=allok;
    }else{
      var sel=selectedVals(t);
      if(!sel.length){setFb(t,'no','请先选择一个选项再检查。');return;}
      var ans=(t.getAttribute('data-answer')||'').split(',').map(function(x){return x.trim();}).sort();
      ok=(sel.join('|')===ans.join('|'));
    }
    var body=ok?(t.getAttribute('data-ok')||'回答正确。'):(t.getAttribute('data-no')||'再想想。');
    var src=t.getAttribute('data-src');
    setFb(t,ok?'ok':'no',(ok?'✅ ':'❌ ')+body+(src?('<span class="src">'+src+'</span>'):''));
    t.setAttribute('data-answered','1');t.setAttribute('data-correct',ok?'1':'0');
    updateBar();renderWrong();
  }
  function genReport(){
    var box=document.getElementById('report');if(!box)return;
    var all=$all('.task'),done=$all('.task[data-answered="1"]'),right=$all('.task[data-answered="1"][data-correct="1"]');
    var lines=['=== 学习报告 ===','完成题目：'+done.length+' / '+all.length,'答对：'+right.length+' 题',''];
    var wrong=$all('.task[data-answered="1"][data-correct="0"]');
    if(wrong.length){lines.push('我答错的题（建议复习）：');wrong.forEach(function(t){lines.push('- '+(t.getAttribute('data-task')||'')+'：'+(t.getAttribute('data-review')||''));});}
    else{lines.push('暂无错题。');}
    box.textContent=lines.join('\n');
  }
  document.addEventListener('click',function(e){
    var c=e.target.closest?e.target:null;
    var opt=c&&e.target.closest('.opt');
    if(opt){var t=opt.closest('.task');if(!t)return;
      if(t.getAttribute('data-multi')==='true'){opt.classList.toggle('selected');}
      else{$all('.opt',t).forEach(function(o){o.classList.remove('selected');});opt.classList.add('selected');}
      return;}
    var btn=c&&e.target.closest('.check');
    if(btn){var tk=btn.closest('.task');if(tk)check(tk);return;}
    if(e.target&&e.target.id==='genReport'){genReport();return;}
    if(e.target&&e.target.id==='copyReport'){var r=document.getElementById('report');if(r&&navigator.clipboard)navigator.clipboard.writeText(r.textContent);return;}
  });
  function init(){updateBar();renderWrong();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
</script>
```

### 为什么这样能跨模型稳定

- 逻辑固定、原样粘贴：模型不再自己发明绑定方式，消除“点了没反应”的根因。
- 事件委托：点击通过冒泡在 document 捕获，不依赖“脚本必须在元素生成后运行”，时机问题被绕过。
- 全部数据放在 `data-*`：答案和反馈与题目同处一地，模型不会把答案对象写得和题目对不上。

---

## 后台语音播报（可选功能 · 需用户开启）

> 让用户在忙碌时（通勤、做家务、健身、闭眼休息）也能通过「听」掌握内容。**整页一条连续语音 + 逐句字幕同步**——所有章节自动串成一条总时间轴，播完一章自动接下一章，适合长时间作业时连续聆听；播放器内嵌字幕区，实时高亮当前正在念的那句（当前句加粗深绿、前一句淡显作上下文）。播放器做成「圆润玩具风」迷你 MP3，**右侧常驻「书签脊」入口**（默认只露竖排图标，鼠标悬停时平滑拉出展开「后台语音」文字），点开即弹；时间轴可拖动跳转、显示时间。
>
> 本功能是**可选叠加层**：用户不开启时，skill 行为与本节无关，与改造前完全一致。

### 工作原理（务必先理解）

整个功能拆成两段，分别在不同时机执行：

| 阶段 | 在哪运行 | 做什么 |
|---|---|---|
| **生成时** | 调用方（你 / 终端运行 Python） | 把语音稿 `.json` 按章节批量合成成 `audio/*.mp3` **+ 整句字幕 `audio/*.json`** |
| **播放时** | 浏览器（用户双击 HTML） | 纯前端 JS 把各章节 mp3 **串成一条连续播放列表**播放，字幕引擎按播放进度同步高亮句子，不联网 |

- 合成用 `scripts/tts.py`，基于 `edge-tts`（微软 Azure Neural TTS，免 API Key，中文音质业界最好）。tts.py 在合成音频的同时，用 edge-tts 的 `SentenceBoundary` 事件（中文按句切分）生成整句字幕 JSON。
- ⚠️ **生成时依赖联网**（edge-tts 的固有特性）。生成完成后，播放是纯本地，断网也能听。
- ⚠️ 个人学习自用没问题；商用属灰色地带（微软服务条款）。

### 连续播放 + 字幕同步的设计（核心）

- **音频文件仍按章节切**（便于维护、改一章只重合成一章）；**字幕文件与 mp3 同名**（`ch1.mp3` ↔ `ch1.json`），播放器自动加载。
- **播放器把它们串成一条总时间轴**：总时长 = 各章时长之和。播完一章自动无缝接下一章，时间轴显示「当前累计秒数 / 总秒数」。
- **拖动时间轴可跳到任意位置**：松开拖动时，根据目标秒数算出落在第几章、章内第几秒，自动切到那一章并 seek。用户感知到的是「一整段连续语音」。
- **字幕同步（零侵入解耦）**：字幕引擎用 `MutationObserver` 监听播放器里 `.vp-cur`（时间显示，固定语音引擎每秒更新）和 `.vp-title`（曲名，切曲时变）这两个 DOM 文本节点——节点一变就解析出当前秒数、驱动字幕高亮。**完全不碰 audio 对象本身**（因为固定引擎用 `new Audio()` 不入 DOM，靠 `querySelectorAll('audio')` 找不到它，这是踩过的坑）。
- 适合健身、通勤、做家务等「手不能看屏、但耳朵空闲」的场景连续聆听。

### 第 1 步：询问用户是否开启（强制）

进入生成流程前，**必须先问一句**（不要默认开启）：

> 要不要为这份学习地图加上「后台语音播报」功能？
> - 开启后：每章会生成一段口语化播报音频，用户可点「后台语音」按钮边听边看。
> - 注意：生成音频需要联网，且会增加一些生成时间。

- 用户**同意** → 执行下面第 2~5 步，HTML 里挂上播放器与语音引擎。
- 用户**拒绝或没明确同意** → 完全跳过本节，按原流程生成纯文本 HTML。

### 第 2 步：撰写语音稿（最重要 · 与正文不是一回事）

⚠️ **语音稿 ≠ 把正文文字原样念一遍**。书面内容是给眼睛看的，语音稿是给耳朵听的，必须**口语化改写**。

#### 撰写契约

1. **逐章节一篇**：为每个章节/模块写一段独立的播报稿，对应一个 `data-audio` 音频。
2. **长度**：每段 150~400 字（合成后约 1~2.5 分钟），太长听不下来，太短没内容。
3. **口语化**：把书面表达翻译成「能说出口的话」。
4. **保留骨架**：核心判断、原文依据要保留，但**去掉**表格、代码、选择题、并列序号这些「只能看不能听」的形式。
5. **开头点题，结尾收束**：开头一句话说清「这章讲什么」，结尾一句「记住这一条就够了」。
6. **禁止**：念 URL、念代码、念选项 ABCD、念「如下图所示」。

#### 正反示例（务必对照）

❌ **书面原文（照念 = 灾难）**：
> 核心判断：LLM 的推理能力并非来自显式符号推理，而是模式匹配。
> 原文依据：「We argue that…」
> 类型：判断。易误读：把模式匹配等同于无推理。

✅ **口语化播报稿（改写后 = 能听懂）**：
> 这一章聊一个关键问题：大模型的推理能力到底是怎么来的？很多人以为模型会像人一样一步步推理，但其实作者认为，它的能力主要来自海量数据里学到的模式匹配，而不是真正的符号推理。作者的原文是这么说的，大模型是在做模式匹配。这里你只要记住一句话就够了：大模型看起来在推理，本质上是在做非常熟练的模式匹配。

### 第 3 步：写出语音稿 JSON

把所有章节的稿子写进一个 `audio-script.json`（与 HTML 同目录），格式固定：

```json
{
  "voice": "zh-CN-XiaoxiaoNeural",
  "items": [
    {"id": "ch1", "title": "第一章 核心判断", "text": "这一章聊一个关键问题……（口语化稿子）记住一句话就够了。"},
    {"id": "ch2", "title": "第二章 关键概念", "text": "第二章我们讲三个关键概念……"}
  ]
}
```

字段说明：
- `voice`：可选，覆盖默认音色（默认晓晓女声）。
- `items[].id`：音频文件名（生成的文件是 `audio/<id>.mp3`），同时也是 HTML 里 `<meta>` 列表的关联键，**必须和 HTML 里的 id 一一对应**。
- `items[].title`：章节标题，显示在播放器上（当前章名）。
- `items[].text`：口语化播报稿。
- **`items` 数组的顺序 = 播放顺序**：播放器按数组顺序把各章串成连续播放列表。一般就按章节的自然顺序（第 1 章 → 第 2 章 → …）排列。

常用音色：`zh-CN-XiaoxiaoNeural`（晓晓，女，默认）、`zh-CN-YunxiNeural`（云希，男）、`zh-CN-XiaoyiNeural`（晓伊，女，活泼）。完整列表用 `python scripts/tts.py --list-voices` 查看。

### 第 4 步：生成音频文件（调用方执行，不是浏览器）

写好 JSON 后，由调用方在终端跑这条命令（不是写进 HTML）：

```bash
python scripts/tts.py audio-script.json --out-dir audio/
```

产物结构（与 HTML 同目录）：
```
原文标题 - 理解地图.html
audio-script.json
audio/
  ├─ ch1.mp3        音频
  ├─ ch1.json       整句字幕（与 mp3 同名，播放器自动加载）
  ├─ ch2.mp3
  ├─ ch2.json
  └─ ...
```

> ⚠️ 必须先确认 `audio/` 下每个 `<id>.mp3` **和** `<id>.json` 都真实生成成功，再进入下一步写 HTML 引用。字幕 JSON 格式为 `[{start, end, text}, ...]`（秒）。

### 第 5 步：HTML 播放器契约（模型只填 meta + 按钮）

#### 5.1 章节播报列表（放在 `<body>` 开头，引擎靠它构造连续播放列表）

把每章的音频信息列成一个 `<script type="application/json" id="voicePlaylist">`。**模型只填这个数组**（顺序 = 播放顺序），引擎自动把各章串成一条总时间轴：

```html
<script type="application/json" id="voicePlaylist">
[
  {"id":"ch1","title":"第一章 核心判断","src":"audio/ch1.mp3"},
  {"id":"ch2","title":"第二章 关键概念","src":"audio/ch2.mp3"}
]
</script>
```

#### 5.2 章节标题旁的「听这章」按钮（可选，便于从某章开始听）

固定结构，模型只填 `data-voice-id`（对应上面数组里的 `id`），其余原样：

```html
<button class="voice-btn" data-voice-id="ch1">🎧 听这章</button>
```

放置位置：每个章节标题（h2/h3）旁边。点击 = 从该章开始连续播放（之后自动接下一章）。不挂也不影响功能——用户仍可点右侧书签脊从第 1 章开始听。

#### 5.3 右侧常驻「书签脊」入口（悬停拉出，避开「关于捞鱼」浮条）

放在 `</body>` 前，与播放器并列。这是主要入口（用户健身时点它开始整页聆听）。

⚠️ **不要用右下角圆形浮条**——会和页面已有的「关于捞鱼」浮条（`.float-btn` 也在右下）重叠。改用**右侧竖条书签脊**：固定在右边缘垂直居中，默认只露一个竖排 🎧 图标（窄条），鼠标悬停时平滑拉出展开「后台语音」文字。

结构（注意是两个子 span，不是单个 emoji 文本）：

```html
<button id="voiceFab" aria-label="打开后台语音"><span class="fab-icon">🎧</span><span class="fab-text">后台语音</span></button>
```

#### 5.4 圆润玩具风播放器样式 + 书签脊 + 字幕区（加进 `<style>`，用已有 CSS 变量）

```css
/* 章节标题旁的「听这章」小按钮 */
.voice-btn{
  display:inline-block; vertical-align:middle; margin-left:.6em;
  padding:.25em .8em; border:1px solid var(--forest); border-radius:var(--radius-pill);
  background:var(--cream); color:var(--forest); font:600 .8rem/1.2 var(--font-body);
  cursor:pointer; transition:background .15s;
}
.voice-btn:hover{ background:var(--sage); }
.voice-btn.active{ background:var(--forest); color:var(--cream); }

/* 右侧书签脊（默认收起只露图标，悬停拉出展开文字）。
   ⚠️ 不要用右下圆形浮条——会和「关于捞鱼」重叠。用右侧竖条书签脊。 */
#voiceFab{
  position:fixed; right:0; top:50%; transform:translateY(-50%); z-index:9998;
  display:flex; align-items:center; flex-direction:row;
  background:var(--forest); color:var(--cream); border:none; cursor:pointer;
  height:5em; padding:0 .55em;                  /* 高度固定，宽度随内容变 */
  border-radius:16px 0 0 16px;
  box-shadow:-4px 0 14px rgba(0,0,0,.18);
  font-family:var(--font-head); font-size:.85rem;
  overflow:hidden;
  transition:width .42s cubic-bezier(.4,0,.2,1), box-shadow .3s ease;  /* 丝滑缓动 */
  width:1.9em;                                   /* 收起态：只露图标宽度 */
}
/* 图标常驻竖排（写作竖向书签脊），不参与动画 */
#voiceFab .fab-icon{
  font-size:1.15rem; writing-mode:vertical-rl; text-orientation:upright;
  letter-spacing:.1em; white-space:nowrap; flex-shrink:0;
}
/* 文字横排，收起时被宽度裁掉、透明；展开时淡入 */
#voiceFab .fab-text{
  white-space:nowrap; opacity:0; margin-left:.6em;
  transition:opacity .28s ease .12s;            /* 延迟一点淡入，等宽度撑开 */
}
#voiceFab:hover{
  width:8.6em;                                   /* 拉开容下"🎧 后台语音" */
  box-shadow:-6px 0 22px rgba(0,0,0,.25);
}
#voiceFab:hover .fab-text{ opacity:1; }
#voiceFab.beat{ animation:voiceBeat 1.6s ease-in-out infinite; }   /* 播放中脉动光晕 */
@keyframes voiceBeat{ 0%,100%{box-shadow:-4px 0 14px rgba(0,0,0,.18)} 50%{box-shadow:-4px 0 20px rgba(181,72,42,.5)} }

/* 圆润玩具风播放器（固定居中靠下，不挡内容） */
#voicePlayer{
  position:fixed; left:50%; bottom:1rem; transform:translateX(-50%) translateY(140%);
  width:min(92vw,380px); padding:1rem 1.1rem 1.1rem; background:var(--cream);
  border:2px solid var(--forest); border-radius:26px;
  box-shadow:0 8px 28px rgba(0,0,0,.16); z-index:9999; transition:transform .28s ease;
  text-align:center; font-family:var(--font-body);
}
#voicePlayer.show{ transform:translateX(-50%) translateY(0); }
#voicePlayer .vp-head{ font-size:.75rem; color:var(--forest); opacity:.8; letter-spacing:.05em; }
#voicePlayer .vp-title{ font:700 1rem/1.35 var(--font-body); color:var(--ink);
  margin:.25rem 0 .7rem; padding:0 .2rem; word-break:break-word; }
/* 大圆形播放钮（玩具风核心） */
#voicePlayer .vp-play{
  width:3.6rem; height:3.6rem; border:none; border-radius:50%;
  background:var(--forest); color:var(--cream); font-size:1.3rem; cursor:pointer;
  margin:0 auto .7rem; display:flex; align-items:center; justify-content:center;
  box-shadow:0 3px 0 #142710; transition:transform .1s, box-shadow .1s;
}
#voicePlayer .vp-play:active{ transform:translateY(2px); box-shadow:0 1px 0 #142710; }
#voicePlayer .vp-prev,#voicePlayer .vp-next{
  width:2.3rem; height:2.3rem; border:1.5px solid var(--forest); border-radius:50%;
  background:var(--cream); color:var(--forest); font-size:.9rem; cursor:pointer;
}
#voicePlayer .vp-controls{ display:flex; align-items:center; justify-content:center; gap:1.2rem; margin-bottom:.7rem; }
/* 可拖动时间轴 + 时间显示 */
#voicePlayer .vp-seek{ width:100%; margin:.2rem 0; cursor:pointer; accent-color:var(--forest); }
#voicePlayer .vp-time{ display:flex; justify-content:space-between; font:600 .72rem/1 var(--font-mono); color:var(--ink); opacity:.75; }
#voicePlayer .vp-close{ position:absolute; top:.5rem; right:.6rem; width:1.5rem; height:1.5rem;
  border:none; background:transparent; color:var(--ink); font-size:1rem; cursor:pointer; opacity:.5; }

/* 字幕显示区（播放器内，时间轴下方）。逐句高亮当前正在念的句子 */
#voicePlayer .vp-sub{
  min-height:2.6em; max-height:3.9em; overflow:hidden;
  font:.85rem/1.5 var(--font-body); color:var(--ink); opacity:.55;
  margin:.2rem 0 .5rem; padding:0 .3rem;
  transition:opacity .2s; text-align:center;
}
#voicePlayer .vp-sub.active{ opacity:1; }
#voicePlayer .vp-sub .cur{ color:var(--forest); font-weight:600; }   /* 当前句加粗深绿 */
```

> **字幕区 `.vp-sub` 设计说明**：默认半透明显示上一句作上下文，命中当前句时切换 `.active` 全亮、当前句用 `.cur` 加粗深绿、前一句淡显（opacity:.45）。淡入淡出靠 `transition:opacity`，无突兀跳变。

#### 5.5 播放器容器（放在 `</body>` 前，含字幕区）

注意 `.vp-sub` 字幕区要放在 `.vp-time` **后面**（时间轴下方）：

```html
<div id="voicePlayer">
  <button class="vp-close" aria-label="关闭">✕</button>
  <div class="vp-head">🎧 后台语音 · 连续播放</div>
  <div class="vp-title">—</div>
  <div class="vp-controls">
    <button class="vp-prev" aria-label="上一章">⏮</button>
    <button class="vp-play" aria-label="播放/暂停">▶</button>
    <button class="vp-next" aria-label="下一章">⏭</button>
  </div>
  <input class="vp-seek" type="range" min="0" max="1000" value="0" aria-label="进度">
  <div class="vp-time"><span class="vp-cur">00:00</span><span class="vp-dur">00:00</span></div>
  <div class="vp-sub">点开播放后，这里会同步显示字幕</div>
</div>
```

### 第 6 步：固定语音引擎（原样粘贴，与互动引擎并列，互不干扰）

> 和「固定互动引擎」完全相同的架构思路：逻辑固定、事件委托、模型不写 JS。引擎读 `#voicePlaylist` JSON，自动把各章 mp3 串成一条连续总时间轴，支持拖动跳转、自动续播下一章。

下面的 `<script>` 必须放在 `</body>` 前，**原样粘贴，不要改写逻辑**：

```html
<script>
(function(){
  "use strict";
  if(window.__voiceEngine) return;        // 防重复
  window.__voiceEngine = true;

  /* ---- 读取播放列表（模型只填这个 JSON）---- */
  var listNode = document.getElementById('voicePlaylist');
  if(!listNode){ return; }                // 没有列表 → 本页没开语音，安静退出
  var TRACKS = [];
  try { TRACKS = JSON.parse(listNode.textContent.trim()); } catch(e){ return; }
  if(!TRACKS.length) return;

  var player = document.getElementById('voicePlayer');
  var fab = document.getElementById('voiceFab');
  var audio = new Audio(); audio.preload = 'metadata';
  var cur = 0;                 // 当前曲目下标
  var ranges = [];             // [{dur, start}] 各曲时长与累计起点，loaded 后填
  var total = 0;               // 总时长（秒）
  var seeking = false;         // 正在拖动时暂停 timeupdate 写 seek

  function $(s){ return player ? player.querySelector(s) : null; }
  function fmt(s){ s=Math.max(0,Math.floor(s||0)); var m=Math.floor(s/60), x=s%60;
    return (m<10?'0':'')+m+':'+(x<10?'0':'')+x; }

  /* ---- 总时长：等所有曲目的 duration 都拿到 ---- */
  var probe = TRACKS.map(function(){ return {dur:0}; });
  function tryFinalize(){
    if(probe.some(function(p){return !p.dur;})) return;   // 还有没拿到的
    ranges = []; total = 0;
    probe.forEach(function(p){ ranges.push({dur:p.dur, start:total}); total += p.dur; });
    var d = $('.vp-dur'); if(d) d.textContent = fmt(total);
    var sk = $('.vp-seek'); if(sk){ sk.max = Math.max(1000, Math.floor(total*10)); }
  }
  TRACKS.forEach(function(t, i){
    var a = new Audio(); a.preload = 'metadata'; a.src = t.src;
    a.addEventListener('loadedmetadata', function(){
      probe[i].dur = a.duration || 0; tryFinalize();
    });
    a.addEventListener('error', function(){ probe[i].dur = 0; tryFinalize(); });
  });

  /* ---- 播放控制 ---- */
  function load(i){
    cur = i; audio.src = TRACKS[i].src;
    var ti = $('.vp-title'); if(ti) ti.textContent = TRACKS[i].title || ('第 '+(i+1)+' 段');
    markBtn(i);
  }
  function play(){ audio.play().then(function(){ show(); setPlayIcon(true); if(fab) fab.classList.add('beat'); }).catch(function(){}); }
  function pause(){ audio.pause(); setPlayIcon(false); if(fab) fab.classList.remove('beat'); }
  function toggle(){ audio.paused ? play() : pause(); }
  function next(){ if(cur < TRACKS.length-1){ load(cur+1); play(); } else { pause(); } }   // 末曲结束停在末尾
  function prev(){ /* 累计时间 > 当前曲起点+3s 时退到本曲起点，否则上一曲 */
    var abs = absTime();
    if(cur > 0 && abs - ranges[cur].start < 3){ load(cur-1); play(); }
    else { audio.currentTime = 0; }
  }
  function absTime(){ return ranges[cur] ? ranges[cur].start + (audio.currentTime||0) : (audio.currentTime||0); }
  function setPlayIcon(on){ var b=$('.vp-play'); if(b) b.textContent = on ? '⏸' : '▶'; }
  function show(){ if(player) player.classList.add('show'); }
  function hide(){ if(player) player.classList.remove('show'); }
  function markBtn(i){
    document.querySelectorAll('.voice-btn[data-voice-id]').forEach(function(b){
      b.classList.toggle('active', b.getAttribute('data-voice-id') === TRACKS[i].id);
    });
  }

  /* ---- 同步 UI ---- */
  audio.addEventListener('timeupdate', function(){
    if(seeking) return;
    if(!ranges[cur]) return;
    var abs = absTime(); var sk = $('.vp-seek'); var c = $('.vp-cur');
    if(sk && total) sk.value = Math.round(abs / total * (sk.max||1000));
    if(c) c.textContent = fmt(abs);
  });
  audio.addEventListener('ended', function(){ if(cur < TRACKS.length-1){ load(cur+1); play(); }
    else { setPlayIcon(false); if(fab) fab.classList.remove('beat'); } });

  /* ---- 拖动时间轴：把目标累计秒数还原成「第几曲 + 曲内秒数」---- */
  function seekToFraction(frac){
    if(!total) return;
    var target = Math.max(0, Math.min(total, frac * total));
    var i = 0; while(i < ranges.length-1 && ranges[i].start + ranges[i].dur < target){ i++; }
    if(i !== cur){ cur = i; audio.src = TRACKS[i].src;
      var ti=$('.vp-title'); if(ti) ti.textContent = TRACKS[i].title||('第 '+(i+1)+' 段'); markBtn(i); }
    audio.currentTime = target - ranges[i].start;
    var c=$('.vp-cur'); if(c) c.textContent = fmt(target);
  }

  /* ---- 事件委托 ---- */
  document.addEventListener('click', function(e){
    var t = e.target;
    /* 「听这章」按钮：从指定曲开始连续播放 */
    var vb = t.closest ? t.closest('.voice-btn[data-voice-id]') : null;
    if(vb){
      var id = vb.getAttribute('data-voice-id'), idx = -1;
      TRACKS.forEach(function(tr, k){ if(tr.id === id) idx = k; });
      if(idx >= 0){ load(idx); play(); }
      return;
    }
    /* 右侧书签脊：打开播放器；未播放则从第 1 曲开始 */
    if(t.id === 'voiceFab'){ show(); if(audio.paused && !audio.src){ load(0); } if(audio.paused){ play(); } return; }
    if(!player || !player.contains(t)) return;
    if(t.classList.contains('vp-play')){ toggle(); return; }
    if(t.classList.contains('vp-prev')){ prev(); return; }
    if(t.classList.contains('vp-next')){ next(); return; }
    if(t.classList.contains('vp-close')){ pause(); hide(); return; }
  });
  /* 时间轴拖动 */
  var sk = $('.vp-seek');
  if(sk){
    sk.addEventListener('input', function(){ seeking = true;
      if(total){ var c=$('.vp-cur'); if(c) c.textContent = fmt((sk.value/(sk.max||1000))*total); } });
    sk.addEventListener('change', function(){ seekToFraction(sk.value/(sk.max||1000)); seeking = false; });
  }
})();
</script>
```

#### 为什么这样设计

- **连续播放列表**：引擎读 `#voicePlaylist` JSON，预探测各曲时长，拼出总时间轴；播完一曲自动无缝接下一曲，用户感知是「一整段语音」，适合健身/通勤连续聆听。
- **可拖动跳转**：拖动时间轴 → 把「累计秒数」还原为「第几曲 + 曲内秒数」→ 自动切曲并 seek，跨曲跳转也对。
- **圆润玩具风 + 右侧书签脊**：大圆形播放钮（带凸起阴影、按下回弹）、明亮玩具色、**右侧常驻书签脊入口**（悬停拉出、播放中脉动光晕），符合「玩具 mp3」观感；用右侧竖条而非右下圆形，是为了避开「关于捞鱼」浮条。
- **后台播放**：独立 `Audio` 对象 + 自绘播放器，不弹原生全屏播放器，边听边能滚动浏览页面。
- **事件委托 + 与互动引擎隔离**：和互动引擎同样的稳定性保障；三段 IIFE（互动 / 语音 / 字幕）互不引用、不污染全局，可同时存在。

### 第 7 步：字幕同步引擎（原样粘贴，与语音引擎并列）

> 字幕引擎**不碰 audio 对象**（固定语音引擎用 `new Audio()` 不入 DOM，靠 `querySelectorAll('audio')` 找不到——这是踩过的坑）。改用 `MutationObserver` 监听播放器里的 `.vp-cur`（时间显示，每秒变）和 `.vp-title`（曲名，切曲时变），节点一变就解析出当前秒数、驱动字幕。这是零侵入解耦的关键设计。

下面的 `<script>` 放在 `</body>` 前、固定语音引擎之后，**原样粘贴，不要改写逻辑**：

```html
<script>
(function(){
  "use strict";
  if(window.__subEngine) return;
  window.__subEngine = true;

  var listNode = document.getElementById("voicePlaylist");
  if(!listNode) return;
  var subBox = document.querySelector("#voicePlayer .vp-sub");
  var curEl = document.querySelector("#voicePlayer .vp-cur");
  var titleEl = document.querySelector("#voicePlayer .vp-title");
  if(!subBox) return;

  var subs = [];
  var subCache = {};
  var curSrc = "";

  function esc(s){ var d=document.createElement("div"); d.textContent=s; return d.innerHTML; }

  /* mp3 路径 → json 字幕路径（同目录同名） */
  function mp3ToJson(src){
    var m = src.replace(/^.*?([a-zA-Z0-9_\/.\-]+\.mp3)(?:\?.*)?$/i, "$1");
    return m.replace(/\.mp3$/i, ".json");
  }

  function loadSubFor(src){
    if(!src || src === curSrc) return;
    curSrc = src;
    var jsonUrl = mp3ToJson(src);
    if(subCache[jsonUrl]){ subs = subCache[jsonUrl]; return; }
    fetch(jsonUrl).then(function(r){
      if(!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function(arr){
      subCache[jsonUrl] = Array.isArray(arr) ? arr : [];
      subs = subCache[jsonUrl];
    }).catch(function(){ subs = []; });
  }

  /* "mm:ss" → 秒 */
  function parseTime(text){
    var p = String(text).trim().split(":");
    if(p.length === 2){
      var m = parseInt(p[0], 10) || 0;
      var s = parseInt(p[1], 10) || 0;
      return m * 60 + s;
    }
    return parseFloat(text) || 0;
  }

  function renderSub(t){
    if(!subs.length) return;
    var hit = null, idx = -1;
    for(var i = 0; i < subs.length; i++){
      if(t >= subs[i].start && t < subs[i].end){ hit = subs[i]; idx = i; break; }
    }
    if(!hit){
      var prev = null;
      for(var j = 0; j < subs.length; j++){
        if(subs[j].start <= t) prev = subs[j]; else break;
      }
      subBox.classList.remove("active");
      subBox.innerHTML = prev ? esc(prev.text) : "";
      return;
    }
    subBox.classList.add("active");
    var prevHtml = idx > 0
      ? '<span style="opacity:.45">' + esc(subs[idx - 1].text) + "</span> "
      : "";
    subBox.innerHTML = prevHtml + '<span class="cur">' + esc(hit.text) + "</span>";
  }

  function tick(){
    if(!curEl) return;
    var sec = parseTime(curEl.textContent);
    renderSub(sec);
  }

  /* 用曲名反查 src（切曲时 title 变，触发加载对应字幕） */
  function onTitleChange(){
    var TRACKS = [];
    try { TRACKS = JSON.parse(listNode.textContent.trim()); } catch(e){ return; }
    var title = titleEl ? titleEl.textContent.trim() : "";
    for(var i = 0; i < TRACKS.length; i++){
      if(TRACKS[i].title === title){ loadSubFor(TRACKS[i].src); return; }
    }
  }

  /* MutationObserver 监听播放器内部文本节点变化 */
  if(window.MutationObserver){
    var obs = new MutationObserver(function(){ tick(); onTitleChange(); });
    if(curEl) obs.observe(curEl, { childList:true, characterData:true, subtree:true });
    if(titleEl) obs.observe(titleEl, { childList:true, characterData:true, subtree:true });
  } else {
    setInterval(function(){ tick(); onTitleChange(); }, 300);   /* 降级轮询 */
  }
  setTimeout(tick, 500);   /* 启动时也 tick 一次 */
})();
</script>
```

#### 字幕引擎为什么这样设计

- **MutationObserver 而非找 audio 对象**：固定语音引擎的 `new Audio()` 不插入 DOM，字幕引擎靠 `querySelectorAll('audio')` 永远找不到它（这是踩过的真坑——字幕卡在初始文案不动）。改监听播放器里固定语音引擎**必定会更新**的 DOM 文本节点（`.vp-cur` 每秒变、`.vp-title` 切曲时变），彻底绕开 audio 对象。
- **按曲名反查 src**：切曲时固定引擎把曲目标题写进 `.vp-title`，字幕引擎监听到 title 变化，用标题在 `#voicePlaylist` 里反查 src，加载对应的 `<id>.json` 字幕。
- **字幕缓存**：`subCache` 按 jsonUrl 缓存，反复切回同一曲不重复 fetch。
- **三段 IIFE 完全隔离**：互动引擎 / 语音引擎 / 字幕引擎各自独立，互不引用、互不污染全局，可同时存在。

---

## 语言规则

### 基本要求

- 短句
- 主语明确
- 不堆抽象名词
- 不把复杂争议讲成单一结论
- 不用没有解释的英文缩写
- 不用“显然”“本质上”来跳过论证

### 逻辑检查

重点检查这些词：

- 但
- 因为
- 所以
- 而
- 这说明
- 这意味着
- 本质上

如果出现因果或转折，必须确认：

1. 前后是否讲同一个问题
2. 中间推理是否补齐
3. 这是不是原文说的，还是你的解释

### 保真检查

每个核心判断都问：

- 原文依据在哪里？
- 这是作者明确说的，还是我推出来的？
- 有没有删掉关键限制条件？
- 有没有为了比喻改变意思？
- 有没有把并列关系写成因果关系？

### 术语翻译规则（跨语言处理）

不要逐字直译技术术语。判断标准只有一句话：**目标语言的从业者实际上管它叫什么**，而不是“这个词字面怎么译”。

字面直译会产生不知所云的伪翻译，例如把 headless Chrome 译成「无头 Chrome 渲染」、把 authoring surface 译成「编写表面」。这是必须避免的失败。

每个术语先过 4 个测试：

1. 回译测试：把你的译名给懂行的人，他能反推回原词吗？「上下文窗口」能想到 context window（通过）；「无头 Chrome」没人反推得出 headless（不通过）。
2. 社区检验：这个说法在真实的目标语言技术内容里有人用吗？临时造出来、零命中的词不要用。
3. 独立可懂测试：译名单独拿出来，母语者能猜到意思吗？「神经网络」能，「编写表面」不能。
4. 失真测试：直译有没有丢限定词或改变原意？

然后分三档处理：

- A 有通用译法：用目标语言，首次出现可附原文。例（中文）：强化学习(reinforcement learning)、上下文窗口(context window)、预训练、权重、扩散模型。
- B 圈内本就说原词：保留原词 + 一句解释。例：headless Chrome、prompt、token、agent、DOM、GSAP、vibe coding。
- C 无公认译法 / 直译荒谬：保留原词 + 一句人话解释，绝不硬翻。例：authoring surface、source of truth、round-trip、BeginFrame。

默认原则：拿不准就归到 B 或 C，宁可保留原词，也不要造一个生硬直译。

格式建议：

```text
有通用译法：译名（原文）
保留原词：原文 —— 一句解释（这是什么、读本文为什么需要）
```

---

## 视觉规则

风格：研究报告 × 学习 App。

使用下面 CSS 变量：

```css
:root{
  --cream:#FAF6EB;
  --paper:#F3EDDD;
  --forest:#1E3A24;
  --sky:#BCD8EE;
  --sage:#AFCDA8;
  --ink:#1A2018;
  --marker:#F5E08A;
  --brick:#B5482A;
  --correct:#2F7D46;
  --wrong:#B5482A;
  --font-display:"Archivo Black","Noto Sans SC","PingFang SC",sans-serif;
  --font-head:"Poppins","Noto Sans SC","PingFang SC",sans-serif;
  --font-body:-apple-system,"PingFang SC","Noto Sans SC",sans-serif;
  --font-mono:"Roboto Mono","JetBrains Mono",monospace;
  --radius-pill:999px;
  --radius-card:14px;
}
```

要求：

- 原文依据要有明显样式
- 作者观点和辅助解释要视觉区分
- 互动任务要像关卡，但不要喧宾夺主
- 每张卡片文字不要太满
- 移动端单列
- 不使用阴影、渐变、毛玻璃

### 版式与布局（强制）

整页采用「左侧固定侧边栏 + 右侧单列主区」的两栏骨架。除侧边栏外，主区内所有内容一律纵向堆叠。

1. **左侧固定侧边栏**（桌面端 `position: sticky` 或 `fixed`，随页面常驻）：
   - 顶部：主题标题
   - 任务进度条（如 `0/8`）
   - 完整导航栏（01~11 各模块的锚点链接，点击跳转）
   - 侧边栏宽度建议 240~300px，深色背景与主区区分

2. **右侧主区：严格单列、全部纵向**。
   - 学习目标（目标 1/2/3…）**纵向逐条堆叠**，禁止做成横向网格或一排多卡。
   - 背景包、核心判断、概念卡、关卡题、误解卡等，**全部一张一张竖直往下排**。
   - 禁止任何 `display:flex; flex-direction:row` 或多列 `grid` 把卡片横向并排。卡片之间只有上下关系，没有左右并排。

3. **唯一允许的并排**：只有「左侧边栏 vs 右侧主区」这一处是左右布局；主区内部不得再出现左右并排。

4. **移动端**：侧边栏收起或移到顶部，主区依旧单列纵向。

> 反例（禁止）：把目标 1~5 做成一行五个方块、把背景概念做成 2~3 列网格。
> 正例（要求）：目标 1 在上、目标 2 在下……依次竖排；每个背景概念独占一行宽度。

---

## 源材料处理（PPT/逐字稿/OCR 提取）

> 真实课程材料常以 PDF（PPT 导出）、语音转写逐字稿、OCR 图片等形式提供，需要先提取成可用文本。

### PDF（PPT 导出）提取：用 pymupdf，不要用 pdftotext

中文 PPT 导出的 PDF 常带 `Adobe-GB1` / `SimSun` 字体，`pdftotext`（poppler）会因 `Couldn't find 'GBK-EUC-H' CMap` 报一堆 `Syntax Error` 且输出乱码。**改用 pymupdf（fitz）**，对中文嵌入式字体提取稳定：

```python
import pymupdf
doc = pymupdf.open('xxx.pdf')
out = []
for i in range(doc.page_count):
    out.append(f'=== 第 {i+1} 页 ===')
    out.append(doc[i].get_text().strip())
open('ppt.txt','w',encoding='utf-8').write('\n'.join(out))
```

> 经验：52 页 PPT 用 pymupdf 秒出、零乱码；同一文件 pdftotext 全是 `Syntax Error` 且输出不可用。优先 pymupdf。

### 逐字稿（语音转写）清洗要点

语音转写的逐字稿有三个固定问题，拆解前必须处理：
1. **同音错字**：「微盛」→「威盛/威胜/微胜」、「企微」→「前微信/写微信/起微」、「SCRM」→「SCM/SF」、「AI」→「AR」。结合 PPT 和上下文批量纠正。
2. **口语冗余**：「呃」「然后呢」「就是」「对吧」「其实」密集出现，拆解时剔除。
3. **无标点长句**：整段没有句号，需要按语义断句。

**关键纪律（用户明确要求）**：学习地图中**不要出现「这是逐字稿」的字样**，当成手工记录处理——因为学习地图会被同事看到，被发现录音不好。逐字稿只作为内部理解材料，输出时一律按「培训发言稿/分享」措辞。

### PPT + 逐字稿 + 重点笔记三者交叉

最稳的拆解方式是三源交叉：PPT 给结构和硬数字（页码可定位），逐字稿给案例和口语化解释（补 PPT 没展开的「为什么」），用户的重点笔记给考试方向（哪些必考）。三者冲突时以 PPT 原文为准（最权威），逐字稿辅助理解，重点笔记标注考试重点。

---

## 目录页新增章节（AES 加密目录页维护）

> 目录页（lyzbcy.github.io 上的 index.html）是 AES-256-GCM 整页加密的，新增章节卡片和搜索数据都加密在同一个 payload 里。新增一章的完整流程：

### 解密 → 改 → 重新加密 三步走

1. **解密**：用 Node.js `crypto` 模块，密码 = 泽恩，PBKDF2(100000, SHA-256) 派生 AES-256-GCM key，payload 结构 = `salt(16) + iv(12) + tag(16) + ciphertext`，base64 编码。解密后得到明文 HTML 存临时文件。

```javascript
const crypto = require('crypto');
const data = Buffer.from(cipherB64, 'base64');
const salt = data.subarray(0,16), iv = data.subarray(16,28), tag = data.subarray(28,44), ct = data.subarray(44);
const key = crypto.pbkdf2Sync(Buffer.from('泽恩','utf8'), salt, 100000, 32, 'sha256');
const d = crypto.createDecipheriv('aes-256-gcm', key, iv); d.setAuthTag(tag);
let pt = Buffer.concat([d.update(ct), d.final()]);  // 明文
```

2. **改明文**：
   - 加章节卡片（`<a class="chapter-card" href="新部署URL">`），位置按课程顺序插
   - 跑 `node build-search.cjs` 重新生成 SEARCH_INDEX（CHAPTERS 配置清单先加新章），用括号深度计数法替换明文里的旧 `var SEARCH_INDEX = [...]`（非贪婪正则 `.*?` 在多行 JSON 上不可靠）
   - **不要手改统计数字**（「X 章」），它们由 JS 从 SEARCH_INDEX 动态算

3. **重新加密**：生成新 salt + iv，同样结构打包 base64，替换 index.html 里的 `CIPHER_B64`，并把 `PAGE_V` 数字 +1。

```javascript
const salt = crypto.randomBytes(16), iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(Buffer.from('泽恩','utf8'), salt, 100000, 32, 'sha256');
const c = crypto.createCipheriv('aes-256-gcm', key, iv);
let ct = Buffer.concat([c.update(Buffer.from(plaintext,'utf8')), c.final()]);
const tag = c.getAuthTag();
const b64 = Buffer.concat([salt, iv, tag, ct]).toString('base64');
```

4. **bump version.json**：`v` 值必须 = `PAGE_V`（否则缓存检测逻辑会让老用户无限刷新）。push 前用 Node 解密验证一次 round-trip（密码能解开、新卡片在、新章节在 SEARCH_INDEX、div 标签平衡）。

### 安全红线

- **解密后的明文（`_plaintext.html` 等）绝不能提交到 git**。仓库根必须有 `.gitignore` 排除 `_plaintext.html` / `_search_index.js` / `_final_verify.mjs` 等临时文件。
- 部署后立即删除本地临时明文文件。

---

## 静态网页自动更新标准（缓存自动刷新机制）

> 静态网页（GitHub Pages / COS / 任何 CDN）的最大痛点：**改了内容、push 了，用户打开还是旧的**——因为 CDN 和浏览器都缓存了 HTML。本节是经过多轮迭代验证的「用户无感自动刷新」标准方案，**所有静态页面部署都必须按此配置**。

### 为什么需要这套机制（踩过的坑）

| 方案 | 为什么不行 |
|---|---|
| 只加 `<meta http-equiv="Cache-Control" content="no-cache,...">` | meta 缓存头**很多 CDN 直接忽略**（GitHub Pages CDN 用 `max-age=600` 自己的规则，不读 meta） |
| 让用户手动 Ctrl+F5 | 用户根本不知道你更新了，不会主动刷新 |
| sessionStorage 标记「正在刷新」防死循环 | **第一次访问 sessionStorage 是空的**，首次打开检测失效，用户看到的还是旧缓存 |
| 只靠 version.json 时间戳 fetch 对比 | 没有「页面内联版本号」做基准，旧缓存 HTML 里的比对逻辑本身也是旧的 |

**正确方案的核心思想**：页面 HTML 里写死一个**内联版本号 `PAGE_V`**（随 HTML 一起被 CDN 缓存），同时用一个**独立 `version.json` 文件**（用 `cache:'no-store'` 强制不缓存）存最新版本号。两者不一致 = 当前 HTML 是旧缓存 = 自动 reload 拿最新的。reload 后拿到的新 HTML 里 `PAGE_V` 更新了，两者一致，停止刷新。

### 三件套（缺一不可）

#### 1. 页面内联版本号 `PAGE_V`（随 HTML 缓存的「旧版本指纹」）

在页面 `<head>` 或 `<body>` 开头的 `<script>` 里，写死一个数字常量。**每次更新页面内容，这个数字必须 +1**：

```javascript
var PAGE_V = 9;   // ← 每次改页面内容，手动 +1（和 version.json 的 v 保持一致）
```

这个常量是「这版 HTML 自带的版本号」。当 CDN 缓存了一份旧 HTML（比如 PAGE_V=8），用户打开时页面里跑的是旧的 `PAGE_V=8`。

#### 2. 独立的 `version.json`（永远拿最新的「真相版本号」）

仓库根放一个 `version.json`，**只存版本号和日期**：

```json
{
  "v": 9,
  "updated": "2026-07-08"
}
```

关键：fetch 它时用 `cache:'no-store'` + URL 加时间戳，**强制绕过所有 CDN 缓存**，每次都拿服务器最新版。

#### 3. 自动刷新 IIFE（对比两者，不一致就 reload）

页面 `<script>` 里放这段固定逻辑（原样粘贴，只改 `PAGE_V` 初始值）：

```html
<script>
var PAGE_V = 9;
fetch('version.json?t=' + Date.now(), {cache:'no-store'})
  .then(function(r){ return r.json(); })
  .then(function(d){
    if(PAGE_V !== d.v){
      // 当前 HTML 是旧缓存 → 提示用户 + 自动刷新
      var el = document.getElementById('g-load');
      if(el){ el.textContent = '内容已更新，正在刷新…'; el.style.display = 'block'; }
      setTimeout(function(){ location.reload(true); }, 800);
    }
  })
  .catch(function(){});   // version.json 拿不到（网络问题）静默失败，不阻塞页面
</script>
```

#### 工作原理图解

```
用户打开页面（CDN 返回缓存的旧 HTML，PAGE_V=8）
       │
       ▼
页面执行 fetch('version.json?t=时间戳', {cache:'no-store'})  ← 强制拿服务器最新
       │
       ▼
version.json 返回 {"v": 9}   ← 服务器上是 9（你刚 push 的）
       │
       ▼
比较：PAGE_V(8) !== d.v(9)  → 不一致！当前是旧缓存
       │
       ▼
显示「内容已更新，正在刷新…」→ location.reload(true)
       │
       ▼
reload 后 CDN 可能还是返回旧 HTML？不会——因为 GitHub Pages 的 reload(true)
会带 no-cache 请求头，拿到最新的 PAGE_V=9
       │
       ▼
PAGE_V(9) === d.v(9) → 一致，停止刷新，用户看到最新内容 ✓
```

### 更新页面的标准流程（每次改内容必走）

1. **改完页面内容**（HTML/章节/卡片/搜索数据等）
2. **`PAGE_V` +1**：把页面里的 `var PAGE_V = N;` 改成 `N+1`
3. **`version.json` 的 `v` 同步 +1**：`{"v": N+1, "updated": "今天日期"}`
4. **验证两者相等**：`PAGE_V` 必须严格等于 `version.json` 的 `v`，否则用户会无限刷新
5. **push / 部署**

> ⚠️ **最容易忘的就是第 2、3 步**。只改了内容忘了 bump 版本号 = 用户看到的还是旧的。所以这条已写进自检清单。

### 为什么这样设计能解决所有坑

| 坑 | 这个方案怎么解 |
|---|---|
| CDN 缓存 HTML（max-age=600） | `PAGE_V` 内联在 HTML 里，旧缓存的 `PAGE_V` 是旧数字，和最新 `version.json` 对比必然不一致 |
| 第一次访问（sessionStorage 空） | 不依赖 sessionStorage，靠的是「内联旧版本 vs fetch 新版本」对比，首次访问照样生效 |
| version.json 也被缓存 | `cache:'no-store'` + `?t=Date.now()` 时间戳，强制每次拿服务器最新 |
| reload 后还是旧 HTML | GitHub Pages 对 `reload(true)` 会发 no-cache 请求拿最新；即使个别 CDN 还是旧的，`PAGE_V` 一致就不会再 reload（不死循环） |
| 用户正在答题，刷新丢失进度 | 加 800ms 延迟 + 提示文案，给用户一个心理准备；如果是敏感场景可加 `sessionStorage` 标记「刚刷新过」防立即二次刷新 |

### 额外加固（可选但推荐）

#### meta 缓存头（双保险，虽然 CDN 可能忽略）

```html
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
```

#### 防刷新死循环的 sessionStorage 标记（reload 前设、reload 后清）

如果担心 reload 后 CDN 仍返回旧 HTML 导致反复刷新，可在 reload 前设标记：

```javascript
if(PAGE_V !== d.v){
  // 防死循环：如果刚刷新过（3秒内），不再刷新，让用户手动处理
  var last = 0;
  try{ last = parseInt(sessionStorage.getItem('weshoto_refreshed_at') || '0'); }catch(e){}
  if(Date.now() - last < 3000){
    // 3秒内又检测到不一致 = CDN 可能还没生效，不刷新，静默等下次访问
    return;
  }
  try{ sessionStorage.setItem('weshoto_refreshed_at', String(Date.now())); }catch(e){}
  setTimeout(function(){ location.reload(true); }, 800);
}
```

> 注意：sessionStorage 标记只能作为「防死循环兜底」，**不能作为主检测机制**——因为第一次访问 sessionStorage 是空的，首次检测会失效。主检测必须是「PAGE_V 内联 vs version.json fetch」对比。

### 适用范围

这套机制适用于：
- **GitHub Pages** 上的任何静态页（目录页、章节页、活动页）
- **COS / S3 + CDN** 部署的静态页
- **help.wshoto.com** 部署的章节页（如果需要自动更新；当前章节页改动频率低，可选不加）

**加密目录页**（AES）尤其需要——因为加密 payload 整个在 `CIPHER_B64` 里，改内容 = 重新加密 = 必须 bump 版本让用户刷新拿新密文，否则用户拿旧密文 + 旧密钥解出来的还是旧内容。

---

## 生成流程

0. **（语音）询问用户**：要不要为本次学习地图开启「后台语音播报」功能？（详见「后台语音播报」章节。用户未明确同意则全程跳过语音相关步骤）
1. 读完原文
2. 提取作者在回答的问题
3. 判断原文结构类型
4. 提取核心判断
5. 给每个判断找原文依据
6. 区分事实、判断、推论、例子
7. 拆关键概念和概念关系
8. 设计苏格拉底问题
9. 设计闯关式任务
10. 写误解与边界
11. 写背景知识缺口
12. 生成 HTML（左侧边栏 + 右侧单列，粘贴固定互动引擎）
13. 检查保真、语言、互动和布局
14. **（语音·仅用户同意时）撰写口语化语音稿 → 写出 `audio-script.json` → 由调用方跑 `python scripts/tts.py audio-script.json --out-dir audio/` 同时生成 `audio/*.mp3` **和** `audio/*.json`（整句字幕）→ HTML 里放 `#voicePlaylist` 播放列表 + 右侧书签脊入口 `#voiceFab`（**不要用右下圆形浮条，会和「关于捞鱼」重叠**）+ 圆润玩具风播放器 `#voicePlayer`（含 `.vp-sub` 字幕区）+ 粘贴固定语音引擎 + 粘贴字幕同步引擎**

---

## 最终自检清单

- [ ] 是否有 3 到 5 个可检查学习目标？
- [ ] 是否有零基础背景包？
- [ ] 背景补充是否和原文判断分开？
- [ ] 是否判断了原文结构类型？
- [ ] 是否每个核心判断都有原文依据？
- [ ] 是否区分事实、判断、推论、例子？
- [ ] 是否没有强行套因果链？
- [ ] 是否没有用比喻替代定义？
- [ ] 是否有苏格拉底式问题？
- [ ] 是否有闯关式任务包装？
- [ ] 是否有误解与边界？
- [ ] 是否有背景知识缺口？
- [ ] 是否有复盘与学习报告？
- [ ] 是否检查了“但/因为/所以/这意味着”等逻辑连接？
- [ ] 是否避免信息失真？
- [ ] 所有互动题是否真的可点击、可反馈、可记录？
- [ ] 首屏是否删除了方法论说明和免责声明？
- [ ] **（统计数字）** 页面里"X 章/Y 题/Z 模块"这类统计数字是否从数据结构动态计算，而不是写死固定数字？（加内容后数字必须自动更新，否则会变成错误信息）
- [ ] 是否没有开放式文本题？
- [ ] 反馈区默认是否可见，而不是 display:none？
- [ ] 术语是否做了恰当跨语言处理，没有出现「无头 Chrome 渲染」式的生硬直译？
- [ ] 是否原样粘贴了「固定互动引擎」，没有让模型自己另写互动 JS？
- [ ] 题目是否只用 data-* 属性承载答案与反馈，且每题点击「检查」都真有反应？
- [ ] 是否左侧固定「任务进度 + 导航栏」侧边栏，右侧主区单列？
- [ ] 主区内是否全部纵向堆叠（目标 1-5、各类卡片），没有任何卡片横向并排？
- [ ] 输出语言是否默认为中文，且仅在用户明确指定时才改用其他语言？
- [ ] **（课程/真题场景）** 计算题是否用 walkthrough + wt-step 逐步推演，而不是只给结论？
- [ ] **（课程/真题场景）** 每道真题是否标注了出处（📎 真题来源/提纲出处）？
- [ ] **（部署 GitHub Pages）** 推成批图片/大资源前，仓库根是否放了空 `.nojekyll`？（否则 Jekyll build fail，页面 404）
- [ ] **（静态网页自动更新 · 必须）** 更新任何静态页面内容后，是否同时 bump 了页面内联的 `PAGE_V`（+1）**和** `version.json` 的 `v`（同值）？两者必须严格相等，否则用户会无限刷新。（详见「静态网页自动更新标准」章节：内联 PAGE_V vs fetch version.json cache:no-store 对比 → 不一致自动 reload）
- [ ] **（静态网页自动更新 · IIFE）** 页面是否粘贴了「自动刷新 IIFE」（fetch version.json 带 `?t=Date.now()` + `cache:'no-store'`，对比 PAGE_V 不一致则 reload）？meta 缓存头是否也加了（双保险）？
- [ ] **（HTML 结构）** section/div/table/tr/td 等标签开闭数量是否一致？（用脚本对比，不只靠 node --check 查 JS）
- [ ] **（引用图片）** 所有 `<img src>` 引用的图片文件名是否都真实存在？（中文文件名必须重命名为英文短名，避免 URL 编码问题）
- [ ] **（表情种草）** module 标题表情是否用运行时 IIFE 按 sec-id 语义映射注入，而不是手改 N 处 HTML？
- [ ] 页脚是否含 lyzbcy 推广署名（「捞鱼」指向 lyzbcy.github.io）？
- [ ] **（推广）** 是否默认挂上了 4 大导流入口（浮条/作者介绍/三栏二维码/页脚）+ 表情包种草 5 触点？
- [ ] **（推广 · 二维码）** 模态框三栏二维码格（QQ群 / 赞赏 / 微信表情包）是否每一格都放了**真实可扫的二维码图片**（不是空格、不是只有文字）？微信表情包二维码是否已执行 `curl ... -o img/sticker/sticker-qr.png` 下载到本地自托管？（QQ群、赞赏从 `E:\短视频创作\项目\...如果今年高考...\img\ui\` 复制 qq-group.jpg / reward-qr.jpg）
- [ ] **（语音 · 仅用户同意时）** 是否先询问过用户「是否开启后台语音播报」？未明确同意则不应出现任何语音相关产物。
- [ ] **（语音 · 仅用户同意时）** 语音稿是否做了**口语化改写**（不是把正文/表格/选择题原样照念）？每段 150~400 字、开头点题结尾收束？
- [ ] **（语音 · 仅用户同意时）** `audio-script.json` 里每个 `id`/`src` 与 HTML 里 `#voicePlaylist` 数组的 `id`/`src` 是否一一对应？`audio/<id>.mp3` **和** `audio/<id>.json`（字幕）文件是否都已由 `python scripts/tts.py audio-script.json --out-dir audio/` 真实生成成功？（tts.py 现在同时产出 mp3 + 字幕 JSON）
- [ ] **（语音 · 仅用户同意时）** 是否放了 `#voicePlaylist`（播放列表 JSON）+ `#voiceFab`（**右侧书签脊入口，不是右下圆形浮条**——避开「关于捞鱼」）+ `#voicePlayer`（圆润玩具风播放器，含可拖动 `.vp-seek` + `.vp-cur`/`.vp-dur` 时间显示 **+ `.vp-sub` 字幕区**）？「固定语音引擎」+「字幕同步引擎」是否都原样粘贴、未改写逻辑？
- [ ] **（语音 · 仅用户同意时 · 字幕）** 字幕引擎是否用 **`MutationObserver` 监听 `.vp-cur`/`.vp-title`** 驱动字幕（而非找 audio 对象——`new Audio()` 不入 DOM 找不到，这是踩过的坑）？播放后字幕是否真的逐句跟随高亮（不要卡在初始文案）？
- [ ] **（语音 · 仅用户同意时 · 书签脊）** `#voiceFab` 是否做成右侧竖条书签脊（`width` + `cubic-bezier` 缓动 + 文字 `opacity` 淡入），而**不是** `writing-mode` 切换（那是离散跳变，不丝滑）？悬停是否平滑拉出？
- [ ] **（源材料 · PDF 提取）** 中文 PPT 导出的 PDF 是否用 **pymupdf** 提取（而非 pdftotext，后者对 Adobe-GB1/SimSun 字体报 CMap 错且乱码）？
- [ ] **（源材料 · 逐字稿）** 语音转写逐字稿是否做了同音错字纠正（微盛≠威盛、企微≠前微信、SCRM≠SCM）？学习地图里是否**避免了「逐字稿」字样**（改用「培训发言稿/分享」，因为会被同事看到）？
- [ ] **（目录页 · 新增章节）** 新增一章时是否走了「解密 → 加卡片 + build-search 重生成 SEARCH_INDEX → 重新加密 → bump PAGE_V + version.json」完整流程？重新加密后是否用密码 round-trip 验证（能解开、新卡片在、标签平衡）？
- [ ] **（目录页 · 安全）** 解密后的明文临时文件（`_plaintext.html` 等）是否已加入 `.gitignore` 且**未提交到 git**？部署后是否删除了本地明文？

---

## 成功标准

读者完成后应该能做到：

- 说出作者真正回答的问题
- 列出核心判断及其原文依据
- 区分原文事实、作者判断和辅助解释
- 解释关键概念之间的关系
- 指出容易误解的地方
- 提出下一步值得追问的问题

lyzbcy 的目标不是“轻松看完”，而是“准确理解”。

## 互动题稳定性（与固定引擎配合）

生成 HTML 互动题时必须满足：

1. 题目只使用选择题、判断题、匹配题、排序题等可闭环题型；不要用开放式 textarea 作为题目（textarea 只能用于只读学习报告）。
2. 每个题块必须包含 data-task、data-answer、check 按钮、feedback 反馈区。
3. feedback 默认必须可见，初始文案写：选择后点击检查，这里会显示反馈。不要用 display:none。
4. 互动逻辑统一使用上文「固定互动引擎」，原样粘贴并放在 `</body>` 前；不要让模型自己另写绑定逻辑（引擎已用事件委托，不需要再逐个按钮绑定）。
5. 生成文件后必须抽取 script 内容并运行 `node --check`，确认没有语法错误。
