# LOCUST Journal 部署 Runbook

> V1.0 静态站 · Hugo Extended + PaperMod · Cloudflare Pages · locustjournal.com

本文档是**可复制粘贴的分步操作手册**。每一步都带验证命令，执行后请确认结果再进入下一步。

**当前状态（2026-09-30）**：代码已推送至 `github.com/Locust-Journal/locustjournal`（`main` 分支，commit `01033ae`），
本地与 GitHub 干净克隆的构建产物**逐字节一致**。Cloudflare 侧待配置。

---

## Step 0 · 前置检查

| 项 | 要求 | 检查命令 |
|----|------|----------|
| Hugo | **Extended** 版本（`+extended` 后缀） | `hugo version` |
| Git | 任意近期版本 | `git --version` |
| Cloudflare 账号 | 域名需已托管在 Cloudflare DNS | — |

> ⚠️ **必须是 Extended 版**。本项目验证过用的是 `v0.167.0+extended`。
> 输出里带 `+extended` 才是对的。

```bash
hugo version
# 期望：hugo v0.167.0+extended darwin/arm64
```

<details>
<summary>macOS 装不上 Hugo？点这里（brew 会失败）</summary>

`brew install hugo` 在 macOS 上可能因嵌套 sandbox 失败
（`sandbox-exec: sandbox_apply: Operation not permitted`），且会卡住 20 分钟以上。
`HOMEBREW_NO_SANDBOX=1` 和手动授权都无效——brew 内部自套 sandbox。

Hugo 0.167+ 起 macOS 只发 `.pkg` 不发 `.tar.gz`，手动装法：

```bash
VER=0.167.0
curl -sSL -C - --retry 20 --retry-all-errors --max-time 3000 \
  -o /tmp/hugo_ext.pkg \
  "https://github.com/gohugoio/hugo/releases/download/v${VER}/hugo_extended_${VER}_darwin-universal.pkg"

cd /tmp && rm -rf hugopkg && mkdir hugopkg && cd hugopkg
xar -xf /tmp/hugo_ext.pkg
mkdir x && cd x && gzip -dc ../Payload | cpio -i

cp hugo /opt/homebrew/bin/hugo && chmod +x /opt/homebrew/bin/hugo
hugo version   # 确认带 +extended
```

> GitHub Release 下载极慢（42MB 可能要 20+ 分钟），务必用 `-C -` 断点续传并放后台跑。
</details>

---

## Step 1 · 本地构建与预览

```bash
cd /Users/dynooob/Projects/locustjournal

# 生产构建（严格模式：任何 warning 都返回非 0）
hugo --gc --minify --panicOnWarning
echo "exit=$?"   # 必须是 0

# 本地预览（含草稿）
hugo server -D   # → http://localhost:1313
```

**期望输出**：`Pages │ 60`，`Static files │ 11`，`Total in ~30 ms`，无任何 WARN。

**验证清单**（逐项确认）：

- [ ] 首页标语分行显示：`Speeches fade, snacks remain.` / `报告转瞬即逝，茶歇亘古长存`
- [ ] 顶部导航 7 项齐全：首页 / 发刊宗旨 / 投稿须知 / 蝗札 / 蝗客学社 / 编委会 / 总归档
- [ ] `/articles/` 表格 2 行，「网页」「下载」两个链接都能点开
- [ ] 两篇蝗札文末出现「蝗掠指数 + 巡食官评语 + 审稿结论」三段（**必须分行，不能挤成一行**）
- [ ] `/scholar/` 3 篇随笔可点开
- [ ] **首页底部只出现蝗札，不混入学社随笔**（栏目隔离验证）
- [ ] 移动端（375px）导航独占一行、可横向滑动、右缘有渐隐提示
- [ ] `/nope-404/` 返回期刊语气的 404 页

**可选 · 视觉审计**（13 路由 × 桌面/移动双视口）：

```bash
hugo server -D &
NODE_PATH=/Users/dynooob/.workbuddy/binaries/node/workspace/node_modules \
  /Users/dynooob/.workbuddy/binaries/node/versions/22.22.2/bin/node tools/visual_audit.js
# 截图落在 /tmp/locust-audit/，报告为 report.json
# 期望：资源 404 = 0、横向溢出 = 0、低对比度 = 0
```

> 注：审计报告里 `/nope-404/` 会显示 `res=1`，那是 404 页面本身的正确响应，不是缺陷。

---

## Step 2 · 推送

> 遵循既有纪律：**未经明确指示不自动 commit / push。**

```bash
cd /Users/dynooob/Projects/locustjournal
git add -A
git status --short            # 人工过一遍，确认没有 public/、.DS_Store
git commit -m "content: 更新第 X 卷"
git push
```

**远程仓库**：`https://github.com/Locust-Journal/locustjournal.git`（`main` 分支）

**submodule 说明**：`themes/PaperMod` 是 git submodule（指针 `d376885`）。
Cloudflare 克隆时会自动拉取，本地克隆若主题为空需执行：

