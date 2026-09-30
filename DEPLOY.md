# LOCUST Journal 部署 Runbook

> V1.0 静态站 · Hugo Extended + PaperMod · Cloudflare Workers（Static Assets）· locustjournal.com

本文档是**可复制粘贴的分步操作手册**。每一步都带验证命令，执行后请确认结果再进入下一步。

**当前状态（2026-09-30）**：代码已推送至 `github.com/Locust-Journal/locustjournal`（`main` 分支）。
仓库根已备好 `wrangler.jsonc` + `build.sh`，Cloudflare Dashboard 侧只剩填几项与点部署。

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

- [ ] 首页刊头居中大写 `LOCUST JOURNAL`，中文副题「学术蝗虫」
- [ ] 顶部导航 7 项齐全：首页 / 发刊宗旨 / 投稿须知 / 蝗札 / 蝗客学社 / 编委会 / 总归档
- [ ] 首页「本卷要目」2 篇蝗札，顺序为 01（7.8）在 02（8.3）之前
- [ ] 首页「学社随笔」独立成节，**不配发蝗掠指数**
- [ ] `/articles/` 目录 2 条、`/scholar/` 3 条、`/archive/` 5 条
- [ ] 两篇蝗札有篇首（题名/作者单位/摘要框/关键词）+ 篇末审稿意见书
- [ ] `/scholar/essay01/` 有栏目眉「仅经合规审核　不配发蝗掠指数」，**无**摘要框与审稿意见书
- [ ] 页脚有常驻投稿栏 `buno.dev/locustjournal`
- [ ] 移动端（375px）导航独占一行、可横向滑动、右缘有渐隐提示
- [ ] `/nope-404/` 返回期刊语气的 404 页（404 · 蝗迹未存）

**可选 · 视觉审计**（13 路由 × 桌面/移动双视口）：

```bash
hugo --gc --minify
/Users/dynooob/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  -m http.server 1313 --bind 127.0.0.1 --directory public &
NODE_PATH=/Users/dynooob/.workbuddy/binaries/node/workspace/node_modules \
  OUT=/tmp/lj-audit \
  /Users/dynooob/.workbuddy/binaries/node/versions/22.22.2/bin/node tools/visual_audit.js
# 截图落在 $OUT/，报告为 report.json
# 期望：横向溢出 = 0、低对比度 = 0
```

> 审计报告里有两类**已知误报**，不用管：
> - `livereload.js` 404 —— `hugo server` 的调试脚本，静态 `public/` 与生产环境都没有
> - `/nope-404/` 404 —— 那就是 404 页本身，预期行为

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

## Step 3 · Cloudflare Workers 部署

### 为什么是 Workers，不是 Pages

Cloudflare 已停止推荐 Pages（不再维护），官方现在把纯静态站也导向
**Workers with Static Assets**。Hugo 官方部署文档（`gohugo.io/host-and-deploy/host-on-cloudflare/`）
给的就是这条路。

**两者对本站没有成本差异**：静态请求在 Pages 和 Workers 上都免费。
所以 Dashboard 里那个提示 `npx wrangler deploy` 的面板**就是正确路线**，不用退出去。

仓库根已备好两个文件，Dashboard 会自动读取：

| 文件 | 作用 |
|------|------|
| `wrangler.jsonc` | 项目名、构建命令、静态资源目录、404 行为 |
| `build.sh` | 下载固定版本 Hugo（Extended）→ 拉 submodule → 构建 → 校验产物 |

### Dashboard 操作步骤

1. 登录 <https://dash.cloudflare.com>
2. 左侧 **Compute & AI** → **Workers & Pages**
3. **Create application** → **Connect to Git** → 选 `Locust-Journal/locustjournal`
4. 项目名填 `locustjournal`（须与 `wrangler.jsonc` 的 `name` 一致）
5. **Build command** 填 `npx wrangler deploy`
6. **Deploy**

> ⚠️ 这里必须是 `npx wrangler deploy`，**不要**改成 `chmod +x build.sh && ./build.sh`。
>
> Dashboard 的 **Build command** 只负责「跑构建」，产物**不会**被自动上传。
> 早前填成 `build.sh` 时，构建日志全绿（27 个 HTML 页面、图标闭环校验全过），
> 但线上返回的是 Cloudflare 脚手架默认的 `Hello world` —— 仅 11 字节、
> `content-type: text/plain`。
>
> `npx wrangler deploy` 会自己先执行 `wrangler.jsonc` 里的
> `build.command`（即 `build.sh`）完成构建，再把 `public/` 作为静态资源推上线。
> **一个入口同时负责构建与上传，不会递归。**
>
> 反面教材：不要在 `build.sh` 末尾调 `wrangler deploy` —— wrangler 会再读
> `build.command` 调回 `build.sh`，无限递归。也不存在 `wrangler deploy --skip-build`
> 这个参数（跳过打包的开关叫 `--no-bundle`，且它跳的是打包不是自定义构建）。

