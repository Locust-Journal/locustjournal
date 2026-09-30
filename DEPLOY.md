# LOCUST Journal 部署 Runbook

> V1.0 静态站 · Hugo Extended + PaperMod · Cloudflare Pages · locustjournal.com

本文档是**可复制粘贴的分步操作手册**。每一步都带验证命令，执行后请确认结果再进入下一步。

---

## Step 0 · 前置检查清单

| 项 | 要求 | 检查命令 |
|----|------|----------|
| Hugo | **Extended** 版本（`+extended` 后缀） | `hugo version` |
| Git | 任意近期版本 | `git --version` |
| GitHub 账号 | 需能创建私有仓库 | — |
| Cloudflare 账号 | 域名需已托管在 Cloudflare DNS | — |

> ⚠️ **必须是 Extended 版**。非 Extended 版不支持 SCSS，PaperMod 的样式表会构建失败且报错信息极其难懂（会表现为一堆 CSS 缺失的空白页面）。
> 检查：输出里带 `+extended` 才是对的。

```bash
hugo version
# 期望输出：hugo v0.148.2+extended darwin/arm64
```

若未安装：

```bash
# macOS (Homebrew)
brew install hugo

# 或手动安装（不依赖 brew）
curl -sL -o /tmp/hugo.tar.gz \
  "https://github.com/gohugoio/hugo/releases/download/v0.148.2/hugo_extended_0.148.2_darwin-universal.tar.gz"
tar -xzf /tmp/hugo.tar.gz -C /usr/local/bin hugo
hugo version
```

---

## Step 1 · 本地构建与预览

```bash
cd /Users/dynooob/Projects/locustjournal

# 生产构建（严格模式，把 warning 当 error）
hugo --gc --minify --logLevel warn

# 本地预览（含未发布草稿）
hugo server -D
```

打开 <http://localhost:1313> 逐页核对。

**验证清单**（逐项确认，不要跳）：

- [ ] 首页标语正确显示：`Speeches fade, snacks remain.` / `报告转瞬即逝，茶歇亘古长存`
- [ ] 顶部导航 7 项齐全且可跳转：首页 / 发刊宗旨 / 投稿须知 / 蝗札 / 蝗客学社 / 编委会 / 总归档
- [ ] `/articles/` 列表页表格 2 行，两篇均可点开
- [ ] `/articles/vol1/article01/` 与 `article02/` 完整渲染，含摘要、引言、实验环境等章节
- [ ] 两篇文末出现「蝗掠指数」评审块（引用块样式）
- [ ] `/scholar/` 3 篇随笔可点开
- [ ] 页脚免责声明完整显示（两行）
- [ ] 移动端（375px 宽）导航折叠为汉堡菜单
- [ ] **构建无 warning 输出**（有 warning 先修，别带着上线）

```bash
# 严格模式验证：任何 warning 都会让命令返回非 0
hugo --logLevel warn --panicOnWarning
echo "exit=$?"   # 必须是 0
```

---

## Step 2 · 提交并推送

> 遵循既有纪律：**未经明确指示不自动 commit/push。**

```bash
cd /Users/dynooob/Projects/locustjournal
git add -A
git status --short          # 人工过一遍，确认没有 public/、.DS_Store
git commit -m "feat: LOCUST Journal V1.0 站点骨架与首卷内容"
```

**新建 GitHub 私有仓库**（推荐私有：本刊为非正式刊物，不希望被搜索引擎抓取内部内容）：

```bash
# 在 GitHub 网页端创建空仓库（不要勾选 README/.gitignore/LICENSE），名为 locustjournal，设为 Private
# 然后：
git remote add origin git@github.com:<你的账号>/locustjournal.git
git push -u origin main
```

验证：

```bash
git remote -v
git log --oneline -1
```

---

## Step 3 · Cloudflare Pages 部署

1. 登录 <https://dash.cloudflare.com>
2. 左侧 **Workers & Pages** → **Pages** → **Create application** → **Connect to Git**
3. 选择 GitHub 账号，授权 Cloudflare 访问 `locustjournal` 仓库
4. 选择该仓库 → 点击 **Start deployment**

**构建设置（关键，逐项核对）**：

| 字段 | 值 |
|------|-----|
| Project name | `locustjournal` |
| Production branch | `main` |
| Framework preset | `Hugo` |
| Build command | `hugo --gc --minify` |
| Build output directory | `public` |
| Root directory | *(留空)* |

**环境变量**（Settings → Environment variables → Add）：

| 名称 | 值 | 环境 |
|------|-----|------|
| `HUGO_VERSION` | `0.148.2` | Production + Preview |
| `HUGO_ENVIRONMENT` | `production` | Production |
| `HUGO_ENVIRONMENT` | `development` | Preview |

> ⚠️ **`HUGO_VERSION` 必须填，Cloudflare 不会自动推断。** 不填的话构建环境用的是它默认的某个版本，可能与你本地不一致，出现"本地好好的线上白屏"。

5. 点击 **Save and Deploy**
6. 等待构建完成（约 1–3 分钟），得到 `https://locustjournal.pages.dev` 形式的临时地址

**验证**：

```bash
# 用临时地址验证（把 <TMP> 换成实际地址）
curl -sI https://<TMP>.pages.dev | head -1        # 期望 HTTP/2 200
curl -s https://<TMP>.pages.dev/ | grep -o 'Speeches fade, snacks remain'  # 应有输出
curl -s -o /dev/null -w '%{http_code}\n' https://<TMP>.pages.dev/articles/vol1/article01/  # 期望 200
```

---

## Step 4 · 绑定自定义域名