```bash
git clone --recurse-submodules <url>
# 或已克隆后：
git submodule update --init --recursive
```

验证 submodule 状态：

```bash
git ls-tree HEAD themes/     # 应显示 160000 commit d376885... themes/PaperMod
find themes/PaperMod -type f | wc -l   # 应为 126
```

---

## Step 3 · Cloudflare Pages 部署

### ⚠️ 先说结论：不要用你截图里的 Workers 配置

你截图那个面板（构建命令栏提示 `npx wrangler deploy`）是 **Workers** 的配置界面，
对静态 Hugo 站点不适用。仓库里也确实没有任何 `wrangler.toml` / `package.json`。

**正确路径**：Workers & Pages → **Pages** → Connect to Git。

### 操作步骤

1. 登录 <https://dash.cloudflare.com>
2. 左侧 **Workers & Pages** → **Pages** → **Create application** → **Connect to Git**
3. 授权 Cloudflare 访问 GitHub 仓库 `Locust-Journal/locustjournal`
   （若仓库是 Private，需在 GitHub 侧 Settings → Apps → 安装 Cloudflare Pages 应用并授权该仓）
4. 选择仓库 → **Start deployment**

### 构建设置（逐项照填）

| 字段 | 值 |
|------|-----|
| Project name | `locustjournal` |
| Production branch | `main` |
| Framework preset | `Hugo` |
| **Build command** | `hugo --gc --minify` |
| **Build output directory** | `public` |
| Root directory | *（留空）* |
| Build comments / environment | *（留空）* |

> **Build command 不要加 `--panicOnWarning`**。Cloudflare 的 Hugo 版本若与本地有细微差异，
> 严格模式可能在远端因无害 deprecation 直接失败，导致整站部署不了。本地自己把关即可。

### 环境变量（Settings → Environment variables → Add）

| 名称 | 值 | 环境 |
|------|-----|------|
| `HUGO_VERSION` | `0.167.0` | Production + Preview |
| `HUGO_ENVIRONMENT` | `production` | Production |
| `HUGO_ENVIRONMENT` | `development` | Preview |

> ⚠️ **`HUGO_VERSION` 必须填**，Cloudflare 不会自动推断。不填会用它默认的版本，
> 出现"本地好好的、线上白屏"。

5. **Save and Deploy**，等待 1–3 分钟，得到 `https://locustjournal.pages.dev` 形式的临时地址

### 验证

```bash
BASE=https://<你的项目名>.pages.dev

curl -sI $BASE | head -1                                    # 期望 HTTP/2 200
curl -s $BASE/ | grep -o 'Speeches fade, snacks remain'      # 应有输出
curl -s -o /dev/null -w '%{http_code}\n' $BASE/articles/vol1/article01/   # 期望 200
curl -s -o /dev/null -w '%{http_code}\n' $BASE/assets/pdf/vol1/article01.pdf  # 期望 200
```

如果构建日志报 **找不到主题 / 样式全丢**，说明 submodule 没拉下来。
在 Cloudflare 侧把 Build command 临时改成：

```bash
git submodule update --init --recursive && hugo --gc --minify
```

---

## Step 4 · 绑定自定义域名

1. Pages 项目 → **Custom domains** → **Set up a custom domain** → 输入 `locustjournal.com`
2. 域名若已在 Cloudflare DNS，会自动添加记录，无需手动改 DNS
3. 等待证书签发（通常几分钟，最长 24 小时）

**验证证书**：

```bash
echo | openssl s_client -servername locustjournal.com -connect locustjournal.com:443 2>/dev/null \
  | openssl x509 -noout -dates -subject
```

### www → 主域 301

**方式 A · Cloudflare Redirect Rules**（推荐，边缘生效）
- Rules → Redirect Rules → Single Redirect
- 条件：`http.host eq "www.locustjournal.com"`
- 目标：`https://locustjournal.com` + **Pass query string** + **Always HTTPS**

**方式 B**：在 Pages 自定义域里也加 `www.locustjournal.com`，再用同样的规则跳转

```bash
curl -sI https://www.locustjournal.com | head -3    # 期望 301 → https://locustjournal.com/
curl -sI https://locustjournal.com | head -1        # 期望 200
```

> ⚠️ 换域名后**务必点一次 Retry deployment**，让站点用正确 baseURL 重新构建。
> 漏了这步，站内链接会全部指向 `pages.dev`——这是最常见的翻车点。

---

## Step 5 · 上线后验证

```bash
BASE=https://locustjournal.com

for p in / /about/ /guide/ /articles/ /articles/vol1/ \
         /articles/vol1/article01/ /articles/vol1/article02/ \
         /scholar/ /scholar/essay01/ /scholar/essay02/ /scholar/essay03/ \
         /board/ /archive/ /sitemap.xml /index.xml /robots.txt \
         /assets/pdf/vol1/article01.pdf /assets/pdf/vol1/article02.pdf \
         /assets/images/favicon.png; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' "$BASE$p")  $p"
done
```

