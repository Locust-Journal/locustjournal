#!/usr/bin/env bash
#==============================================================================
# LOCUST Journal · Cloudflare Workers 构建脚本
#------------------------------------------------------------------------------
# 由 wrangler.jsonc 的 build.command 调用：chmod +x build.sh && ./build.sh
#
# 为什么要这个脚本：Cloudflare 的 Workers 构建镜像不带 Hugo，
# 而 Hugo 的版本直接决定构建产物是否与本地一致。本项目用 0.167.0
# （Extended 版，必须 —— 非 Extended 不支持 SCSS 且与本地产物不一致）。
#
# 版本策略：显式下载并校验，不依赖构建镜像里预装的任何工具。
# 网络中断时脚本立即失败，不会产出一个「构建成功但资源全丢」的假象。
#==============================================================================

# 出错即停：未定义变量、管道失败、命令失败都立即退出
set -euo pipefail

# 固定工具版本 —— 与本地开发环境保持一致
HUGO_VERSION="0.167.0"
TZ_BUILD="Asia/Shanghai"

# 构建缓存目录（放仓库内，利用 Cloudflare 的目录缓存加速重复构建）
HUGO_CACHEDIR="${PWD}/.cache/hugo"

#------------------------------------------------------------------------------
# 清理钩子：无论成败都删掉临时下载目录，避免残留到构建产物里
#------------------------------------------------------------------------------
build_temp_dir=""
cleanup() {
  if [[ -n "${build_temp_dir}" && -d "${build_temp_dir}" ]]; then
    rm -rf "${build_temp_dir}"
  fi
}
trap cleanup EXIT SIGINT SIGTERM

#------------------------------------------------------------------------------
# 准备环境
#------------------------------------------------------------------------------
echo "==> 设置构建时区与缓存目录"
export TZ="${TZ_BUILD}"
export HUGO_CACHEDIR

mkdir -p "${HUGO_CACHEDIR}" "${HOME}/.local"

#------------------------------------------------------------------------------
# 解析当前平台对应的 Hugo 发行资产名
#
# 这里不能简单按 uname 拼 "${os}-${arch}"：Hugo 官方并不提供全平台矩阵。
# 以 0.167.0 为例，extended 包在 Linux/Windows 有 tar.gz/zip，
# 但在 macOS 只有 hugo_extended_<ver>_darwin-universal.pkg —— 没有
# darwin-amd64、也没有 darwin-arm64 资产。早前"按 uname 自动探测"的
# 写法在 macOS 上拼出 darwin-arm64，URL 返回 404，脚本直接死在那。
#------------------------------------------------------------------------------
hugo_is_extended() {
  # 参数是 hugo 可执行文件路径；判定标准是版本串里的 "+extended"
  [[ -x "$1" ]] && "$1" version 2>/dev/null | grep -q "v${HUGO_VERSION}.*+extended"
}

hugo_asset_name() {
  local os arch
  case "$(uname -s)" in
    Linux)  os="linux" ;;
    Darwin) os="darwin" ;;
    *) echo "不支持的操作系统：$(uname -s)" >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64|amd64)  arch="amd64" ;;
    arm64|aarch64) arch="arm64" ;;
    *) echo "不支持的 CPU 架构：$(uname -m)" >&2; exit 1 ;;
  esac

  if [[ "${os}" == "darwin" ]]; then
    # macOS 仅有 universal .pkg
    echo "hugo_extended_${HUGO_VERSION}_darwin-universal.pkg"
  else
    echo "hugo_extended_${HUGO_VERSION}_${os}-${arch}.tar.gz"
  fi
}

#------------------------------------------------------------------------------
# 安装 Hugo
#
# 优先复用缓存目录里已装好的版本；macOS 上退而使用 PATH 里已有的 hugo
#（Homebrew 装的即是 +extended），都拿不到才从官方下载。
#------------------------------------------------------------------------------
HUGO_BIN_DIR="${HOME}/.local/hugo/bin"
HUGO_BIN="${HUGO_BIN_DIR}/hugo"
export PATH="${HUGO_BIN_DIR}:${PATH}"