1. Pages 项目 → **Custom domains** → **Set up a custom domain** → 输入 `locustjournal.com`
2. Cloudflare 会自动添加 DNS 记录（域名已在 Cloudflare 时自动生效，无需手动操作）
3. 等待证书签发（1 分钟 – 24 小时，通常几分钟）

**验证证书**：

```bash
echo | openssl s_client -servername locustjournal.com -connect locustjournal.com:443 2>/dev/null \
  | openssl x509 -noout -dates -subject
```

4. 配置 `www` 301 重定向到主域：

**方式 A · Cloudflare Redirect Rules**（推荐，边缘生效更快）
- Rules → Redirect Rules → Single Redirect
- 条件：`http.host eq "www.locustjournal.com"`
- 目标：`https://locustjournal.com` + **Pass query string** + **Always HTTPS**

**方式 B · Pages 的 CNAME 方式**
在 Pages 自定义域里额外添加 `www.locustjournal.com`，然后在 Cloudflare Rules 里加同样的跳转。

**验证**：

```bash
curl -sI https://www.locustjournal.com | head -3    # 期望 301 → https://locustjournal.com/
curl -sI https://locustjournal.com | head -1        # 期望 200
```

5. 在 Pages 项目的 **Settings → Environment variables** 确认 `HUGO_VERSION` 仍在，然后点 **Retry deployment**，让站点用正确的 baseURL 重新构建一次（这一步很多人漏掉，导致站内链接仍指向 pages.dev）。

---

## Step 5 · 上线后验证

```bash
BASE=https://locustjournal.com

# 逐页状态码，必须全 200
for p in / /about/ /guide/ /articles/ /articles/vol1/ \
         /articles/vol1/article01/ /articles/vol1/article02/ \
         /scholar/ /scholar/essay01/ /scholar/essay02/ /scholar/essay03/ \
         /board/ /archive/ /sitemap.xml /index.xml; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$p")
  echo "$code  $p"
done
```

**注意**：以下两个会返回 404，属**预期行为**，但需要处理：

| 路径 | 原因 | 处理 |
|------|------|------|
| `/assets/pdf/vol1/article01.pdf` | 尚未放入 PDF | 放入 PDF，或从 `content/articles/_index.md` 移除该列 |
| `/assets/images/favicon.png` | 尚未放入 favicon | 放入 `favicon.png`，或在 config 中移除 `assets.favicon` |

**修复 favicon 404 的两种方式**：

```bash
# 方式 A：放入 512x512 PNG
cp /path/to/your-icon.png static/assets/images/favicon.png

# 方式 B：不配 favicon（编辑 config.toml 删掉 [params.assets] 段）
```

最后浏览器硬刷新（Cmd+Shift+R）确认站点无 404 资源、无控制台报错。

---

## 常见故障速查

| 现象 | 根因 | 处置 |
|------|------|------|
| 线上白屏，无样式 | 非 Extended 版 Hugo / `HUGO_VERSION` 未填 | 检查输出与构建日志 |
| 构建报 SCSS 错误 | PaperMod 需要 Extended | 换 Extended 版 |
| 站内链接指向 `pages.dev` | 换域名后没重新构建 | Retry deployment |
| 中文显示为方块 | 字体栈缺中文回退 | 见下方「中文字体」 |
| 导航栏某项缺失 | `pageRef` 路径与实际文件不符 | 核对 `content/` 下文件名 |
| 列表页 PDF 链接 404 | PDF 未上传 | 上传或移除链接 |
| 提交后线上没更新 | 分支不是 `main`，或未触发 | 核对 Production branch |

### 中文字体（可选优化）

PaperMod 默认字体栈对中文支持一般。若需更好观感，在项目根目录创建 `assets/css/extend/custom.css`：

```css
:root {
  --theme-font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", "Source Han Sans SC",
    "Noto Sans CJK SC", sans-serif;
}
```

并在 `config.toml` 的 `[params]` 下加：

```toml
[params.customCSS]
  = "css/extend/custom.css"
```

> PaperMod 中 `customCSS` 需作为 params 数组项配置。改完跑一次 `hugo server` 确认生效，且中文不再有锯齿/回退异常。

---

## 更新日常维护

改完内容后：

```bash
# 本地先验
hugo --logLevel warn --panicOnWarning && hugo server -D   # 人工过一遍

# 提交（需明确指示）
git add -A && git commit -m "content: 更新第X卷" && git push

# Cloudflare Pages 会自动检测 push 并重建，无需手动触发
```

查看构建状态：Cloudflare Dashboard → Pages → 你的项目 → **Deployments**，最新一次应为绿色 ✅。

---

## 目录速查

```text
locustjournal/
├── config.toml              # 站点配置（改这里，不改主题）
├── content/
│   ├── _index.md             # 首页
│   ├── about.md              # 发刊宗旨
│   ├── guide.md              # 投稿须知
│   ├── board.md              # 编委会
│   ├── archive.md            # 总归档
│   ├── articles/
│   │   ├── _index.md         # 蝗札列表
│   │   └── vol1/             # 第1卷
│   │       ├── _index.md
│   │       ├── article01.md
│   │       └── article02.md
│   └── scholar/
│       ├── _index.md
│       ├── essay01.md
│       ├── essay02.md
│       └── essay03.md
├── static/assets/
│   ├── images/               # favicon、logo
│   └── pdf/vol1/             # 稿件 PDF
├── themes/PaperMod/          # 主题（勿直接改，改用 extend 覆盖）
└── .gitignore
```

**改主题样式的正确姿势**：不要直接编辑 `themes/PaperMod/`，覆盖会被下次更新冲掉。用 `assets/css/extend/custom.css` 或 `layouts/partials/extended_head.html` 覆盖。
