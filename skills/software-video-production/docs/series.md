# 系列成长记录与上期反馈

仅为用户明确启用的系列使用，配置和历史放该用户的私人项目，不把个人创作偏好写成所有使用者的强制片头。读取项目的系列配置：首发日依据、时区、固定位置、已发布作品账本和上期选择规则。不要将真实账号、作品ID、封面、数据、签名URL或本机路径装入公开skill。 系列配置已记录的回顾、互动、常驻BGM、事件音效与片尾展示偏好继续沿用，不能因为用户这次没重说就漏掉；当前明确要求可覆盖。具体个人默认值留在私人系列配置，skill只规定读取和核对。

## 天数与画面位置

`series.epochDate`固定为该工作流首次公开发布的当地日期，保留可核查发布记录；首日为第1天。`episodeDate`是本期采用的北京时间日期，按自然日差加1，跨版本、跳更、重渲染不重置，也不按期数累加。不要让最终渲染机器的时区或午夜时间临时改变文案。

系列小标记默认中上方常驻“用AI剪视频的第xx天”。本实现720×1280逻辑画布中，框为x110–610、y52–98；缩放随输出尺寸。它保持静止，给主体、字幕和平台控件留出位置；最终平台裁切仍需实看。上期封面与数据集中短暂展示，先兑现本期开头，再按内容衔接，不强制另起片头或拉长等待。

Remotion各镜可传`series:{enabled:true,epochDate,episodeDate,timezone:"Asia/Shanghai",position:"upper-center"}`。同一片全镜共享同一份配置。混合真实录屏与Remotion镜头时，不只给动画镜头贴标：`render_shots.cjs`配置`exportSeriesBadge:true`，用第一镜设置导出全画布透明`series-badge.png`；将其路径、SHA256和`approved:true`填入EDL工程`series_badge`，`render_edl.py`在全片合成并最后烧字幕。此模式的源镜头不要另行烧入小标记，避免重复覆盖。检查首帧、每个切点、真实录屏段、片尾和EOF；PNG仅负责标记，不代表系列数据已验证。

## 上期的确定与采集

1. **先确定“上期”属于哪个内容系列。** 已知当前系列或期数时，必须先按 `seriesId` 匹配同系列，已知本期第 N 期则选已发布的第 N−1 期；不得拿其他题材中较新的作品代替。找不到同系列上一期，保留待核验并定位作品，不回退到账号最新作品或其他软件广告。只有未指定具体内容系列时，才从已发布账本中选择最新一条使用该工作流的作品；排除无关新作品、草稿和未发布项，绑定平台作品ID、标题与发布回执。若账本缺失，先识别候选并确认，不能直接取账号最新作品。抓取本期制作时的累计数据，保存采集时间；不同统计窗口不混合。
2. 在当前已登录浏览器中打开抖音创作者平台对应作品详情。先读取当前账号和作品标题/ID，核对发布回执，再读作品级指标。使用可用浏览器工具和当前DOM；不导出登录凭据、不猜接口或签名参数。
3. 当前已验证页面：`https://creator.douyin.com/creator-micro/work-management/work-detail/<作品ID>`；DOM的`data-metric-key`分别为`view_count`（播放量）、`like_count`（点赞量）、`favorite_count`（收藏量）、`comment_count`（评论量）、`subscribe_count`（涨粉量）。必须先实看页面标签，再读对应标题和值。页面改版时重新观察，不能默默取相邻数字。账号页“净增粉丝”不等于单作品新增关注。
4. **回顾必须展示对应上期的真实封面，并与标题、作品ID、数据属于同一条作品。** 不能只放数字或用本期封面、软件图标代替；封面缺失属于回顾未完成。取得该作品详情页实际封面原图；若页面允许，可从已加载且允许跨域的封面img绘制到canvas后导出PNG，或使用可用的官方/浏览器图片获取。核对封面和同一作品ID，保存哈希。不要抓头像、随机最新封面或截图整张后台；不将签名URL当长期可用素材。需要脱敏时先处理派生图。
5. 保存原始标签与显示值、来源、采集时间、统计口径、已审核的封面路径/哈希。拿不到的指标省略；实际0保留。`1.2万`等平台约数保留原显示，不冒充精确12000。本系列本来就没有上期时可省略；已有系列配置、发布账本或用户明确要求回顾时，先追踪同系列实际最新一期，不能以“本轮没提供”为由静默跳过。找不到身份、封面或实时指标时记录具体缺口并继续定位，仍无法取得则向用户说明，不能把回顾缺失当作已完成。不得虚构全0。

## 冻结输入与生成

`series_state.py`使用已有私人配置，不自动登录、刷新或发布：

```powershell
python scripts/series_state.py --profile "<项目>/series.json" --snapshot "<项目>/snapshot.json" --episode-date YYYY-MM-DD --output "<项目>/previous-shot.json"
```

profile可选`currentSeriesId`与`currentEpisodeNumber`以限定同系列上一期；已启用系列限定但账本缺失时会报错，不自动替换其他系列。每条已发布记录用`seriesId`、`episodeNumber`标注归属。profile含`epochDate`、`timezone`、可选`visualStyle`与`episodes:[{itemId,title,publishedAt,workflow:"software-video-production",published:true}]`。snapshot含同一`itemId`、`sourceUrl`、带时区的`snapshotAt`、`period:"cumulative"`、`approved:true`、`coverPath`、`coverSha256`、`coverApproved:true`、`metrics:{views/likes/favorites/comments/followers:{sourceLabel,raw}}`；sourceLabel使用上方真实页面名称。审核标志只记录已完成的核对，不自动证明真实性。

输出可作为`previous_episode`镜头加入现有渲染配置。回顾展示真实封面、上期标题、已取得指标及北京时间采集时刻。随后回到本期主线；是否更有吸引力需靠实际视听与后续数据判断。发布后将本期ID、实际发布时间和回执加入私人账本，下次重新采集，不能把旧快照当已刷新。
