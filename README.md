# LOCUST Journal《学术蝗虫》

> **Speeches fade, snacks remain.**
> **报告转瞬即逝，茶歇亘古长存**

非营利趣味模拟学术期刊，专收各类**无法在正式期刊发表的研究副产物**：失败的实验、离谱的观测、复现不出来的结论、实验室玄学现象、工程踩坑记录。

⚠️ 本刊为**纯娱乐性质的模拟学术刊物**，不具备任何学术效力，不可用于毕业、评奖、职称认定与项目申报。

- **站点**：<https://locustjournal.com>
- **技术栈**：Hugo Extended + PaperMod · 纯静态，无后端
- **托管**：Cloudflare Pages
- **许可**：永久免费，不收取任何版面费、审稿费

---

## 快速开始

```bash
# 1. 确认 Hugo 是 Extended 版（必须）
hugo version        # 输出需带 +extended

# 2. 本地预览
hugo server -D      # → http://localhost:1313

# 3. 生产构建（严格模式，warning 即失败）
hugo --gc --minify --panicOnWarning
```

部署上线请看 **[DEPLOY.md](DEPLOY.md)**，含 GitHub 私有仓 → Cloudflare Pages → 域名绑定 → 301 的完整 runbook。

---

## 目录结构

```text
locustjournal/
├── config.toml              # 站点配置（唯一需要改的地方）
├── DEPLOY.md                # 部署 runbook
├── content/                 # 所有内容（Markdown）
│   ├── _index.md            # 首页
│   ├── about.md             # 发刊宗旨
│   ├── guide.md             # 投稿须知
│   ├── board.md             # 编委会
│   ├── archive.md           # 总归档
│   ├── articles/            # 蝗札（正式刊载，需双盲评审）
│   │   ├── _index.md
│   │   └── vol1/            # 卷期目录
│   │       ├── _index.md
│   │       ├── article01.md
│   │       └── article02.md
│   └── scholar/             # 蝗客学社（随笔，仅合规审核）
│       ├── _index.md
│       └── essay01.md
├── layouts/                 # 覆盖主题模板（不改 themes/）
│   ├── baseof.html          # 替换废弃的 .Language.LanguageDirection
│   ├── index.html           # 首页：封面 + 本卷要目
│   ├── imprint.html         # 刊务公告页（发刊宗旨 / 投稿须知 / 编委会）
│   ├── archive.html         # 总归档：逐卷总目次
│   ├── 404.html             # 期刊语气 404 页
│   ├── rss.xml              # 替换废弃的 .Language.LanguageCode
│   ├── _default/
│   │   ├── single.html      # 蝗札单篇：篇首 + 摘要框 + 审稿意见书
│   │   └── list.html        # 栏目目录页
│   ├── scholar/single.html  # 学社随笔单篇（独立版式，不配指数）
│   └── _partials/templates/opengraph.html
├── assets/css/extended/     # 期刊样式（PaperMod 用 resources.Match 自动收录）
├── static/assets/           # 静态资源
│   ├── images/              # favicon / logo / locust.svg
│   └── pdf/vol1/            # 稿件 PDF（由 tools/make_pdf.py 生成）
├── themes/PaperMod/         # 主题（git submodule，勿直接改）
├── tools/
│   ├── make_pdf.py          # Markdown → 排版 PDF（reportlab）
│   └── visual_audit.js      # Playwright 视觉审计（截图 + 对比度 + 溢出）
└── .gitignore
```

---

## 内容规范

### 栏目

| 栏目 | 路径 | 审核 | 配发蝗掠指数 |
|------|------|------|--------------|
| 蝗札 · Articles | `content/articles/` | 双盲趣味评审 | 是 |
| 蝗客学社 · Locust Scholar | `content/scholar/` | 仅合规性审核 | 否 |

### 新增一篇蝗札

1. 复制 `content/articles/vol1/article01.md` 到对应卷期目录
2. 填 front matter：`title` / `titleEn` / `authors` / `affiliation` / `date` / `tags` /
   `vol` / **`seq`**（篇序，决定目录顺序）/ **`page`**（页码）/ **`locust_index`** /
   **`review`**（巡食官评语，支持 `**加粗**`）/ **`verdict`** / `pdf`