构建通常 1–3 分钟（首次要下载 Hugo 约 30MB）。

### 若需要环境变量

Dashboard → Settings → Builds & deployments → Variables and secrets：

| 名称 | 值 | 环境 |
|------|-----|------|
| `NODE_VERSION` | `22` | Production |

> 本项目不需要 `HUGO_VERSION` 环境变量 —— `build.sh` 里已经把版本钉死
> （`HUGO_VERSION="0.167.0"`）并直接下载二进制，比依赖构建镜像预装版本更可靠。

### 验证

```bash
BASE=https://locustjournal.com      # 或部署后拿到的 workers.dev 地址

curl -sI $BASE | head -1                                    # 期望 HTTP/2 200
curl -s $BASE/ | grep -o 'Speeches fade, snacks remain'     # 应有输出
curl -s $BASE/ | grep -o 'LOCUST JOURNAL'                   # 刊头是否渲染
curl -s -o /dev/null -w '%{http_code}\n' $BASE/articles/vol1/article01/  # 200
curl -s -o /dev/null -w '%{http_code}\n' $BASE/assets/pdf/vol1/article01.pdf  # 200
curl -s -o /dev/null -w '%{http_code}\n' $BASE/nonexistent/  # 期望 404（自定义 404 页）
```

### build.sh 的自检机制

脚本在构建后会逐个检查关键产物，缺任何一个就 `exit 1` 终止部署：

```
public/index.html
public/sitemap.xml
public/robots.txt
public/css/extended.css          ← 缺这个说明 submodule 没拉下来
public/articles/index.html
public/articles/vol1/article01/index.html
public/articles/vol1/article02/index.html
public/scholar/index.html
public/archive/index.html
public/assets/pdf/vol1/article01.pdf
public/assets/pdf/vol1/article02.pdf
public/assets/images/favicon.png
```

**设计意图**：宁可部署失败，也不要出现「构建成功但样式全丢」的假象 ——
后者在 Dashboard 上显示为绿色成功，等到发现时已经上线了。

---

---

## Step 4 · 绑定自定义域名

> Workers 绑定域名的位置与 Pages 不同：不在 Pages 的 Custom domains，
> 而在 Worker 项目的 **Settings → Domains & Routes → Add → Custom domain**。

1. 打开 Worker 项目 `locustjournal` → **Settings** → **Domains & Routes**
2. **Add** → **Custom domain** → 输入 `locustjournal.com` → **Add domain**
3. 域名已在 Cloudflare DNS 时，Cloudflare 自动添加记录，无需手动改 DNS
4. 等待证书签发（通常几分钟）

> `wrangler.jsonc` 里已设 `"workers_dev": false`，所以不会生成
> `locustjournal.<subdomain>.workers.dev` 临时域名，避免搜索引擎收录重复站点。

**验证证书**：

```bash
echo | openssl s_client -servername locustjournal.com -connect locustjournal.com:443 2>/dev/null \
  | openssl x509 -noout -dates -subject
```

### www → 主域 301

- **Rules → Redirect Rules → Single Redirect**
- 条件：`http.host eq "www.locustjournal.com"`
- 目标：`https://locustjournal.com` + **Pass query string** + **Always HTTPS**

```bash
curl -sI https://www.locustjournal.com | head -3    # 期望 301 → https://locustjournal.com/
curl -sI https://locustjournal.com | head -1        # 期望 200
```

> ⚠️ 本项目的 `baseURL` 已固定为 `https://locustjournal.com/`（见 `config.toml`），
> 所以**不需要**为换域名重新构建 —— 站内链接从一开始就是主域绝对地址。
> 若将来改域名，才需要改 `config.toml` 的 `baseURL` 并重新部署。

---

## Step 5 · 上线后验证

