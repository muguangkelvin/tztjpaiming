import os
import json
import re
import html
import shutil
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
DATA_DIR = os.path.join(ROOT_DIR, "data")
CONTENT_DIR = os.path.join(ROOT_DIR, "content")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

SEO_PROFILE = load_json(os.path.join(ROOT_DIR, "site-seo-profile.json"))
PROVIDERS = load_json(os.path.join(DATA_DIR, "providers.json"))

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def parse_markdown(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    
    front_matter = {}
    content = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            content = parts[2].strip()
            for line in fm_text.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if v.startswith("[") and v.endswith("]"):
                        v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                    front_matter[k] = v
    return front_matter, content

def parse_inline_md(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    
    def link_replacer(m):
        label = m.group(1)
        url = m.group(2)
        if "code=" in url or "aff" in url or "vip" in url or ("http" in url and "tztjpaiming.xyz" not in url):
            return f'<a href="{url}" target="_blank" rel="sponsored nofollow noopener" class="aff-link">{label}</a>'
        return f'<a href="{url}">{label}</a>'

    text = re.sub(r"\[(.*?)\]\((.*?)\)", link_replacer, text)
    return text

def simple_markdown_to_html(md_text):
    lines = md_text.split("\n")
    html_out = []
    in_list = False
    list_type = "ul"
    in_table = False
    table_rows = []
    in_code_block = False
    code_block_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Code block handling (```)
        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                code_content = html.escape("\n".join(code_block_lines))
                html_out.append(f'<div class="code-container"><pre class="mana-code-block"><code>{code_content}</code></pre></div>')
                code_block_lines = []
            else:
                in_code_block = True
                code_block_lines = []
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        # Table handling
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(stripped)
            continue
        elif in_table:
            in_table = False
            html_out.append('<div class="table-container"><table class="mana-table">')
            header_done = False
            for r_idx, r in enumerate(table_rows):
                cols = [c.strip() for c in r.strip("|").split("|")]
                if r_idx == 1 and all(set(c) <= set("-: ") for c in cols):
                    header_done = True
                    continue
                tag = "th" if not header_done else "td"
                html_out.append("<tr>" + "".join(f"<{tag}>{parse_inline_md(c)}</{tag}>" for c in cols) + "</tr>")
            html_out.append('</table></div>')
            table_rows = []

        if not stripped or stripped in ("---", "***", "___") or (len(stripped) >= 3 and set(stripped) <= {"-", "*", "_"}):
            if in_list:
                html_out.append(f"</{list_type}>")
                in_list = False
            continue

        if stripped.startswith("#### "):
            html_out.append(f"<h4>{parse_inline_md(stripped[5:])}</h4>")
        elif stripped.startswith("### "):
            html_out.append(f"<h3>{parse_inline_md(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html_out.append(f"<h2>{parse_inline_md(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html_out.append(f"<h1>{parse_inline_md(stripped[2:])}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_out.append("<ul>")
                in_list = True
                list_type = "ul"
            html_out.append(f"<li>{parse_inline_md(stripped[2:])}</li>")
        elif re.match(r"^\d+\.\s", stripped):
            item_text = re.sub(r"^\d+\.\s", "", stripped)
            if not in_list:
                html_out.append("<ol>")
                in_list = True
                list_type = "ol"
            html_out.append(f"<li>{parse_inline_md(item_text)}</li>")
        elif stripped.startswith("> "):
            html_out.append(f"<blockquote class=\"mana-callout\">{parse_inline_md(stripped[2:])}</blockquote>")
        else:
            if in_list:
                html_out.append(f"</{list_type}>")
                in_list = False
            html_out.append(f"<p>{parse_inline_md(stripped)}</p>")

    if in_code_block and code_block_lines:
        code_content = html.escape("\n".join(code_block_lines))
        html_out.append(f'<div class="code-container"><pre class="mana-code-block"><code>{code_content}</code></pre></div>')

    if in_table and table_rows:
        html_out.append('<div class="table-container"><table class="mana-table">')
        header_done = False
        for r_idx, r in enumerate(table_rows):
            cols = [c.strip() for c in r.strip("|").split("|")]
            if r_idx == 1 and all(set(c) <= set("-: ") for c in cols):
                header_done = True
                continue
            tag = "th" if not header_done else "td"
            html_out.append("<tr>" + "".join(f"<{tag}>{parse_inline_md(c)}</{tag}>" for c in cols) + "</tr>")
        html_out.append('</table></div>')

    if in_list:
        html_out.append(f"</{list_type}>")

    return "\n".join(html_out)

def render_mana_page(title, description, canonical, content_html, active_nav="", extra_head="", breadcrumbs=None, show_sidebar=True):
    nav_html = ""
    nav_items = [
        {"label": "综合排名榜", "url": "/posts/ranking/"},
        {"label": "客户端指南", "url": "/posts/clients/"},
        {"label": "测速与排错", "url": "/posts/speed-test-guide/"},
        {"label": "自营专线通道", "url": "/service/"},
        {"label": "服务状态", "url": "/status/"},
        {"label": "FAQ 知识库", "url": "/faq/"}
    ]
    for item in nav_items:
        current_attr = ' aria-current="page" class="active"' if item.get("url") == active_nav else ''
        nav_html += f'<li><a href="{item["url"]}"{current_attr}>{item["label"]}</a></li>\n'

    bc_html = ""
    if breadcrumbs:
        bc_items = ['<li><a href="/">首页</a></li>']
        for b_title, b_url in breadcrumbs:
            if b_url:
                bc_items.append(f'<li><a href="{b_url}">{b_title}</a></li>')
            else:
                bc_items.append(f'<li><span>{b_title}</span></li>')
        bc_html = f'<nav class="breadcrumbs" aria-label="面包屑"><ul>{"".join(bc_items)}</ul></nav>'

    year = datetime.now().year

    # Mana Sidebar Widget
    sidebar_html = """
    <aside class="mana-sidebar">
        <div class="sidebar-widget status-widget">
            <div class="widget-header">
                <span class="status-indicator live"></span>
                <h3>服务实时状态</h3>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted);">已完成 2026-09-23 节点复核：所有中转与 28 家机场订阅响应正常 (SLA 99.9%)。</p>
            <a href="/status/" class="widget-link">查看完整状态日志 →</a>
        </div>

        <div class="sidebar-widget promo-widget">
            <div class="widget-header">
                <span class="badge badge-indigo">自营推荐</span>
                <h3>自营专线通道</h3>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted);">全球多出口 BGP + IPLC 独享带宽，保障跨境团队与生产力办公连通。</p>
            <div style="margin-top: 0.75rem;">
                <a href="/service/" class="btn btn-primary btn-sm block-btn">了解自营通道</a>
                <a href="https://varnexa.lingdongaff.com/#/?code=JoIy7bO1" target="_blank" rel="sponsored nofollow noopener" class="btn btn-secondary btn-sm block-btn" style="margin-top: 0.4rem;">灵动云 8折优惠码: ld88</a>
            </div>
        </div>

        <div class="sidebar-widget">
            <div class="widget-header">
                <h3>TOP 4 严选榜单</h3>
            </div>
            <ul class="top4-quick-list">
                <li><span class="rank-num">1</span> <a href="/providers/lingdong/">灵动云 (LingDong Cloud)</a></li>
                <li><span class="rank-num">2</span> <a href="/providers/twilight/">暮光网络 (Twilight)</a></li>
                <li><span class="rank-num">3</span> <a href="/providers/flycat-cloud/">飞猫云 (FlyCat Cloud)</a></li>
                <li><span class="rank-num">4</span> <a href="/providers/breezenet/">微风网络 (Breezenet)</a></li>
            </ul>
        </div>

        <div class="sidebar-widget">
            <div class="widget-header">
                <h3>FAQ 知识库</h3>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted);">包含 100 个关于 Clash / Shadowrocket / Sing-box 及协议排错的解答。</p>
            <a href="/faq/" class="widget-link">浏览 100 FAQ 问答 →</a>
        </div>
    </aside>
    """

    main_layout = f"""
    <div class="mana-layout">
        <div class="mana-main-content">
            {content_html}
        </div>
        {sidebar_html if show_sidebar else ''}
    </div>
    """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description)}">
    <link rel="canonical" href="{canonical}">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{html.escape(title)}">
    <meta property="og:description" content="{html.escape(description)}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:site_name" content="梯子推荐排名网 (Mana Theme)">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="alternate" type="application/rss+xml" title="梯子推荐排名网 RSS Feed" href="https://tztjpaiming.xyz/index.xml">
    <style>
        :root {{
            --bg-color: #0f172a;
            --surface-color: #1e293b;
            --surface-border: #334155;
            --text-color: #e2e8f0;
            --text-muted: #94a3b8;
            --heading-color: #f8fafc;
            --primary-color: #6366f1;
            --primary-hover: #818cf8;
            --accent-green: #22c55e;
            --accent-amber: #f59e0b;
            --code-bg: #090d16;
            --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
            --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: var(--font-sans);
            line-height: 1.7;
            font-size: 16px;
        }}
        .container {{
            max-width: 1140px;
            margin: 0 auto;
            padding: 0 1.25rem;
        }}
        header.site-header {{
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--surface-border);
            position: sticky;
            top: 0;
            z-index: 100;
            padding: 0.75rem 0;
            margin-bottom: 2rem;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        .logo-area {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .logo a {{
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--heading-color);
            text-decoration: none;
            letter-spacing: -0.02em;
        }}
        .logo span {{ color: var(--primary-color); }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-indigo {{ background: rgba(99, 102, 241, 0.15); color: var(--primary-color); border: 1px solid rgba(99, 102, 241, 0.3); }}
        .badge-green {{ background: rgba(34, 197, 94, 0.15); color: var(--accent-green); border: 1px solid rgba(34, 197, 94, 0.3); }}
        
        nav.main-nav ul {{
            display: flex;
            list-style: none;
            gap: 1rem;
            flex-wrap: wrap;
        }}
        nav.main-nav a {{
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            padding: 0.4rem 0.6rem;
            border-radius: 6px;
            transition: all 0.2s;
        }}
        nav.main-nav a:hover, nav.main-nav a.active {{
            color: var(--heading-color);
            background: var(--surface-border);
        }}

        .header-search-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
            margin-top: 0.85rem;
            padding-top: 0.85rem;
            border-top: 1px solid var(--surface-border);
        }}
        .header-search-container {{
            flex: 1;
            min-width: 280px;
        }}
        .header-search-form {{
            display: flex;
            align-items: center;
        }}
        .search-input-wrapper {{
            position: relative;
            display: flex;
            align-items: center;
            background: var(--bg-color);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 0.35rem 0.65rem;
            gap: 0.5rem;
            width: 100%;
            max-width: 540px;
            transition: all 0.2s;
        }}
        .search-input-wrapper:focus-within {{
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
        }}
        .search-dropdown {{
            position: absolute;
            top: calc(100% + 8px);
            left: 0;
            right: 0;
            background: #0f172a;
            border: 1px solid var(--surface-border);
            border-radius: 10px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
            z-index: 1000;
            max-height: 420px;
            overflow-y: auto;
            padding: 0.75rem;
            text-align: left;
        }}
        .search-dropdown.hidden {{ display: none !important; }}
        .search-dropdown-header {{
            display: flex;
            justify-content: space-between;
            font-size: 0.78rem;
            color: var(--text-muted);
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--surface-border);
            margin-bottom: 0.5rem;
        }}
        .search-close-btn {{ cursor: pointer; color: var(--text-muted); }}
        .search-close-btn:hover {{ color: var(--heading-color); }}
        .search-result-item {{
            display: block;
            padding: 0.6rem 0.75rem;
            border-radius: 6px;
            text-decoration: none !important;
            transition: background 0.15s;
            margin-bottom: 0.25rem;
            border: 1px solid transparent;
        }}
        .search-result-item:hover {{
            background: rgba(99, 102, 241, 0.15);
            border-color: rgba(99, 102, 241, 0.3);
        }}
        .search-result-title {{
            font-weight: 600;
            font-size: 0.88rem;
            color: var(--heading-color);
            margin-bottom: 0.2rem;
            display: flex;
            align-items: center;
        }}
        .search-result-badge {{
            font-size: 0.7rem;
            padding: 0.1rem 0.35rem;
            border-radius: 4px;
            margin-right: 0.45rem;
            font-weight: 600;
            white-space: nowrap;
            display: inline-block;
        }}
        .search-result-badge.badge-post {{ background: rgba(99, 102, 241, 0.2); color: var(--primary-color); }}
        .search-result-badge.badge-provider {{ background: rgba(34, 197, 94, 0.2); color: var(--accent-green); }}
        .search-result-badge.badge-faq {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; }}
        .search-result-badge.badge-topic {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; }}
        .search-result-desc {{
            font-size: 0.78rem;
            color: var(--text-muted);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .search-no-results {{
            padding: 1.5rem 1rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        .search-icon {{
            color: var(--text-muted);
            flex-shrink: 0;
        }}
        .search-input-wrapper input {{
            background: transparent;
            border: none;
            outline: none;
            color: var(--heading-color);
            font-size: 0.875rem;
            width: 100%;
        }}
        .search-submit-btn {{
            background: var(--primary-color);
            color: #ffffff;
            border: none;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: background 0.2s;
        }}
        .search-submit-btn:hover {{
            background: var(--primary-hover);
        }}
        .search-tags {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            flex-wrap: wrap;
            margin-top: 0.5rem;
            font-size: 0.78rem;
            color: var(--text-muted);
        }}
        .search-tag-label {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            color: var(--heading-color);
            font-weight: 600;
        }}
        .search-tags a {{
            color: var(--text-muted);
            text-decoration: none;
            padding: 0.15rem 0.45rem;
            background: var(--surface-color);
            border-radius: 4px;
            border: 1px solid var(--surface-border);
            transition: all 0.2s;
        }}
        .search-tags a:hover {{
            color: var(--primary-color);
            border-color: var(--primary-color);
            background: rgba(99, 102, 241, 0.1);
        }}

        .header-social-buttons {{
            display: flex;
            align-items: center;
            gap: 0.65rem;
        }}
        .social-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.85rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none !important;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .social-btn svg {{
            flex-shrink: 0;
        }}
        .tg-btn {{
            background: rgba(36, 161, 222, 0.12);
            color: #24A1DE;
            border: 1px solid rgba(36, 161, 222, 0.3);
        }}
        .tg-btn:hover {{
            background: rgba(36, 161, 222, 0.25);
            color: #38b5f3;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(36, 161, 222, 0.2);
        }}
        .github-btn {{
            background: rgba(255, 255, 255, 0.08);
            color: var(--heading-color);
            border: 1px solid var(--surface-border);
        }}
        .github-btn:hover {{
            background: rgba(255, 255, 255, 0.16);
            color: #ffffff;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(255, 255, 255, 0.1);
        }}

        .breadcrumbs {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 1.5rem;
        }}
        .breadcrumbs ul {{
            display: flex;
            list-style: none;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .breadcrumbs li::after {{ content: "/"; margin-left: 0.5rem; color: var(--surface-border); }}
        .breadcrumbs li:last-child::after {{ content: ""; }}
        .breadcrumbs a {{ color: var(--text-muted); text-decoration: none; }}
        .breadcrumbs a:hover {{ color: var(--primary-color); }}

        /* Mana Two-Column Layout */
        .mana-layout {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }}
        @media (min-width: 900px) {{
            .mana-layout {{
                grid-template-columns: 1fr 300px;
            }}
        }}

        h1, h2, h3, h4 {{ color: var(--heading-color); font-weight: 700; margin-top: 1.8rem; margin-bottom: 0.8rem; line-height: 1.3; }}
        h1 {{ font-size: 2.1rem; letter-spacing: -0.02em; border-bottom: 1px solid var(--surface-border); padding-bottom: 0.6rem; }}
        h2 {{ font-size: 1.5rem; border-bottom: 1px solid var(--surface-border); padding-bottom: 0.4rem; }}
        h3 {{ font-size: 1.25rem; }}
        p {{ margin-bottom: 1.2rem; }}
        a {{ color: var(--primary-color); text-decoration: none; }}
        a:hover {{ text-decoration: underline; color: var(--primary-hover); }}
        ul, ol {{ margin-bottom: 1.2rem; padding-left: 1.5rem; }}
        li {{ margin-bottom: 0.4rem; }}
        blockquote.mana-callout {{
            border-left: 4px solid var(--primary-color);
            padding: 0.75rem 1.25rem;
            color: var(--text-color);
            background: var(--surface-color);
            border-radius: 0 8px 8px 0;
            margin-bottom: 1.25rem;
        }}
        code {{
            font-family: var(--font-mono);
            background: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.875em;
            color: #f1f5f9;
        }}

        /* Code Block & Decision Tree Styles */
        .code-container {{
            margin-bottom: 1.5rem;
            overflow-x: auto;
        }}
        pre.mana-code-block {{
            background: #090d16;
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 1.25rem;
            color: #f1f5f9;
            font-family: var(--font-mono);
            font-size: 0.875rem;
            line-height: 1.5;
            white-space: pre;
            overflow-x: auto;
        }}

        .decision-tree-container {{
            background: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.75rem;
        }}
        .decision-step-title {{
            font-weight: 700;
            font-size: 1.05rem;
            color: var(--heading-color);
            margin-bottom: 1rem;
        }}
        .decision-tree-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
        }}
        .decision-card {{
            background: var(--bg-color);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            overflow: hidden;
        }}
        .decision-header {{
            background: rgba(99, 102, 241, 0.15);
            color: var(--primary-color);
            font-weight: 700;
            font-size: 0.875rem;
            padding: 0.6rem 0.85rem;
            border-bottom: 1px solid var(--surface-border);
        }}
        .decision-body {{
            padding: 0.85rem;
        }}
        .decision-badge {{
            display: inline-block;
            background: rgba(34, 197, 94, 0.15);
            color: var(--accent-green);
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            margin-bottom: 0.4rem;
        }}
        .decision-body h4 {{
            margin-top: 0.2rem;
            margin-bottom: 0.4rem;
            font-size: 1rem;
        }}
        .decision-body p {{
            font-size: 0.825rem;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
        }}
        .decision-actions {{
            display: flex;
            gap: 0.5rem;
        }}

        .table-container {{
            overflow-x: auto;
            margin-bottom: 1.5rem;
        }}
        table.mana-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.92rem;
        }}
        table.mana-table th, table.mana-table td {{
            padding: 0.75rem;
            border: 1px solid var(--surface-border);
        }}
        table.mana-table th {{
            background: var(--surface-color);
            color: var(--heading-color);
        }}
        table.mana-table tr:nth-child(even) {{
            background: rgba(255,255,255,0.02);
        }}

        /* Hero & Banner */
        .hero-banner {{
            background: linear-gradient(135deg, rgba(30, 41, 59, 1) 0%, rgba(15, 23, 42, 1) 100%);
            border: 1px solid var(--surface-border);
            border-radius: 12px;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }}
        .hero-banner h1 {{ border-bottom: none; padding-bottom: 0; font-size: 1.85rem; margin-top: 0; }}
        .hero-desc {{ font-size: 0.98rem; color: var(--text-muted); margin-top: 0.75rem; margin-bottom: 1.25rem; }}
        .hero-cta {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 1rem; }}
        
        .btn {{
            display: inline-block;
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            font-weight: 600;
            text-decoration: none !important;
            font-size: 0.9rem;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .btn-sm {{ padding: 0.4rem 0.8rem; font-size: 0.825rem; }}
        .btn-primary {{ background: var(--primary-color); color: #ffffff; }}
        .btn-primary:hover {{ background: var(--primary-hover); }}
        .btn-secondary {{ background: var(--surface-color); color: var(--heading-color); border: 1px solid var(--surface-border); }}
        .btn-secondary:hover {{ background: var(--surface-border); }}
        .block-btn {{ display: block; text-align: center; width: 100%; }}

        /* Mana Sidebar Components */
        .sidebar-widget {{
            background: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
        }}
        .widget-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }}
        .widget-header h3 {{ margin: 0; font-size: 1.1rem; color: var(--heading-color); }}
        .status-indicator {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}
        .status-indicator.live {{ background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }}
        .widget-link {{ font-size: 0.85rem; font-weight: 600; display: inline-block; margin-top: 0.5rem; }}

        .top4-quick-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .top4-quick-list li {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.4rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .top4-quick-list li:last-child {{ border-bottom: none; }}
        .rank-num {{
            background: var(--primary-color);
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 700;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .provider-card {{
            background: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
        }}
        .provider-card.primary-rank {{
            border-color: rgba(99, 102, 241, 0.5);
            background: linear-gradient(180deg, rgba(30, 41, 59, 1) 0%, rgba(15, 23, 42, 0.6) 100%);
        }}
        .provider-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }}
        .provider-rank {{
            background: var(--primary-color);
            color: #ffffff;
            font-weight: 700;
            font-family: var(--font-mono);
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        .provider-name {{ font-size: 1.3rem; font-weight: 700; color: var(--heading-color); }}
        .provider-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.75rem;
            font-size: 0.875rem;
            background: rgba(0,0,0,0.25);
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.75rem;
        }}
        .provider-actions {{
            display: flex;
            gap: 0.75rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}

        .article-card {{
            background: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }}
        .article-card h3 {{ margin-top: 0; font-size: 1.15rem; }}

        footer.site-footer {{
            background: var(--surface-color);
            border-top: 1px solid var(--surface-border);
            padding: 2.5rem 0;
            margin-top: 4rem;
            font-size: 0.875rem;
            color: var(--text-muted);
        }}
        .footer-keywords {{
            background: var(--bg-color);
            padding: 1.25rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            border: 1px solid var(--surface-border);
        }}
        .footer-links {{
            display: flex;
            gap: 1.25rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
            list-style: none;
            padding: 0;
        }}
        .footer-links a {{ color: var(--text-muted); }}
        .footer-links a:hover {{ color: var(--primary-color); }}

        .pagination {{
            display: flex;
            gap: 0.5rem;
            margin-top: 2rem;
            justify-content: center;
            list-style: none;
            padding: 0;
        }}
        .pagination a, .pagination span {{
            padding: 0.4rem 0.8rem;
            background: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 6px;
            color: var(--text-color);
            text-decoration: none;
        }}
        .pagination .active {{
            background: var(--primary-color);
            color: #ffffff;
            font-weight: bold;
        }}
    </style>
    {extra_head}
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div class="header-top">
                <div class="logo-area">
                    <div class="logo">
                        <a href="/">2026年 <span>梯子推荐排名</span></a>
                    </div>
                    <span class="badge badge-indigo">Hugo Extended + Mana</span>
                    <span class="badge badge-green">28 节点正常</span>
                </div>
                <nav class="main-nav" aria-label="主导航">
                    <ul>
                        {nav_html}
                    </ul>
                </nav>
            </div>
            <div class="header-search-row">
                <div class="header-search-container">
                    <form class="header-search-form" action="/faq/" method="get" onsubmit="return handleSiteSearch(event)">
                        <div class="search-input-wrapper">
                            <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                            <input type="text" id="site-search-input" name="q" autocomplete="off" placeholder="搜索 2026 梯子、Clash / Shadowrocket 配置、IPLC 专线与全站 150+ 文章..." />
                            <button type="submit" class="search-submit-btn">搜索</button>
                            <div id="search-results-dropdown" class="search-dropdown hidden">
                                <div class="search-dropdown-header">
                                    <span>全站关联文章匹配 (<strong id="search-count">0</strong>)</span>
                                    <span class="search-close-btn" onclick="closeSearchDropdown()">&times; Esc 关闭</span>
                                </div>
                                <div id="search-results-list" class="search-results-list"></div>
                            </div>
                        </div>
                    </form>
                    <div class="search-tags">
                        <span class="search-tag-label">
                            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                            搜索关联词：
                        </span>
                        <a href="/posts/2026-tizi-tuijian-paiming-zonghe-henping/">2026 梯子排名</a>
                        <a href="/posts/ai-gongju-mofa-shangwang-jidian-xuanze/">ChatGPT 解锁</a>
                        <a href="/posts/clash-verge-rev-peizhi-jiaocheng/">Clash Verge 教程</a>
                        <a href="/posts/ios-tizi-xuangou-shadowrocket-quantumult-x/">iOS 小火箭</a>
                        <a href="/posts/iplc-zhuanxian-vs-bgp-zhongji-jishu-henping/">IPLC 专线</a>
                    </div>
                </div>
                <div class="header-social-buttons">
                    <a href="https://t.me/+6fo_zU8PHKVlMzZl" target="_blank" rel="noopener noreferrer" class="social-btn tg-btn" title="Telegram 官方频道">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.02-1.96 1.25-5.54 3.69-.52.36-1 .54-1.43.53-.47-.01-1.37-.26-2.05-.48-.83-.27-1.49-.42-1.43-.88.03-.24.37-.49 1.02-.74 3.99-1.74 6.66-2.89 8.01-3.45 3.81-1.59 4.6-.19 4.6.43 0 .15-.02.31-.05.47z"/>
                        </svg>
                        <span>TG 频道</span>
                    </a>
                    <a href="https://github.com" target="_blank" rel="noopener noreferrer" class="social-btn github-btn" title="GitHub 官方代码库">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                            <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
                        </svg>
                        <span>GitHub</span>
                    </a>
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        {bc_html}
        <main id="main-content">
            {main_layout}
        </main>
    </div>

    <footer class="site-footer">
        <div class="container">
            <div class="footer-keywords">
                <p><strong>梯子推荐排名网（Mana 架构）</strong>专注 2026 年梯子推荐排名、纯静态文章与专题博客、教程、评测、FAQ、服务状态与自营专线产品入口。全站继承自营服务推广与转化优先规则。</p>
                <p style="margin-top: 0.5rem; font-size: 0.8rem;">声明：本站提供客观技术评测与节点选型指标对比，含有透明商业合作与邀请链接收益。最后数据核验日期：2026-09-23。</p>
            </div>
            <ul class="footer-links">
                <li><a href="/about/">关于本站</a></li>
                <li><a href="/editorial-policy/">编辑原则</a></li>
                <li><a href="/methodology/">评测方法</a></li>
                <li><a href="/affiliate-disclosure/">联盟披露</a></li>
                <li><a href="/privacy/">隐私政策</a></li>
                <li><a href="/terms/">服务条款</a></li>
                <li><a href="/contact/">联系我们</a></li>
                <li><a href="/status/">服务状态</a></li>
                <li><a href="/coupons/">优惠码汇总</a></li>
                <li><a href="/sitemap.xml">Sitemap</a></li>
                <li><a href="/index.xml">RSS Feed</a></li>
            </ul>
            <p>© {year} 梯子推荐排名网 (tztjpaiming.xyz) · Mana 纯静态文章与专题博客。</p>
    <script>
    var searchIndexData = null;

    function fetchSearchIndex(cb) {{
        if (searchIndexData) {{
            if (cb) cb(searchIndexData);
            return;
        }}
        fetch('/search-index.json')
            .then(function(res) {{ return res.json(); }})
            .then(function(data) {{
                searchIndexData = data;
                if (cb) cb(searchIndexData);
            }})
            .catch(function(err) {{ console.error('Error fetching search index:', err); }});
    }}

    function handleSiteSearch(e) {{
        e.preventDefault();
        var val = document.getElementById('site-search-input').value.trim();
        if (val) {{
            window.location.href = '/faq/?q=' + encodeURIComponent(val);
        }}
        return false;
    }}

    function handleSearchInput(e) {{
        var val = e.target.value.trim().toLowerCase();
        var dropdown = document.getElementById('search-results-dropdown');
        var listContainer = document.getElementById('search-results-list');
        var countEl = document.getElementById('search-count');

        if (!val) {{
            if (dropdown) dropdown.classList.add('hidden');
            return;
        }}

        fetchSearchIndex(function(data) {{
            var terms = val.split(/\\s+/);
            var matches = data.filter(function(item) {{
                var text = (item.title + ' ' + (item.desc || '') + ' ' + (item.category || '') + ' ' + (item.type || '')).toLowerCase();
                return terms.every(function(t) {{ return text.indexOf(t) !== -1; }});
            }});

            if (countEl) countEl.textContent = matches.length;
            if (listContainer) {{
                listContainer.innerHTML = '';
                if (matches.length === 0) {{
                    listContainer.innerHTML = '<div class="search-no-results">未找到与 "' + escapeHtml(val) + '" 相关的文章或教程</div>';
                }} else {{
                    matches.slice(0, 10).forEach(function(item) {{
                        var badgeClass = item.type === '测评' ? 'badge-provider' : (item.type === 'FAQ' ? 'badge-faq' : (item.type === '专题' ? 'badge-topic' : 'badge-post'));
                        var a = document.createElement('a');
                        a.href = item.url;
                        a.className = 'search-result-item';
                        a.innerHTML = '<div class="search-result-title"><span class="search-result-badge ' + badgeClass + '">' + escapeHtml(item.type) + '</span>' + highlightText(item.title, val) + '</div>' +
                                      '<div class="search-result-desc">' + escapeHtml(item.desc || '') + '</div>';
                        listContainer.appendChild(a);
                    }});
                }}
            }}
            if (dropdown) dropdown.classList.remove('hidden');
        }});
    }}

    function escapeHtml(str) {{
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }}

    function highlightText(text, keyword) {{
        var safeText = escapeHtml(text);
        if (!keyword) return safeText;
        var idx = safeText.toLowerCase().indexOf(keyword.toLowerCase());
        if (idx === -1) return safeText;
        var match = safeText.substring(idx, idx + keyword.length);
        return safeText.substring(0, idx) + '<mark style="background: rgba(99,102,241,0.35); color: #ffffff; border-radius: 3px; padding: 0 2px;">' + match + '</mark>' + safeText.substring(idx + keyword.length);
    }}

    function closeSearchDropdown() {{
        var dropdown = document.getElementById('search-results-dropdown');
        if (dropdown) dropdown.classList.add('hidden');
    }}

    document.addEventListener('DOMContentLoaded', function() {{
        var input = document.getElementById('site-search-input');
        if (input) {{
            input.addEventListener('focus', function() {{ fetchSearchIndex(); }});
            input.addEventListener('input', handleSearchInput);
            input.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape') closeSearchDropdown();
            }});
        }}

        document.addEventListener('click', function(e) {{
            var wrapper = document.querySelector('.search-input-wrapper');
            if (wrapper && !wrapper.contains(e.target)) {{
                closeSearchDropdown();
            }}
        }});

        var params = new URLSearchParams(window.location.search);
        var q = params.get('q');
        if (q && input) {{
            input.value = q;
            fetchSearchIndex(function() {{
                handleSearchInput({{ target: input }});
            }});
        }}
    }});
    </script>
</body>
</html>
"""

ALL_URLS = []

def build_site():
    if os.path.exists(PUBLIC_DIR):
        shutil.rmtree(PUBLIC_DIR)
    ensure_dir(PUBLIC_DIR)

    # 1. Homepage
    top4 = PROVIDERS[:4]
    rest = PROVIDERS[4:]

    top4_html = ""
    for p in top4:
        top4_html += f"""
        <div class="provider-card primary-rank">
            <div class="provider-header">
                <span class="provider-rank">No. {p['rank']}</span>
                <span class="provider-name">{html.escape(p['name'])}</span>
                <span style="color: var(--accent-green); font-size: 0.85rem; font-weight: 600;">{html.escape(p.get('priceFrom', ''))}</span>
            </div>
            <p style="font-size: 0.92rem; color: var(--text-color); margin-bottom: 0.5rem;">{html.escape(p.get('summary', ''))}</p>
            <div class="provider-meta">
                <div><strong>流量参考：</strong>{html.escape(p.get('trafficFrom', ''))}</div>
                <div><strong>优惠码：</strong><code>{html.escape(p.get('coupon', '暂无'))}</code></div>
                <div><strong>适用场景：</strong>{html.escape(p.get('suitableFor', ''))}</div>
            </div>
            <div class="provider-actions">
                <a href="/providers/{p['slug']}/" class="btn btn-secondary">查看独立测评</a>
                <a href="{p['inviteURL']}" target="_blank" rel="sponsored nofollow noopener" class="btn btn-primary">{p['ctaText']}</a>
            </div>
        </div>
        """

    rest_rows = ""
    for p in rest:
        rest_rows += f"""
        <tr>
            <td><strong>No. {p['rank']}</strong></td>
            <td><a href="/providers/{p['slug']}/">{html.escape(p['name'])}</a></td>
            <td>{html.escape(p.get('priceFrom', '以结算页为准'))}</td>
            <td>{html.escape(p.get('trafficFrom', '待核验'))}</td>
            <td><code>{html.escape(p.get('coupon', '暂无'))}</code></td>
            <td><a href="{p['inviteURL']}" target="_blank" rel="sponsored nofollow noopener" class="btn btn-secondary btn-sm">查看套餐</a></td>
        </tr>
        """

    table_html = f"""
    <div class="table-container">
        <table class="mana-table">
            <thead>
                <tr>
                    <th>排名</th>
                    <th>服务商名称</th>
                    <th>参考价格</th>
                    <th>流量规格</th>
                    <th>优惠码</th>
                    <th>快速入口</th>
                </tr>
            </thead>
            <tbody>
                {rest_rows}
            </tbody>
        </table>
    </div>
    """

    hero_html = """
    <div class="hero-banner">
        <h1>2026年梯子推荐排名与 Mana 专题选型博客</h1>
        <div class="hero-desc">
            Hugo Extended + Mana 纯静态架构：专注教程、评测、FAQ、服务状态与自营专线产品入口。继承自营服务推广与转化优先规则。
        </div>
        <div style="background: rgba(99, 102, 241, 0.1); border-left: 4px solid var(--primary-color); padding: 0.85rem; border-radius: 6px; font-size: 0.875rem; margin-bottom: 1rem;">
            <strong>Mana 核心评测标准：</strong> 晚高峰丢包率冗余 (SLA)、IP 纯净度与流媒体解锁、跨平台客户端订阅导入兼容性、IPLC/BGP 专线架构与自营通道。
        </div>
        <div class="hero-cta">
            <a href="/posts/ranking/" class="btn btn-primary">查看 2026 梯子推荐排名榜</a>
            <a href="/service/" class="btn btn-secondary">自营专线通道</a>
            <a href="/status/" class="btn btn-secondary">服务实时状态</a>
        </div>
    </div>
    """

    home_content = hero_html + f"""
    <h2>全站固定 TOP 4 商业严选梯子榜单</h2>
    <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.2rem;">编辑部基于多地区节点连通性、晚高峰带宽与高可用 SLA 精选的 4 家主推服务（顺序固定）：</p>
    {top4_html}

    <h2>28 家梯子服务商综合横评对比表</h2>
    <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem;">2026 年最新核验数据，包含价格、流量、优惠码与购买前须知：</p>
    {table_html}

    <h2>Mana 专题分类与教程中心</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
        <div style="background: var(--surface-color); border: 1px solid var(--surface-border); padding: 1.25rem; border-radius: 8px;">
            <h3><a href="/posts/ranking/">梯子推荐排名专栏</a></h3>
            <p style="font-size: 0.85rem; color: var(--text-muted);">榜单打分与对比，吃定商业意图搜索流量。</p>
        </div>
        <div style="background: var(--surface-color); border: 1px solid var(--surface-border); padding: 1.25rem; border-radius: 8px;">
            <h3><a href="/posts/clients/">客户端使用指南</a></h3>
            <p style="font-size: 0.85rem; color: var(--text-muted);">Clash Verge, Shadowrocket, Sing-box 配置教程。</p>
        </div>
        <div style="background: var(--surface-color); border: 1px solid var(--surface-border); padding: 1.25rem; border-radius: 8px;">
            <h3><a href="/posts/speed-test-guide/">测速与排错指南</a></h3>
            <p style="font-size: 0.85rem; color: var(--text-muted);">深入分析延迟、丢包率与实际带宽。</p>
        </div>
        <div style="background: var(--surface-color); border: 1px solid var(--surface-border); padding: 1.25rem; border-radius: 8px;">
            <h3><a href="/faq/">FAQ 100 知识库</a></h3>
            <p style="font-size: 0.85rem; color: var(--text-muted);">全套 100 个常见问答与排错指南。</p>
        </div>
    </div>
    """

    canonical_home = "https://tztjpaiming.xyz/"
    ALL_URLS.append(canonical_home)
    home_rendered = render_mana_page(SEO_PROFILE["titlePatterns"]["home"], SEO_PROFILE["descriptionPatterns"]["home"], canonical_home, home_content, active_nav="/", show_sidebar=True)
    with open(os.path.join(PUBLIC_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(home_rendered)

    # 2. Build Article Pages in content/posts/
    posts_dir = os.path.join(CONTENT_DIR, "posts")
    posts_public_dir = os.path.join(PUBLIC_DIR, "posts")
    ensure_dir(posts_public_dir)

    posts_list = []
    if os.path.exists(posts_dir):
        for fname in os.listdir(posts_dir):
            if fname.endswith(".md"):
                fpath = os.path.join(posts_dir, fname)
                fm, md = parse_markdown(fpath)
                slug = fm.get("slug", fname.replace(".md", ""))
                title = fm.get("title", slug)
                cat = fm.get("category", "综合排名榜")
                desc = fm.get("description", title)
                cta_text = fm.get("ctaText", "阅读全文 →")
                body_html = simple_markdown_to_html(md)

                posts_list.append({"slug": slug, "title": title, "category": cat, "desc": desc, "ctaText": cta_text})

                out_dir = os.path.join(posts_public_dir, slug)
                ensure_dir(out_dir)
                canonical = f"https://tztjpaiming.xyz/posts/{slug}/"
                ALL_URLS.append(canonical)

                bc = [("文章专栏", "/posts/ranking/"), (title, "")]
                rendered = render_mana_page(f"{title} | Mana 专题博客", desc, canonical, body_html, active_nav="/posts/ranking/", breadcrumbs=bc, show_sidebar=True)
                with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)

    # 3. Build Navigation Category Pages
    nav_routes = [
        ("/posts/ranking/", "综合排名榜", "2026 梯子推荐排名榜：高性价比与稳定专线机场对比 | Mana 专题博客", "深入对比2026年各大高性价比魔法上网梯子，涵盖晚高峰带宽冗余度、IP纯净度、IPLC专线与流媒体解锁能力。"),
        ("/posts/clients/", "客户端指南", "主流魔法上网客户端下载、安装与订阅配置全指南 | Mana 专题博客", "跨平台客户端配置教程，涵盖 Windows Clash Verge, macOS Loon/Clash, iOS Shadowrocket, Android Surfboard 及 Sing-box 订阅导入。"),
        ("/posts/speed-test-guide/", "测速与排错", "节点延迟与丢包率分析：测速排错与稳定性指南 | Mana 专题博客", "节点延迟与丢包率分析、测速排错、掉线自动切换与网络丢包深度评测指南。"),
        ("/service/", "自营专线通道", "自营专线高速通道：高 SLA 生产力办公网络保障 | Mana 专题博客", "针对企业跨境团队与高吞吐需求用户，提供独立带宽冗余、99.9% 在线率 SLA 的专线网络通道方案。")
    ]

    for route_url, cat_name, cat_title, cat_desc in nav_routes:
        rel_path = route_url.strip("/")
        route_out_dir = os.path.join(PUBLIC_DIR, rel_path)
        ensure_dir(route_out_dir)

        matching_posts = [p for p in posts_list if p["category"] == cat_name or cat_name in p["category"] or (cat_name == "综合排名榜" and "排名" in p["category"])]
        if not matching_posts:
            matching_posts = posts_list[:6]

        cards_html = ""
        for p in matching_posts:
            cta_btn = html.escape(p.get('ctaText', '阅读全文 →'))
            cards_html += f"""
            <div class="article-card">
                <h3><a href="/posts/{p['slug']}/">{html.escape(p['title'])}</a></h3>
                <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.75rem;">{html.escape(p['desc'])}</p>
                <a href="/posts/{p['slug']}/" class="btn btn-secondary btn-sm">{cta_btn}</a>
            </div>
            """

        cat_html = f"""
        <h1>{html.escape(cat_name)}</h1>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">{html.escape(cat_desc)}</p>
        <div class="articles-grid">
            {cards_html}
        </div>
        """

        canonical = f"https://tztjpaiming.xyz{route_url}"
        ALL_URLS.append(canonical)
        rendered = render_mana_page(cat_title, cat_desc, canonical, cat_html, active_nav=route_url, breadcrumbs=[(cat_name, "")], show_sidebar=True)
        with open(os.path.join(route_out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(rendered)

    # 4. Build 28 Provider Evaluation Pages in content/providers/
    prov_dir = os.path.join(CONTENT_DIR, "providers")
    prov_public_dir = os.path.join(PUBLIC_DIR, "providers")
    ensure_dir(prov_public_dir)

    if os.path.exists(prov_dir):
        for fname in os.listdir(prov_dir):
            if fname.endswith(".md"):
                fpath = os.path.join(prov_dir, fname)
                fm, md = parse_markdown(fpath)
                slug = fm.get("slug", fname.replace(".md", ""))
                title = fm.get("title", slug)
                desc = fm.get("description", title)
                body_html = simple_markdown_to_html(md)

                out_dir = os.path.join(prov_public_dir, slug)
                ensure_dir(out_dir)
                canonical = f"https://tztjpaiming.xyz/providers/{slug}/"
                ALL_URLS.append(canonical)

                bc = [("梯子服务测评", "/"), (title, "")]
                rendered = render_mana_page(f"{title} | Mana 专题博客", desc, canonical, body_html, breadcrumbs=bc, show_sidebar=True)
                with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)

    # 5. Build 100 FAQ Articles & 5 Paginated Listing Pages
    faq_dir = os.path.join(CONTENT_DIR, "faq")
    faq_public_dir = os.path.join(PUBLIC_DIR, "faq")
    ensure_dir(faq_public_dir)

    faq_list = []
    if os.path.exists(faq_dir):
        for fname in sorted(os.listdir(faq_dir)):
            if fname.endswith(".md"):
                fpath = os.path.join(faq_dir, fname)
                fm, md = parse_markdown(fpath)
                slug = fm.get("slug", fname.replace(".md", ""))
                title = fm.get("title", slug)
                cluster = fm.get("cluster", "常见问题")
                body_html = simple_markdown_to_html(md)

                faq_list.append({"slug": slug, "title": title, "cluster": cluster})

                out_dir = os.path.join(faq_public_dir, slug)
                ensure_dir(out_dir)
                canonical = f"https://tztjpaiming.xyz/faq/{slug}/"
                ALL_URLS.append(canonical)

                bc = [("常见问题 FAQ", "/faq/"), (title, "")]
                rendered = render_mana_page(f"{title} | Mana FAQ 知识库", f"常见问题解答：{title}", canonical, body_html, active_nav="/faq/", breadcrumbs=bc, show_sidebar=True)
                with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)

    # Build 5 Paginated FAQ Index Pages
    page_size = 20
    total_faqs = len(faq_list)
    total_pages = (total_faqs + page_size - 1) // page_size

    for page_num in range(1, total_pages + 1):
        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        page_items = faq_list[start_idx:end_idx]

        items_html = ""
        for item in page_items:
            items_html += f"""
            <div class="article-card">
                <span class="badge badge-indigo">{html.escape(item['cluster'])}</span>
                <h3 style="margin-top: 0.5rem;"><a href="/faq/{item['slug']}/">{html.escape(item['title'])}</a></h3>
                <a href="/faq/{item['slug']}/" class="btn btn-secondary btn-sm" style="margin-top: 0.5rem;">查看解答 →</a>
            </div>
            """

        pagination_html = '<ul class="pagination">'
        for p in range(1, total_pages + 1):
            p_url = "/faq/" if p == 1 else f"/faq/page/{p}/"
            active_cls = ' class="active"' if p == page_num else ''
            pagination_html += f'<li><a href="{p_url}"{active_cls}>{p}</a></li>'
        pagination_html += '</ul>'

        faq_index_html = f"""
        <h1>Mana 常见问题解答 FAQ Center (第 {page_num} 页)</h1>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">覆盖 100 个关于梯子选型、Clash / Shadowrocket 配置、SS/Trojan 协议与故障排查的核心问答：</p>
        <div class="faq-grid">
            {items_html}
        </div>
        {pagination_html}
        """

        if page_num == 1:
            canonical = "https://tztjpaiming.xyz/faq/"
            out_file = os.path.join(faq_public_dir, "index.html")
        else:
            canonical = f"https://tztjpaiming.xyz/faq/page/{page_num}/"
            page_out_dir = os.path.join(faq_public_dir, "page", str(page_num))
            ensure_dir(page_out_dir)
            out_file = os.path.join(page_out_dir, "index.html")

        ALL_URLS.append(canonical)
        rendered = render_mana_page(f"常见问题解答 FAQ (第 {page_num} 页) | Mana 专题博客", "100个梯子推荐与魔法上网常见问题解答中心", canonical, faq_index_html, active_nav="/faq/", breadcrumbs=[("FAQ 知识库", "")], show_sidebar=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(rendered)

    # 6. Build Pages in content/pages/
    pages_dir = os.path.join(CONTENT_DIR, "pages")
    if os.path.exists(pages_dir):
        for fname in os.listdir(pages_dir):
            if fname.endswith(".md"):
                fpath = os.path.join(pages_dir, fname)
                fm, md = parse_markdown(fpath)
                slug = fm.get("slug", fname.replace(".md", ""))
                title = fm.get("title", slug)
                body_html = simple_markdown_to_html(md)

                out_dir = os.path.join(PUBLIC_DIR, slug)
                ensure_dir(out_dir)
                canonical = f"https://tztjpaiming.xyz/{slug}/"
                ALL_URLS.append(canonical)

                rendered = render_mana_page(f"{title} | Mana 专题博客", title, canonical, body_html, active_nav=f"/{slug}/", breadcrumbs=[(title, "")], show_sidebar=True)
                with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)

    # 7. Generate Robots.txt, Sitemap.xml, RSS Feed (index.xml)
    with open(os.path.join(PUBLIC_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: https://tztjpaiming.xyz/sitemap.xml\n")

    sitemap_items = ""
    for u in sorted(set(ALL_URLS)):
        sitemap_items += f"""  <url>
    <loc>{u}</loc>
    <lastmod>2026-09-23</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>\n"""

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap_items}</urlset>
"""
    with open(os.path.join(PUBLIC_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    rss_items = ""
    for p in posts_list[:15]:
        rss_items += f"""    <item>
      <title>{html.escape(p['title'])}</title>
      <link>https://tztjpaiming.xyz/posts/{p['slug']}/</link>
      <description>{html.escape(p['desc'])}</description>
      <pubDate>Wed, 23 Sep 2026 00:00:00 +0800</pubDate>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>梯子推荐排名网 (Mana 专题博客)</title>
    <link>https://tztjpaiming.xyz/</link>
    <description>Hugo Extended + Mana 纯静态文章与专题博客；教程、评测、FAQ、服务状态与自营产品入口。</description>
    <language>zh-CN</language>
{rss_items}  </channel>
</rss>
"""
    with open(os.path.join(PUBLIC_DIR, "index.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    # 8. Generate Full-Site Search Index (search-index.json)
    search_index = []

    for p in posts_list:
        search_index.append({
            "title": p["title"],
            "url": f"/posts/{p['slug']}/",
            "desc": p.get("desc", ""),
            "category": p.get("category", "综合排名榜"),
            "type": "文章"
        })

    for p in PROVIDERS:
        search_index.append({
            "title": f"{p['name']} 机场测评：价格、节点与评测须知",
            "url": f"/providers/{p['slug']}/",
            "desc": p.get("summary", ""),
            "category": p.get("suitableFor", "服务测评"),
            "type": "测评"
        })

    for f in faq_list:
        search_index.append({
            "title": f["title"],
            "url": f"/faq/{f['slug']}/",
            "desc": f"常见问题解答：{f['title']}",
            "category": f.get("cluster", "FAQ 知识库"),
            "type": "FAQ"
        })

    for route_url, cat_name, cat_title, cat_desc in nav_routes:
        search_index.append({
            "title": cat_title,
            "url": route_url,
            "desc": cat_desc,
            "category": cat_name,
            "type": "专题"
        })

    with open(os.path.join(PUBLIC_DIR, "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)

    print(f"Mana theme build complete! Total generated HTML pages: {len(ALL_URLS)}, Search Index items: {len(search_index)}")

if __name__ == "__main__":
    build_site()