3. 正文不要再写一级标题和审稿块 —— 篇首与审稿意见书都由 `single.html` 输出
4. 目录页、首页要目、归档总目会**自动收录**，无需改任何模板
5. 重新生成 PDF：`python tools/make_pdf.py`
6. 跑一次 `hugo --gc --minify --panicOnWarning` 确认零警告

### 蝗掠指数

满分 10 分。分值越高 = 实验翻车越彻底 + 论证越一本正经 + 结论越令人忍俊不禁。
纯粹空洞灌水趋近于 0 分。

### 审稿结论（四级）

`准予登札` / `回甸重啃` / `留甸待阅` / `驱蝗驳回`

**核心拒稿理由：学术过端** —— 过度堆砌公式、滥用术语、行文晦涩，丧失趣味本质。
稿件可以无用，但不能无趣。

---

## 约定与踩坑记录

**主题不要直接改**：`themes/PaperMod/` 是 submodule。需要改样式/模板时，在项目根的
`layouts/` 或 `assets/css/extended/locust-journal.css` 里覆盖，否则主题更新会冲掉。

**样式加载路径**：PaperMod 用 `resources.Match "css/extended/*.css"` 自动收录，
所以样式必须放 `assets/css/extended/`。**不要在 config.toml 里配 `customCSS`** ——
该主题版本不支持这个参数，配了不生效反而误导。

**Hugo 模板作用域**：块内 `{{ $x := ... }}` 的作用域不外传，要跨 `if` 复用必须
在外层先 `{{ $x := ... }}` 声明、块内用 `{{ $x = ... }}` 赋值，否则报
`undefined variable "$x"`。

**`.RegularPages` 不递归子 section**：稿件放在 `content/articles/vol1/` 时，
`/articles/` 页的 `.RegularPages` 长度为 0，目录会是空的。必须从全局取：
`where site.RegularPages "Section" .Section`。`where` 只支持 `= != in notin intersect`，
没有 `Prefix` / `Match` 操作符。

**Hugo 注释不能嵌套 `*/`**：跨行注释里再出现 `*/` 会提前闭合，报
`comment ends before closing delimiter`。拆成两行或换措辞。

**Hugo 0.158+ 字段改名**（本项目已全部覆盖，勿退回旧写法）：

| 废弃 | 新写法 |
|------|--------|
| `languageCode`（项目级） | `locale` |
| `site.Language.LanguageCode` | `site.Language.Locale` |
| `.Language.LanguageDirection` | `.Language.Direction` |
| `languages.xx.languageName` | `languages.xx.label` |

**栏目隔离**：首页文章流由 `config.toml` 的 `mainSections = ["articles"]` 限定，
避免蝗客学社随笔混进蝗札列表。卷期页加 `hiddenInHomeList: true` 避免重复渲染。

**PDF 生成**：`tools/make_pdf.py` 依赖 reportlab，装在隔离 venv 里：

```bash
/Users/dynooob/.workbuddy/binaries/python/envs/default/bin/pip install reportlab
/Users/dynooob/.workbuddy/binaries/python/envs/default/bin/python tools/make_pdf.py
```

macOS 上 PingFang / STHeiti 走 TTC 多子表、Hiragino 是 PostScript 轮廓，
reportlab 都不认，脚本会自动回退到 `/Library/Fonts/Arial Unicode.ttf`（中文显示正常）。

**视觉审计**：

```bash
hugo --gc --minify                       # 先出静态产物
/Users/dynooob/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  -m http.server 1313 --bind 127.0.0.1 --directory public &   # 必须后台常驻
NODE_PATH=/Users/dynooob/.workbuddy/binaries/node/workspace/node_modules \
  OUT=/tmp/lj-audit \
  /Users/dynooob/.workbuddy/binaries/node/versions/22.22.2/bin/node tools/visual_audit.js
```

13 条路由 × 桌面/移动双视口，检查资源 404、横向溢出、WCAG 对比度、零尺寸元素。
截图落在 `$OUT/`。

**审计报告里这两类是已知误报，不用管**：
- `livereload.js` 404 —— `hugo server` 的调试脚本，静态 `public/` 与生产环境都没有
- `/nope-404/` 404 —— 那就是 404 页本身，预期行为

---

## 边界守则

- 不申请刊号，不宣称出版资质
- 不收取任何费用，不开展商业合作
- 不提供录用函 / 发表证明
- 不主动全网引流，限定科研与技术社群内传播
- 内容红线：涉密隐私、违法教程、敏感议题、人身攻击、商业推广一律不收