```bash
BASE=https://locustjournal.com

for p in / /about/ /guide/ /articles/ /articles/vol1/ \
         /articles/vol1/article01/ /articles/vol1/article02/ \
         /scholar/ /scholar/essay01/ \
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
| **构建日志全绿，线上却是 `Hello world`** | Build command 填成了 `build.sh` —— 它只构建、不上传，产物没推上去 | 改成 `npx wrangler deploy`（它会自己调 `build.command` 再上传）。自查：`curl -sI 站点 \| grep content-type` 若不是 `text/html` 就是这个问题 |
| 本地 `npx wrangler deploy` 报 `cannot execute binary file`（exit 126） | `build.sh` 曾硬编码下载 linux-amd64 的 Hugo，macOS 跑不了 | 已修：`build.sh` 改为按 `uname` 自动探测 darwin-arm64 / linux-amd64 |
| 本地 dry-run 报 curl exit 56 | 到 GitHub Release 的网络被中断 | 与脚本无关，Cloudflare 构建机可正常下载；本地验证可改用已装的 hugo |
| 线上白屏，无样式 | submodule 未拉取，CSS 缺失 | 查构建日志有无「初始化 git submodule」段；`build.sh` 也会因缺 CSS 直接失败 |
| 404 返回 Cloudflare 默认页而非期刊 404 页 | `assets.not_found_handling` 没生效 | 核对 `wrangler.jsonc` 里是 `"404-page"` |
| Hugo 下载失败导致部署失败 | 网络问题 | Cloudflare 会自动重试；也可把 Hugo 装进构建镜像 |
| 构建因 warning 失败 | 远端 Hugo 版本与本地有差异 | `build.sh` 已刻意不加 `--panicOnWarning`；若你在 Dashboard 另填了命令，去掉该参数 |
| 搜到两个重复站点 | `workers.dev` 临时域名没关 | 确认 `wrangler.jsonc` 里 `"workers_dev": false` |
| 中文显示方块 | 字体栈缺中文回退 | 见下方「中文字体」 |
| 导航某项缺失 | `pageRef` 与实际文件不符 | 核对 `content/` 下文件名 |
| 提交后线上没更新 | 分支不是 `main` | 核对 Production branch |

### 中文字体

站点已在 `assets/css/extended/locust-journal.css` 里配好中文优先字体栈
（PingFang SC → Hiragino Sans GB → Microsoft YaHei → Noto Sans CJK SC）。
如需调整字体，直接改该文件，**不要动 `themes/`**。

### 提交新稿件的完整流程

```bash
# 1. 新增 content/articles/volN/articleNN.md，填好 front matter
#    （title / titleEn / authors / affiliation / seq / page /
#      locust_index / review / verdict / pdf）
#    目录页、首页要目、归档总目会自动收录，不用改模板

# 2. 重新生成 PDF
/Users/dynooob/.workbuddy/binaries/python/envs/default/bin/python tools/make_pdf.py

# 3. 本地严格验证
hugo --gc --minify --panicOnWarning && echo "构建 OK"

# 4. 提交（需明确指示）
git add -A && git commit -m "content: 第 N 卷新增 M 篇" && git push

# 5. Cloudflare Workers 自动检测 push 并重建，无需手动触发
#    查看：Dashboard → Workers & Pages → locustjournal → Deployments
```

---

## 目录速查

```text
locustjournal/
├── config.toml              # 站点配置（改这里）
├── wrangler.jsonc           # Cloudflare Workers 配置（项目名 / 构建 / 静态目录 / 404）
├── build.sh                 # CI 构建脚本（下 Hugo → 拉 submodule → 构建 → 校验产物）
├── DEPLOY.md                # 本文件
├── README.md                # 项目说明
├── content/                 # 所有内容
│   ├── _index.md  about.md  guide.md  board.md  archive.md
│   ├── articles/            # 蝗札（双盲评审 + 蝗掠指数）
│   │   └── vol1/            # 卷期目录
│   └── scholar/             # 蝗客学社（仅合规审核）
├── layouts/                 # 覆盖主题模板（不改 themes/）
│   ├── index.html           # 首页：封面 + 本卷要目
│   ├── imprint.html         # 刊务公告页
│   ├── archive.html         # 总归档
│   ├── taxonomy.html        # 主题索引
│   ├── 404.html
│   ├── baseof.html          # 修 Hugo 0.158+ 废弃字段
│   ├── rss.xml
│   ├── _default/
│   │   ├── single.html      # 蝗札单篇
│   │   └── list.html        # 栏目目录 / 词条页
│   ├── scholar/single.html  # 学社随笔（独立版式）
│   ├── _partials/
│   │   ├── footer.html      # 页脚 + 投稿栏
│   │   └── templates/opengraph.html
├── assets/css/extended/locust-journal.css   # 全部期刊样式
├── static/assets/
│   ├── images/              # favicon 全套 + logo + locust.svg
│   └── pdf/vol1/            # 稿件 PDF（由 tools/make_pdf.py 生成）
├── themes/PaperMod/         # 主题（submodule，勿直接改）
└── tools/
    ├── make_pdf.py          # Markdown → 排版 PDF
    └── visual_audit.js      # Playwright 视觉审计
```

**改主题样式的正确姿势**：不要直接编辑 `themes/PaperMod/`，更新主题时会被冲掉。
用 `assets/css/extended/locust-journal.css` 或项目根 `layouts/` 覆盖。