if hugo_is_extended "${HUGO_BIN}"; then
  echo "==> Hugo ${HUGO_VERSION} (extended) 已就绪，跳过下载"
elif [[ "$(uname -s)" == "Darwin" ]] && command -v hugo >/dev/null 2>&1 && hugo_is_extended "$(command -v hugo)"; then
  HUGO_BIN="$(command -v hugo)"
  echo "==> 使用系统已安装的 Hugo（${HUGO_BIN}）"
else
  HUGO_ASSET="$(hugo_asset_name)"
  HUGO_URL="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/${HUGO_ASSET}"
  echo "==> 下载 Hugo ${HUGO_VERSION} (extended, ${HUGO_ASSET})"
  build_temp_dir="$(mktemp -d)"

  # curl -sfL 失败时只返回非零状态码、不输出任何诊断信息。这里补一层
  # 显式检查：把 HTTP 状态和 URL 一起打出来，否则脚本会在这一步悄无声息
  # 地死掉，而外层若还接着管道（./build.sh | tail），退出码会被管道末端的
  # 命令覆盖成 0 —— "下载失败"就被伪装成了"构建成功"。
  http_code=$(curl -sSL --retry 3 --retry-delay 2 \
    -w '%{http_code}' -o "${build_temp_dir}/${HUGO_ASSET}" "${HUGO_URL}" || echo "000")
  if [[ "${http_code}" != "200" ]]; then
    echo "    下载失败：HTTP ${http_code} ← ${HUGO_URL}" >&2
    echo "    若为 404，通常是 Hugo 该版本没有此平台的发行资产，" >&2
    echo "    请对照 https://github.com/gohugoio/hugo/releases/tag/v${HUGO_VERSION} 核对。" >&2
    exit 1
  fi

  mkdir -p "${HUGO_BIN_DIR}"
  case "${HUGO_ASSET}" in
    *.tar.gz)
      # tar 内是 hugo（单文件），解出来放进专用目录
      tar -C "${HUGO_BIN_DIR}" -xzf "${build_temp_dir}/${HUGO_ASSET}" hugo
      ;;
    *.pkg)
      # .pkg 是 xar 归档，Payload 内部再是一层 gzip cpio，取出 hugo 可执行文件
      echo "    解包 .pkg 并提取 hugo 可执行文件"
      (
        cd "${build_temp_dir}"
        xar -xf "${HUGO_ASSET}"
        mkdir -p payload-out
        # Payload 的 cpio 条目名是 ./hugo
        cat Payload | gzip -dc | cpio -idmv --quiet ./hugo 2>/dev/null
      )
      if [[ -f "${build_temp_dir}/hugo" ]]; then
        mv "${build_temp_dir}/hugo" "${HUGO_BIN}"
      else
        # 部分版本的包名带版本号目录，回退到全量提取
        (
          cd "${build_temp_dir}"
          cat Payload | gzip -dc | cpio -idm --quiet
        )
        found_hugo=$(find "${build_temp_dir}" -type f -name hugo -perm -u+x -not -path '*/Payload*' | head -1)
        [[ -n "${found_hugo}" ]] || { echo "    .pkg 内未找到 hugo 可执行文件" >&2; exit 1; }
        mv "${found_hugo}" "${HUGO_BIN}"
      fi
      ;;
  esac
  chmod +x "${HUGO_BIN}"

  if ! hugo_is_extended "${HUGO_BIN}"; then
    echo "    安装后的 hugo 版本或类型不符（需要 v${HUGO_VERSION} +extended）" >&2
    "${HUGO_BIN}" version >&2 || true
    exit 1
  fi
fi

#------------------------------------------------------------------------------
# 记录工具版本（构建日志里留痕，便于排查线上白屏类问题）
#------------------------------------------------------------------------------
echo "==> 工具版本"
"${HUGO_BIN}" version

