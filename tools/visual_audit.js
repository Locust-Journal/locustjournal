// LOCUST Journal 视觉审计脚本
// 逐页截图 + 计算样式探针（对比度 / 溢出 / 隐藏元素 / 资源 404）
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = process.env.BASE || 'http://127.0.0.1:1313';
const OUT = process.env.OUT || '/tmp/locust-audit';

const ROUTES = [
  { path: '/', name: '01-home' },
  { path: '/about/', name: '02-about' },
  { path: '/guide/', name: '03-guide' },
  { path: '/articles/', name: '04-articles' },
  { path: '/articles/vol1/', name: '05-vol1' },
  { path: '/articles/vol1/article01/', name: '06-article01' },
  { path: '/articles/vol1/article02/', name: '07-article02' },
  { path: '/scholar/', name: '08-scholar' },
  { path: '/scholar/essay01/', name: '09-essay01' },
  { path: '/board/', name: '10-board' },
  { path: '/archive/', name: '11-archive' },
  { path: '/tags/', name: '12-tags' },
  { path: '/nope-404/', name: '13-404' },
];

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'mobile', width: 375, height: 812 },
];

// ---- WCAG 亮度与对比度 ----
function lum(rgb) {
  const c = rgb.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contrast(fg, bg) {
  const L1 = lum(fg), L2 = lum(bg);
  return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
}
const parseRgb = (s) => (s.match(/\d+(\.\d+)?/g) || []).slice(0, 3).map(Number);

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const report = [];

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 2,
    });
    const page = await ctx.newPage();

    // 收集资源加载失败
    const failed = [];
    page.on('response', (r) => { if (r.status() >= 400) failed.push(`${r.status()} ${r.url()}`); });
    page.on('pageerror', (e) => failed.push(`JS-ERROR ${e.message}`));

    for (const r of ROUTES) {
      failed.length = 0;
      await page.goto(BASE + r.path, { waitUntil: 'networkidle' });
      await page.waitForTimeout(250);

      const file = path.join(OUT, `${vp.name}-${r.name}.png`);
      await page.screenshot({ path: file, fullPage: vp.name === 'desktop' });

      // 计算样式探针
      const probe = await page.evaluate(() => {
        // 注意：以下两个函数必须定义在页面上下文内，Node 作用域的同名函数不可用
        const lum = (rgb) => {
          const c = rgb.map((v) => {
            const s = v / 255;
            return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
          });
          return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
        };
        const ratio = (fg, bg) => {
          const L1 = lum(fg), L2 = lum(bg);
          return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
        };
        const prgb = (s) => (String(s).match(/\d+(\.\d+)?/g) || []).slice(0, 3).map(Number);

        const out = { contrast: [], overflow: null, hidden: [], fontFamily: null, lang: document.documentElement.lang, dataTheme: document.documentElement.getAttribute('data-theme') };

        // 主题字体栈
        out.fontFamily = getComputedStyle(document.body).fontFamily;

        // 横向溢出
        const de = document.documentElement;
        out.overflow = { scrollW: de.scrollWidth, clientW: de.clientWidth, bodyScrollW: document.body.scrollWidth };
        if (de.scrollWidth > de.clientWidth + 2) {
          const wide = [];
          document.querySelectorAll('body *').forEach((el) => {
            const r = el.getBoundingClientRect();
            if (r.width > de.clientWidth + 4 || r.right > de.clientWidth + 4) {
              wide.push(`${el.tagName.toLowerCase()}.${(el.className || '').toString().split(' ')[0]} w=${Math.round(r.width)} right=${Math.round(r.right)}`);
            }
          });
          out.wideElements = wide.slice(0, 8);
        }

        // 关键文本对比度（走祖先链找有效背景）
        const effBg = (el) => {
          let n = el;
          while (n && n !== document.documentElement) {
            const bg = getComputedStyle(n).backgroundColor;
            if (bg && !/rgba?\(0,\s*0,\s*0,\s*0\)|transparent/.test(bg)) {
              const p = prgb(bg);
              if (p.length === 3) return p;
            }
            n = n.parentElement;
          }
          return [255, 255, 255];
        };

        const targets = [
          ['正文', '.post-content p, .content p'],
          ['导航链接', '.menu a, nav a'],
          ['标题 h1', 'h1'],
          ['标题 h2', 'h2'],
          ['页脚', '.footer, footer'],
          ['引用块', 'blockquote, .post-content blockquote'],
          ['表格单元', 'td, th'],
          ['链接', '.post-content a'],
        ];
        targets.forEach(([label, sel]) => {
          const el = document.querySelector(sel);
          if (!el) return;
          const cs = getComputedStyle(el);
          const fg = prgb(cs.color);
          const bg = effBg(el);
          if (fg.length === 3 && bg.length === 3) {
            out.contrast.push({ label, fg: cs.color, bg: `rgb(${bg.join(',')})`, fontSize: cs.fontSize, ratio: +ratio(fg, bg).toFixed(2) });
          }
        });

        // 零尺寸 / 隐藏但可见的容器
        document.querySelectorAll('main *').forEach((el) => {
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          if (cs.display !== 'none' && cs.visibility !== 'hidden' && (r.width === 0 || r.height === 0) && el.textContent.trim().length > 3) {
            out.hidden.push(`${el.tagName.toLowerCase()}.${(el.className || '').toString().split(' ')[0]} "${el.textContent.trim().slice(0, 30)}"`);
          }
        });
        out.hidden = out.hidden.slice(0, 5);
        return out;
      });

      report.push({ viewport: vp.name, route: r.path, file, probe, failed: [...failed] });
      process.stdout.write(`[${vp.name}] ${r.path.padEnd(38)} `);
      const bad = failed.filter((f) => !f.includes('favicon'));
      const lowC = probe.contrast.filter((c) => c.ratio < 4.5 && parseFloat(c.fontSize) >= 16);
      const of = probe.overflow.scrollW > probe.overflow.clientW + 2;
      console.log(`res=${bad.length} overflow=${of ? 'YES' : 'no'} lowContrast=${lowC.length} ${probe.lang}/${probe.dataTheme}`);
    }
    await ctx.close();
  }

  await browser.close();
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));

  // 汇总
  console.log('\n================ 审计汇总 ================');
  let issues = 0;
  for (const r of report) {
    const bad = r.failed.filter((f) => !f.includes('favicon'));
    const of = r.probe.overflow.scrollW > r.probe.overflow.clientW + 2;
    const lowC = r.probe.contrast.filter((c) => c.ratio < 4.5 && parseFloat(c.fontSize) >= 16);
    if (bad.length || of || lowC.length || r.probe.hidden.length) {
      issues++;
      console.log(`\n⚠ ${r.viewport} ${r.route}`);
      if (bad.length) console.log('   资源失败:', bad.join(' | '));
      if (of) console.log(`   横向溢出: scrollW=${r.probe.overflow.scrollW} clientW=${r.probe.overflow.clientW}`, r.probe.wideElements || '');
      lowC.forEach((c) => console.log(`   低对比(${c.label}): ${c.ratio}:1  ${c.fontSize}  ${c.fg} on ${c.bg}`));
      if (r.probe.hidden.length) console.log('   零尺寸元素:', r.probe.hidden.join(' | '));
    }
  }
  if (!issues) console.log('无问题 ✓');
  console.log(`\n共 ${report.length} 个页面×视口组合，问题项 ${issues} 个`);
  console.log('报告：' + path.join(OUT, 'report.json'));
})();
