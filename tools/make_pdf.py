#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOCUST Journal 稿件 PDF 生成器
================================
把 content/articles/vol1/*.md 渲染为带中文字体支持的排版 PDF，
输出到 static/assets/pdf/vol1/。

用法：
    /Users/dynooob/.workbuddy/binaries/python/envs/default/bin/python tools/make_pdf.py

依赖：reportlab（已装在隔离 venv）
字体：优先用系统中文字体（PingFang / Songti / STHeiti），均找不到时回退到内置 CJK 字体。
"""
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "content", "articles", "vol1")
OUT_DIR = os.path.join(ROOT, "static", "assets", "pdf", "vol1")

ACCENT = colors.HexColor("#b45309")
INK = colors.HexColor("#18181b")
MUTED = colors.HexColor("#71717a")
RULE = colors.HexColor("#d4d4d8")
QUOTE_BG = colors.HexColor("#fafaf9")

# ---- 字体注册 -----------------------------------------------------------

def register_cjk_font():
    """注册一个可显示中文的字体，返回 (regular, bold) 字体名。"""
    candidates = [
        # (regular_path, bold_path, name_prefix)
        ("/System/Library/Fonts/PingFang.ttc",
         "/System/Library/Fonts/PingFang.ttc", "PingFang"),
        ("/System/Library/Fonts/STHeiti Light.ttc",
         "/System/Library/Fonts/STHeiti Medium.ttc", "STHeiti"),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc",
         "/System/Library/Fonts/Hiragino Sans GB.ttc", "HiraginoSansGB"),
        ("/Library/Fonts/Arial Unicode.ttf",
         "/Library/Fonts/Arial Unicode.ttf", "ArialUnicode"),
    ]
    for reg, bold, name in candidates:
        if not os.path.exists(reg):
            continue
        try:
            # TTC 需要指定子表索引；PingFang.ttc 索引 1 为常规、4 为 Semibold
            if reg.endswith(".ttc"):
                pdfmetrics.registerFont(TTFont(name, reg, subfontIndex=1))
                if bold.endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont(name + "-Bold", bold, subfontIndex=4))
                else:
                    pdfmetrics.registerFont(TTFont(name + "-Bold", reg, subfontIndex=1))
            else:
                pdfmetrics.registerFont(TTFont(name, reg))
                pdfmetrics.registerFont(TTFont(name + "-Bold", bold))
            return name, name + "-Bold"
        except Exception as exc:  # noqa: BLE001
            print(f"  ! 字体 {name} 注册失败：{exc}", file=sys.stderr)
    # 回退：reportlab 内置 CJK（CID，无需外部字体文件）
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light", "STSong-Light"


# ---- Markdown 解析（够用即可，不追求完整 CommonMark）-------------------

def read_front_matter(text):
    """拆出 YAML front matter，返回 (meta, body)。"""
    meta = {}
    if not text.startswith("---"):
        return meta, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return meta, text
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, parts[2]


def parse_blocks(body):
    """把 Markdown 正文切成块列表。块类型：
    ('h2', text) ('h3', text) ('p', text) ('quote', text)
    ('ul', [items]) ('table', [rows]) ('code', text) ('hr', None)
    """
    lines = body.splitlines()
    blocks, buf, i = [], [], 0

    def flush_p():
        if buf:
            text = " ".join(x.strip() for x in buf).strip()
            if text:
                blocks.append(("p", text))
            buf.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_p(); i += 1; continue

        if stripped == "---":
            flush_p(); blocks.append(("hr", None)); i += 1; continue

        if stripped.startswith("### "):
            flush_p(); blocks.append(("h3", stripped[4:].strip())); i += 1; continue

        if stripped.startswith("## "):
            flush_p(); blocks.append(("h2", stripped[3:].strip())); i += 1; continue

        if stripped.startswith("# "):
            flush_p(); blocks.append(("h2", stripped[2:].strip())); i += 1; continue

        # 围栏代码块
        if stripped.startswith("```"):
            flush_p(); i += 1; code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            i += 1
            blocks.append(("code", "\n".join(code)))
            continue

        # 表格
        if stripped.startswith("|"):
            flush_p()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                # 跳过 |---| 分隔行
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows))
            continue

        # 引用块
        if stripped.startswith(">"):
            flush_p()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(("quote", " ".join(q for q in quote if q)))
            continue

        # 无序列表
        if re.match(r"^[-*+]\s+", stripped):
            flush_p()
            items = []
            while i < len(lines) and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[i]).strip())
                i += 1
            blocks.append(("ul", items))
            continue

        # 有序列表
        if re.match(r"^\d+\.\s+", stripped):
            flush_p()
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip())
                i += 1
            blocks.append(("ul", items))
            continue

        buf.append(line); i += 1

    flush_p()
    return blocks


def inline_markup(text):
    """处理行内 Markdown → reportlab 富文本标签。"""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 行内代码
    text = re.sub(r"`([^`]+)`", r'<font face="Courier" size="9">\1</font>', text)
    # 粗体
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # 斜体
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


# ---- 渲染 ---------------------------------------------------------------

def build_pdf(md_path, out_path, reg_font, bold_font):
    raw = open(md_path, encoding="utf-8").read()
    meta, body = read_front_matter(raw)
    blocks = parse_blocks(body)

    title = meta.get("title", "Untitled")
    authors = meta.get("authors", "").strip("[]\"'")
    locust_index = meta.get("locust_index", "")
    date = meta.get("date", "")
    vol = meta.get("vol", "")

    doc = BaseDocTemplate(
        out_path, pagesize=A4,
        leftMargin=25 * mm, rightMargin=25 * mm,
        topMargin=22 * mm, bottomMargin=20 * mm,
        title=title, author="LOCUST Journal Editorial Board",
        subject="LOCUST Journal《学术蝗虫》内测号",
    )

    # 样式
    s_title = ParagraphStyle("t", fontName=bold_font, fontSize=19, leading=27,
                              alignment=TA_CENTER, textColor=INK, spaceAfter=4)
    s_meta = ParagraphStyle("m", fontName=reg_font, fontSize=9.5, leading=15,
                            alignment=TA_CENTER, textColor=MUTED, spaceAfter=2)
    s_kicker = ParagraphStyle("k", fontName=bold_font, fontSize=10, leading=16,
                              alignment=TA_CENTER, textColor=ACCENT, spaceAfter=6)
    s_h2 = ParagraphStyle("h2", fontName=bold_font, fontSize=14, leading=22,
                          textColor=INK, spaceBefore=14, spaceAfter=7)
    s_h3 = ParagraphStyle("h3", fontName=bold_font, fontSize=11.5, leading=18,
                          textColor=ACCENT, spaceBefore=10, spaceAfter=5)
    s_body = ParagraphStyle("b", fontName=reg_font, fontSize=10, leading=17.5,
                            alignment=TA_JUSTIFY, textColor=INK, spaceAfter=6)
    s_quote = ParagraphStyle("q", fontName=reg_font, fontSize=9.5, leading=16,
                             textColor=colors.HexColor("#52525b"), leftIndent=8,
                             rightIndent=8, spaceBefore=4, spaceAfter=4)
    s_code = ParagraphStyle("c", fontName="Courier", fontSize=8.5, leading=13,
                            textColor=colors.HexColor("#3f3f46"), leftIndent=8,
                            backColor=colors.HexColor("#f4f4f5"), borderPadding=6)
    s_cell = ParagraphStyle("cl", fontName=reg_font, fontSize=8.5, leading=13, textColor=INK)
    s_cellb = ParagraphStyle("cb", fontName=bold_font, fontSize=8.5, leading=13, textColor=INK)
    s_footnote = ParagraphStyle("fn", fontName=reg_font, fontSize=8.5, leading=14,
                                textColor=MUTED, spaceBefore=8)

    story = []

    # 刊头
    story.append(Paragraph("LOCUST Journal《学术蝗虫》", s_kicker))
    story.append(Paragraph(inline_markup(title), s_title))
    if vol:
        story.append(Paragraph(f"第 {vol} 卷 · 内测号", s_meta))
    if authors:
        story.append(Paragraph(inline_markup(authors), s_meta))
    if locust_index:
        story.append(Paragraph(f"蝗掠指数（Locust Index）{locust_index} / 10", s_meta))
    if date:
        story.append(Paragraph(date, s_meta))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.8, color=RULE))
    story.append(Spacer(1, 10))

    # 正文
    for kind, payload in blocks:
        if kind == "h2":
            story.append(Paragraph(inline_markup(payload), s_h2))
        elif kind == "h3":
            story.append(Paragraph(inline_markup(payload), s_h3))
        elif kind == "p":
            story.append(Paragraph(inline_markup(payload), s_body))
        elif kind == "quote":
            quote_par = Paragraph(inline_markup(payload), s_quote)
            tbl = Table([[quote_par]], colWidths=[160 * mm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), QUOTE_BG),
                ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story += [tbl, Spacer(1, 8)]
        elif kind == "ul":
            for n, item in enumerate(payload, 1):
                story.append(Paragraph(f"• {inline_markup(item)}",
                                       ParagraphStyle("li", parent=s_body,
                                                      leftIndent=14, firstLineIndent=-8)))
            story.append(Spacer(1, 4))
        elif kind == "code":
            code_par = Paragraph(
                payload.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>"),
                s_code)
            story.append(code_par)
            story.append(Spacer(1, 6))
        elif kind == "table":
            if not payload:
                continue
            ncol = max(len(r) for r in payload)
            data = []
            for ri, row in enumerate(payload):
                cells = []
                for ci in range(ncol):
                    txt = inline_markup(row[ci]) if ci < len(row) else ""
                    cells.append(Paragraph(txt, s_cellb if ri == 0 else s_cell))
                data.append(cells)
            colw = 160 * mm / ncol
            tbl = Table(data, colWidths=[colw] * ncol, repeatRows=1, hAlign="LEFT")
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f4f5")),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story += [tbl, Spacer(1, 8)]
        elif kind == "hr":
            story += [Spacer(1, 4), HRFlowable(width="100%", thickness=0.5, color=RULE), Spacer(1, 8)]

    # 免责声明尾页
    story.append(Spacer(1, 14))
    disclaimer = Paragraph(
        "<b>免责声明</b>：本刊为娱乐模拟学术刊物，不具备正式出版资质，"
        "所刊内容无学术效力，不得用于学位申请、职称评定与项目申报。"
        "本刊永久免费，不收取任何版面费、审稿费与处理费。",
        s_footnote)
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE))
    story.append(disclaimer)

    # 页脚
    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont(reg_font, 7.5)
        canvas.setFillColor(MUTED)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(25 * mm, 14 * mm, A4[0] - 25 * mm, 14 * mm)
        canvas.drawString(25 * mm, 9.5 * mm, "LOCUST Journal《学术蝗虫》· 内测号 · 无学术效力")
        canvas.drawRightString(A4[0] - 25 * mm, 9.5 * mm, f"{doc_.page}")
        canvas.restoreState()

    frame = Frame(25 * mm, 20 * mm, A4[0] - 50 * mm, A4[1] - 42 * mm, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    doc.build(story)
    return out_path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    reg, bold = register_cjk_font()
    print(f"字体：{reg} / {bold}")

    targets = [f for f in sorted(os.listdir(SRC_DIR))
               if f.endswith(".md") and not f.startswith("_")]
    if not targets:
        print("没有找到稿件", file=sys.stderr)
        return 1

    for fname in targets:
        src = os.path.join(SRC_DIR, fname)
        dst = os.path.join(OUT_DIR, fname.replace(".md", ".pdf"))
        build_pdf(src, dst, reg, bold)
        size = os.path.getsize(dst)
        print(f"✓ {fname}  →  {os.path.relpath(dst, ROOT)}  ({size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
