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
│       ├── essay01.md  essay02.md  essay03.md
├── layouts/                 # 覆盖主题模板（不改 themes/）
│   ├── 404.html             # 期刊语气 404 页
│   ├── baseof.html          # 替换废弃的 .Language.LanguageDirection
│   ├── rss.xml              # 替换废弃的 .Language.LanguageCode
│   └── _partials/templates/opengraph.html
├── assets/css/extend/       # 自定义样式（字体栈 / 表格 / 窄屏导航）
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
2. 填写 front matter（`title` / `authors` / `date` / `tags` / `locust_index` / `vol`）
3. 文末加审稿块（蝗掠指数 + 巡食官评语 + 审稿结论）
4. 更新 `content/articles/_index.md` 的表格
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
`layouts/` 或 `assets/css/extend/custom.css` 里覆盖，否则主题更新会冲掉。

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
hugo server -D &
NODE_PATH=/Users/dynooob/.workbuddy/binaries/node/workspace/node_modules \
  /Users/dynooob/.workbuddy/binaries/node/versions/22.22.2/bin/node tools/visual_audit.js
```

13 条路由 × 桌面/移动双视口，检查资源 404、横向溢出、WCAG 对比度、零尺寸元素。
截图落在 `/tmp/locust-audit/`。

---

## 边界守则

- 不申请刊号，不宣称出版资质
- 不收取任何费用，不开展商业合作
- 不提供录用函 / 发表证明
- 不主动全网引流，限定科研与技术社群内传播
- 内容红线：涉密隐私、违法教程、敏感议题、人身攻击、商业推广一律不收