#------------------------------------------------------------------------------
# Git 配置
#------------------------------------------------------------------------------
echo "==> 配置 Git"
git config --global core.quotepath false
git config --global --add safe.directory "${PWD}"

# Cloudflare 的浅克隆会导致 Hugo 找不到某些文件，显式补全历史
if [[ "$(git rev-parse --is-shallow-repository 2>/dev/null || echo false)" == "true" ]]; then
  echo "==> 仓库是浅克隆，拉取完整历史"
  git fetch --unshallow || echo "    （拉取失败不影响构建，继续）"
fi

#------------------------------------------------------------------------------
# 初始化 git submodule —— themes/PaperMod 是 submodule
#
# 这一步失败会导致「找不到主题」，症状是页面能出但样式全丢。
#------------------------------------------------------------------------------
if [[ -f .gitmodules ]]; then
  echo "==> 初始化 git submodule（themes/PaperMod）"
  git submodule update --init --recursive
fi

#------------------------------------------------------------------------------
# 构建
#
# 注意：不加 --panicOnWarning。
# 构建镜像里的 Hugo 若与本地有细微版本差异，严格模式会因无害的
# deprecation warning 直接让整站部署失败。本地自己用严格模式把关。
#------------------------------------------------------------------------------
echo "==> 构建 Hugo 站点"
"${HUGO_BIN}" --gc --minify

#------------------------------------------------------------------------------
# 构建后自检 —— 防止「构建成功但产物不完整」被当成成功部署
#------------------------------------------------------------------------------
echo "==> 校验构建产物"

required_files=(
  "public/index.html"
  "public/sitemap.xml"
  "public/robots.txt"
  "public/articles/index.html"
  "public/articles/vol1/article01/index.html"
  "public/articles/vol1/article02/index.html"
  "public/scholar/index.html"
  "public/scholar/essay01/index.html"
  "public/archive/index.html"
  "public/assets/pdf/vol1/article01.pdf"
  "public/assets/pdf/vol1/article02.pdf"
  # 图标在站点根（static/ 根 → 产物根路径），与 PaperMod 的引用约定一致。
  # 早前图标放在 static/assets/images/ 而 HTML 引用 /images/，线上图标全 404，
  # 校验路径也写错了 —— 现在以「HTML 引用」为准校验产物。
  "public/favicon.png"
  "public/favicon-16x16.png"
  "public/favicon-32x32.png"
  "public/favicon.ico"
  "public/apple-touch-icon.png"
  "public/safari-pinned-tab.svg"
)

missing=0
for f in "${required_files[@]}"; do
  if [[ ! -f "${f}" ]]; then
    echo "    缺少产物：${f}" >&2
    missing=1
  fi
done

# 样式检查：PaperMod 把主题样式与 assets/css/extended/ 合并成一个带内容哈希的
# 单文件（public/assets/css/stylesheet.<hash>.css），文件名每次构建都变，
# 所以不能写死路径，只能判断「至少存在一个 CSS 产物」。
#
# 这是最常见的静默故障：themes/PaperMod submodule 没拉下来时，Hugo 不报错、
# 页面照常生成，只是样式全丢 —— 而 Dashboard 上还会显示构建成功。
css_count=$(find public -name "*.css" -type f 2>/dev/null | wc -l | tr -d ' ')
if [[ "${css_count}" -eq 0 ]]; then
  echo "    样式文件缺失 —— 检查 themes/PaperMod submodule 是否拉取成功" >&2
  missing=1
else
  echo "    样式产物 ${css_count} 个"
fi

if [[ "${missing}" -ne 0 ]]; then
  echo "构建产物不完整，终止部署。" >&2
  exit 1
fi