**期望**：以上全部 200（`/nonexistent/` 返回 404 属正常）。

站内链接全量体检：

```bash
cd public 2>/dev/null || git clone --depth 1 <url> && cd <repo> && hugo --gc --minify
python3 - <<'PY'
import os, re, glob
pages = glob.glob('**/*.html', recursive=True)
links = set()
for p in pages:
    html = open(p, encoding='utf-8').read()
    for m in re.finditer(r'(?:href|src)=(?:"([^"]+)"|\'([^\']+)\'|([^\s>]+))', html):
        u = next(g for g in m.groups() if g is not None)
        if u.startswith(('http', '//', 'mailto:', '#', 'data:', 'javascript:')) or 'livereload' in u:
            continue
        links.add((p, u))
bad = []
for src, u in sorted(links):
    path = u.split('#')[0].split('?')[0]
    if not path or path == '/':
        continue
    tgt = path.lstrip('/') if path.startswith('/') else os.path.normpath(os.path.join(os.path.dirname(src), path))
    if os.path.isfile(tgt) or os.path.isdir(tgt) or os.path.isfile(tgt.rstrip('/') + '/index.html'):
        continue
    bad.append((src, u))
print(f'HTML {len(pages)} 个，链接 {len(links)} 条，断链 {len(bad)} 条')
for s, u in bad:
    print(' ', s, '->', u)
PY
```

最后浏览器硬刷新（Cmd+Shift+R），确认无 404 资源、无控制台报错。

---

## 常见故障速查

| 现象 | 根因 | 处置 |
|------|------|------|
| **构建命令栏提示 `npx wrangler deploy`** | 你在 Workers 界面，不是 Pages | 回到 Workers & Pages → **Pages** → Create |
| 线上白屏，无样式 | 非 Extended 版 / `HUGO_VERSION` 未填 | 查构建日志首行的 hugo 版本 |
| 找不到主题，样式全丢 | submodule 未拉取 | Build command 前加 `git submodule update --init --recursive &&` |
| 站内链接指向 `pages.dev` | 换域名后没重新构建 | **Retry deployment** |
| 构建因 warning 失败 | 远端 Hugo 版本与本地有差异 | Build command 去掉 `--panicOnWarning` |
| 中文显示方块 | 字体栈缺中文回退 | 见下方「中文字体」 |
| 导航某项缺失 | `pageRef` 与实际文件不符 | 核对 `content/` 下文件名 |
| 提交后线上没更新 | 分支不是 `main` | 核对 Production branch |

### 中文字体

站点已在 `assets/css/extend/custom.css` 里配好中文优先字体栈
（PingFang SC → Hiragino Sans GB → Microsoft YaHei → Noto Sans CJK SC）。
如需调整字体，直接改该文件，**不要动 `themes/`**。

### 提交新稿件的完整流程

```bash
# 1. 新增 content/articles/volN/articleNN.md，填好 front matter
# 2. 更新 content/articles/_index.md 的表格
# 3. 重新生成 PDF
/Users/dynooob/.workbuddy/binaries/python/envs/default/bin/python tools/make_pdf.py

# 4. 本地严格验证
hugo --gc --minify --panicOnWarning && echo "构建 OK"

# 5. 提交（需明确指示）
git add -A && git commit -m "content: 第 N 卷新增 M 篇" && git push

# 6. Cloudflare Pages 自动检测 push 并重建，无需手动触发
#    查看：Dashboard → Pages → locustjournal → Deployments
```

---

## 目录速查

```text
locustjournal/
├── config.toml              # 站点配置（改这里）
├── DEPLOY.md                # 本文件
├── README.md                # 项目说明
├── content/                 # 所有内容
│   ├── _index.md  about.md  guide.md  board.md  archive.md
│   ├── articles/            # 蝗札（双盲评审 + 蝗掠指数）
│   │   └── vol1/            # 卷期目录
│   └── scholar/             # 蝗客学社（仅合规审核）
├── layouts/                 # 覆盖主题模板（不改 themes/）
│   ├── 404.html
│   ├── baseof.html          # 修 Hugo 0.158+ 废弃字段
│   ├── rss.xml
│   └── _partials/templates/opengraph.html
├── assets/css/extend/custom.css
├── static/assets/
│   ├── images/              # favicon 全套 + logo + locust.svg
│   └── pdf/vol1/            # 稿件 PDF（由 tools/make_pdf.py 生成）
├── themes/PaperMod/         # 主题（submodule，勿直接改）
└── tools/
    ├── make_pdf.py          # Markdown → 排版 PDF
    └── visual_audit.js      # Playwright 视觉审计
```

**改主题样式的正确姿势**：不要直接编辑 `themes/PaperMod/`，更新主题时会被冲掉。
用 `assets/css/extend/custom.css` 或项目根 `layouts/` 覆盖。