#------------------------------------------------------------------------------
# 图标引用闭环检查
#
# 只校验「文件存在」是不够的：本项目曾出现图标放在 static/assets/images/、
# 而 HTML 引用 /images/favicon.png 的错位 —— 文件都在，校验能过，
# 但线上每个页面的图标全是 404。
#
# 这里反向解析首页里真实引用的图标 URL，确认它在 public/ 下确实存在。
#------------------------------------------------------------------------------
echo "==> 校验图标引用闭环"
icon_broken=0
while IFS= read -r icon_url; do
  # https://locustjournal.com/favicon.ico → public/favicon.ico
  rel_path="${icon_url#https://locustjournal.com/}"
  rel_path="${rel_path%%\?*}"
  [[ -z "${rel_path}" ]] && continue
  if [[ ! -f "public/${rel_path}" ]]; then
    echo "    图标引用指向不存在的产物：${rel_path}" >&2
    icon_broken=1
  fi
done < <(grep -oE 'rel=(icon|apple-touch-icon|mask-icon)[^>]*href=https://locustjournal\.com/[^ >]*' \
         public/index.html | grep -oE 'href=https://[^ >]*' | cut -d= -f2- | sort -u)

if [[ "${icon_broken}" -ne 0 ]]; then
  echo "图标引用与产物不一致，终止部署。" >&2
  exit 1
fi
echo "    图标引用全部命中产物"

# 404 页必须存在，否则 not_found_handling: "404-page" 无页可返回
if [[ ! -f "public/404.html" ]]; then
  echo "    缺少 404 页 —— assets.not_found_handling 将回落到默认错误页" >&2
fi

page_count=$(find public -name "*.html" -type f | wc -l | tr -d ' ')
echo "==> 构建完成：${page_count} 个 HTML 页面"
echo "==> 输出目录：public/"

#------------------------------------------------------------------------------
# 刊名标语覆盖检查
#
# 站点辨识度要求：每一页都能看到刊名与标语。历史事故是清理旧标语时
# 用过宽的正则，把三个自定义刊头（列表页 / 归档页 / 主题索引页）里的
# motto 段落整段删掉却没补新的，构建照常通过，只有肉眼翻页才发现缺标语。
#
# 例外：404 页用的是一句改写过的标语（「蝗虫识字，只赴茶歇。但这一页…」），
# 英文标语本就缺席，不纳入本项检查。
#------------------------------------------------------------------------------
echo "==> 校验刊名标语覆盖"
motto_missing=0
while IFS= read -r page; do
  rel="${page#public/}"
  if ! grep -q '蝗虫识字，只赴茶歇' "${page}"; then
    echo "    缺中文标语：${rel}" >&2
    motto_missing=1
  fi
  if ! grep -q 'Locusts can read' "${page}"; then
    echo "    缺英文标语：${rel}" >&2
    motto_missing=1
  fi
done < <(find public -name "*.html" -type f ! -name "404.html")

# 旧标语必须彻底清零，避免两版标语同时出现在站点上
stale=$(grep -rliE 'Speeches fade, snacks remain|报告转瞬即逝，茶歇亘古长存' public 2>/dev/null || true)
if [[ -n "${stale}" ]]; then
  echo "    仍存在旧标语残留：${stale}" >&2
  motto_missing=1
fi

if [[ "${motto_missing}" -ne 0 ]]; then
  echo "刊名标语覆盖不完整，终止部署。" >&2
  exit 1
fi
echo "    全部页面均含刊名与标语"

# 本脚本只负责「构建」，不负责「上传」。
# 上传由 `wrangler deploy` 统一完成：它会先执行 wrangler.jsonc 里的
# build.command（即本脚本）构建，再把 public/ 作为静态资源推上线。
#
# 反面教材（两个都踩过）：
#   1. 在本脚本末尾调 `wrangler deploy` → wrangler 再读 build.command
#      调回本脚本 → 无限递归。
#   2. 想用 `wrangler deploy --skip-build` 规避递归 → 该参数根本不存在。
#      跳过打包的开关叫 --no-bundle，且它跳的是打包，不是自定义构建。
#
# 早前的症状：构建日志全绿（27 个 HTML 页面、图标闭环校验通过），
# 但线上返回 Cloudflare 脚手架默认的 "Hello world"，仅 11 字节、
# content-type: text/plain。原因是只构建、没上传。
