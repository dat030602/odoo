# -*- coding: utf-8 -*-
import html
import os
import re
from odoo import http
from odoo.http import request


class ConnectorDocsController(http.Controller):

    @http.route(
        "/connector/docs/setup",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def setup_guide(self, doc="setup", **kwargs):
        """Serve the interactive, responsive documentation viewer for Setup & Developer Guides."""
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url", "")  # sudo: read base url for setup guide links
        base_url = base_url.rstrip("/") if base_url else ""

        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        guide_filename = "CODING_GUIDE.md" if doc == "coding" else "SETUP_GUIDE.md"
        guide_path = os.path.join(module_dir, guide_filename)

        active_title = "Developer & Coding Guide" if doc == "coding" else "Administrator & Setup Guide"

        if os.path.isfile(guide_path):
            try:
                with open(guide_path, "r", encoding="utf-8") as f:
                    md_text = f.read()
                content_html, toc_html = self._convert_markdown_to_html(md_text, base_url)
            except Exception:
                content_html, toc_html = self._get_fallback_setup_guide_html(base_url)
        else:
            content_html, toc_html = self._get_fallback_setup_guide_html(base_url)

        full_html = self._wrap_in_template(
            active_doc=doc,
            active_title=active_title,
            toc_html=toc_html,
            content_html=content_html,
            base_url=base_url,
        )

        return request.make_response(
            full_html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("X-Frame-Options", "SAMEORIGIN"),
            ],
            status=200,
        )

    def _convert_markdown_to_html(self, md_text, base_url):
        """Converts Markdown text to HTML with TOC generation, callouts, tables, images, and raw HTML pass-through."""
        md_text = md_text.replace("http://localhost:8019", base_url)
        lines = md_text.splitlines()
        html_lines = []
        toc_items = []

        in_code = False
        code_lang = ""
        code_buf = []

        in_table = False
        table_buf = []

        in_list = False
        list_tag = "ul"

        in_raw_html = False
        raw_html_depth = 0

        def normalize_img_url(src):
            src = src.strip()
            if src.startswith("./"):
                src = src[2:]
            if src.startswith("static/"):
                return f"/dn_connector_base/{src}"
            return src

        def make_image_box(alt, src):
            src = normalize_img_url(src)
            alt_clean = html.escape(alt)
            return (
                f'<div class="doc-image-box">\n'
                f'    <img src="{src}" alt="{alt_clean}" class="doc-image"/>\n'
                f'    <div class="doc-image-caption"><i class="fa fa-info-circle"></i> {alt_clean}</div>\n'
                f'</div>'
            )

        def flush_table():
            nonlocal in_table, table_buf
            if not table_buf:
                in_table = False
                return ""
            out = ['<div class="table-container"><table>']
            header_done = False
            for i, row in enumerate(table_buf):
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if i == 1 and all(set(c).issubset({"-", ":", " "}) for c in cells):
                    header_done = True
                    continue
                tag = "th" if not header_done else "td"
                row_html = "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells)
                if not header_done:
                    out.append(f"<thead><tr>{row_html}</tr></thead><tbody>")
                else:
                    out.append(f"<tr>{row_html}</tr>")
            if header_done:
                out.append("</tbody>")
            out.append("</table></div>")
            in_table = False
            table_buf = []
            return "\n".join(out)

        def flush_list():
            nonlocal in_list, list_tag
            if in_list:
                in_list = False
                return f"</{list_tag}>\n"
            return ""

        def inline(text):
            text = html.escape(text)
            # Support inline markdown images
            text = re.sub(
                r"!\[(.*?)\]\((.*?)\)",
                lambda m: f'<img src="{normalize_img_url(m.group(2))}" alt="{m.group(1)}" class="doc-image"/>',
                text,
            )
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
            return text

        for line in lines:
            # 1. Code block handling
            if line.startswith("```"):
                if in_code:
                    in_code = False
                    escaped = html.escape("\n".join(code_buf))
                    html_lines.append(
                        f'<pre><code class="language-{code_lang}">{escaped}</code><button class="copy-btn" onclick="copyCode(this)">Copy</button></pre>'
                    )
                    code_buf = []
                    code_lang = ""
                else:
                    if in_table:
                        html_lines.append(flush_table())
                    if in_list:
                        html_lines.append(flush_list())
                    in_code = True
                    code_lang = line[3:].strip()
                continue

            if in_code:
                code_buf.append(line)
                continue

            # 2. Raw HTML Block Pass-Through (e.g. <div, <table, <svg, <figure, <details, <section)
            raw_tag_pattern = r"<(div|table|svg|figure|details|section|article)\b"
            open_count = len(re.findall(raw_tag_pattern, line, re.IGNORECASE))
            self_closing_count = len(re.findall(r"<(div|table|svg|figure|details|section|article)\b[^>]*/>", line, re.IGNORECASE))
            open_count -= self_closing_count
            close_count = len(re.findall(r"</(div|table|svg|figure|details|section|article)>", line, re.IGNORECASE))

            starts_with_raw_html = (
                line.strip().startswith(('<div class="system-param-card"', "<div", "<table", "<svg", "<figure", "<details", "<section"))
                or (not in_raw_html and open_count > 0)
            )

            if not in_raw_html and starts_with_raw_html:
                if in_list:
                    html_lines.append(flush_list())
                if in_table:
                    html_lines.append(flush_table())
                in_raw_html = True

            if in_raw_html:
                html_lines.append(line)
                raw_html_depth += (open_count - close_count)
                if raw_html_depth <= 0:
                    in_raw_html = False
                    raw_html_depth = 0
                continue

            # Standalone closing tag or HTML comment pass-through
            if line.strip().startswith(("</div", "</table", "</svg", "</figure", "</details", "<!--")):
                html_lines.append(line)
                continue

            # 3. Markdown Image Support: ![alt](url)
            img_match = re.match(r"^\s*!\[(.*?)\]\((.*?)\)\s*$", line)
            if img_match:
                if in_list:
                    html_lines.append(flush_list())
                if in_table:
                    html_lines.append(flush_table())
                alt_text, img_url = img_match.group(1), img_match.group(2)
                html_lines.append(make_image_box(alt_text, img_url))
                continue

            # 4. Table handling
            if line.strip().startswith("|") and line.strip().endswith("|"):
                if in_list:
                    html_lines.append(flush_list())
                in_table = True
                table_buf.append(line)
                continue
            elif in_table:
                html_lines.append(flush_table())

            # 5. Headers
            if line.startswith("## "):
                if in_list:
                    html_lines.append(flush_list())
                title = line[3:].strip()
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
                toc_items.append((2, title, slug))
                html_lines.append(f'<h2 id="{slug}">{inline(title)}</h2>')
                continue
            elif line.startswith("### "):
                if in_list:
                    html_lines.append(flush_list())
                title = line[4:].strip()
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
                toc_items.append((3, title, slug))
                html_lines.append(f'<h3 id="{slug}">{inline(title)}</h3>')
                continue
            elif line.startswith("# "):
                if in_list:
                    html_lines.append(flush_list())
                title = line[2:].strip()
                html_lines.append(f'<h1 class="guide-title">{inline(title)}</h1>')
                continue

            # 6. Callouts
            if line.startswith("> "):
                if in_list:
                    html_lines.append(flush_list())
                content = line[2:].strip()
                callout_class = "callout"
                if "[!NOTE]" in content:
                    content = content.replace("[!NOTE]", '<div class="callout-title">ℹ️ Note</div>')
                    callout_class += " info"
                elif "[!TIP]" in content:
                    content = content.replace("[!TIP]", '<div class="callout-title">💡 Tip</div>')
                    callout_class += " tip"
                elif "[!WARNING]" in content:
                    content = content.replace("[!WARNING]", '<div class="callout-title">⚠️ Warning</div>')
                    callout_class += " warning"
                elif "[!CAUTION]" in content or "[!DANGER]" in content:
                    content = content.replace("[!CAUTION]", '<div class="callout-title">🛑 Caution</div>').replace("[!DANGER]", '<div class="callout-title">🛑 Caution</div>')
                    callout_class += " danger"
                elif "[!IMPORTANT]" in content:
                    content = content.replace("[!IMPORTANT]", '<div class="callout-title">📌 Important</div>')
                    callout_class += " info"
                html_lines.append(f'<div class="{callout_class}"><p>{inline(content)}</p></div>')
                continue

            # 7. Lists
            if re.match(r"^(\*|-|\+)\s+(.+)", line):
                item = re.match(r"^(\*|-|\+)\s+(.+)", line).group(2)
                if not in_list or list_tag != "ul":
                    if in_list:
                        html_lines.append(flush_list())
                    in_list = True
                    list_tag = "ul"
                    html_lines.append("<ul>")
                html_lines.append(f"<li>{inline(item)}</li>")
                continue
            elif re.match(r"^\d+\.\s+(.+)", line):
                item = re.match(r"^\d+\.\s+(.+)", line).group(1)
                if not in_list or list_tag != "ol":
                    if in_list:
                        html_lines.append(flush_list())
                    in_list = True
                    list_tag = "ol"
                    html_lines.append("<ol>")
                html_lines.append(f"<li>{inline(item)}</li>")
                continue
            else:
                if in_list:
                    html_lines.append(flush_list())

            # 8. Horizontal rule
            if line.strip() in ("---", "***", "___"):
                html_lines.append("<hr/>")
                continue

            # 9. Plain paragraph
            if line.strip():
                html_lines.append(f"<p>{inline(line)}</p>")

        if in_table:
            html_lines.append(flush_table())
        if in_list:
            html_lines.append(flush_list())

        # Build TOC HTML
        toc_lines = ['<ul class="toc-list" id="tocList">']
        for level, title, slug in toc_items:
            cls = "toc-link" if level == 2 else "toc-link toc-sublink"
            toc_lines.append(f'<li><a href="#{slug}" class="{cls}">{html.escape(title)}</a></li>')
        toc_lines.append("</ul>")

        return "\n".join(html_lines), "\n".join(toc_lines)

    def _get_fallback_setup_guide_html(self, base_url):
        """Fallback complete Setup Guide content when file is unavailable."""
        toc_html = """
        <ul class="toc-list" id="tocList">
            <li><a href="#overview" class="toc-link active">1. Overview &amp; Architecture</a></li>
            <li><a href="#system-config" class="toc-link">2. System Configuration</a></li>
            <li><a href="#framework-presets" class="toc-link">3. Framework Presets</a></li>
            <li><a href="#inbound-endpoints" class="toc-link">4. Inbound Endpoints</a></li>
            <li><a href="#webhooks-setup" class="toc-link">5. Step-by-Step Webhook Setup</a></li>
            <li><a href="#inbox-monitoring" class="toc-link">6. Inbox Monitoring</a></li>
            <li><a href="#dead-letter-queue" class="toc-link">7. Dead Letter Queue (DLQ)</a></li>
            <li><a href="#retention-settings" class="toc-link">8. Retention Settings</a></li>
            <li><a href="#cron-processing" class="toc-link">9. Concurrency &amp; Cron</a></li>
            <li><a href="#security-hardening" class="toc-link">10. Security &amp; Reverse Proxy</a></li>
        </ul>
        """
        content_html = f"""
        <section id="overview" class="doc-section">
            <h2>1. Overview &amp; Architecture</h2>
            <p>The <code>dn_connector_base</code> module provides a carrier-grade <strong>Dual Inbound Gateway and Outbound REST Engine</strong> for Odoo 19.</p>
            <div class="callout tip">
                <div class="callout-title">💡 Core Architecture Highlights</div>
                <p><strong>Zero Data Loss:</strong> Persists all events in Transactional Inbox (<code>connector.inbound.message</code>) before execution.<br/>
                <strong>Fast Ingestion (&lt;50ms):</strong> Webhook callers receive HTTP 202/200 acknowledgments immediately.<br/>
                <strong>High Concurrency:</strong> Multi-worker batch claiming via PostgreSQL <code>FOR UPDATE SKIP LOCKED</code>.</p>
            </div>
        </section>
        <section id="system-config" class="doc-section">
            <h2>2. System Configuration &amp; Base URL</h2>
            <p>Verify that <code>web.base.url</code> matches your public HTTPS domain in System Parameters.</p>
            <div class="system-param-card">
                <div class="param-header">
                    <i class="fa fa-sliders"></i>
                    <span>System Parameters Reference</span>
                </div>
                <div class="param-row">
                    <span class="param-label">Base Web URL</span>
                    <span class="param-key">web.base.url</span>
                    <span class="param-value">{base_url if base_url else 'https://odoo.yourcompany.com'}</span>
                </div>
                <div class="param-row">
                    <span class="param-label">Freeze Domain Overwrite</span>
                    <span class="param-key">web.base.url.freeze</span>
                    <span class="param-value">True</span>
                </div>
            </div>
            <pre><code class="language-bash">{base_url}/connector/docs/setup</code><button class="copy-btn" onclick="copyCode(this)">Copy</button></pre>
        </section>
        <section id="framework-presets" class="doc-section">
            <h2>3. Framework Presets</h2>
            <p>Standardizes platform signatures for Shopify, GitHub, Stripe, and Generic REST.</p>
        </section>
        <section id="inbound-endpoints" class="doc-section">
            <h2>4. Inbound Endpoints</h2>
            <p>Configure routes with immediate or deferred execution, priority levels, and FIFO ordering keys.</p>
        </section>
        <section id="webhooks-setup" class="doc-section">
            <h2>5. Step-by-Step Webhook Setup</h2>
            <p>Step-by-step guides for connecting Shopify, GitHub, and Stripe webhooks to Odoo.</p>
        </section>
        <section id="inbox-monitoring" class="doc-section">
            <h2>6. Inbox Monitoring</h2>
            <p>Track message states: received, queued, processing, done, failed, dead, and skipped.</p>
        </section>
        <section id="dead-letter-queue" class="doc-section">
            <h2>7. Dead Letter Queue (DLQ)</h2>
            <p>Quarantined messages after 5 retries. Inspect traceback and trigger manual retry with 'Process Now'.</p>
        </section>
        <section id="retention-settings" class="doc-section">
            <h2>8. Centralized Retention Settings</h2>
            <p>Configure retention days for done messages and dead letters in General Settings.</p>
        </section>
        <section id="cron-processing" class="doc-section">
            <h2>9. Concurrency &amp; Cron</h2>
            <p>Inbound batch processor cron tuning with SELECT FOR UPDATE SKIP LOCKED.</p>
        </section>
        <section id="security-hardening" class="doc-section">
            <h2>10. Security &amp; Reverse Proxy</h2>
            <p>Nginx reverse proxy header forwarding, IP allowlists, and HMAC signature validation.</p>
        </section>
        """
        return content_html, toc_html

    def _wrap_in_template(self, active_doc, active_title, toc_html, content_html, base_url):
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{active_title} | Odoo 19 Connector</title>
    <link rel="icon" type="image/png" href="/web/static/img/favicon.ico"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
    <style>
        :root {{
            --primary: #0284c7;
            --primary-hover: #0369a1;
            --primary-light: #e0f2fe;
            --secondary: #475569;
            --accent: #6366f1;
            --bg-page: #f8fafc;
            --bg-surface: #ffffff;
            --bg-code: #0f172a;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --sidebar-width: 300px;
            --radius-sm: 6px;
            --radius-md: 10px;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: var(--text-main);
            background-color: var(--bg-page);
            line-height: 1.65;
        }}
        .top-navbar {{
            position: sticky; top: 0; z-index: 50; display: flex; align-items: center; justify-content: space-between;
            height: 64px; padding: 0 2rem; background: #ffffff; border-bottom: 1px solid var(--border); box-shadow: var(--shadow-sm);
        }}
        .brand {{ display: flex; align-items: center; gap: 0.75rem; text-decoration: none; color: var(--text-main); font-weight: 700; font-size: 1.15rem; }}
        .brand-badge {{ display: inline-block; background: var(--primary-light); color: var(--primary-hover); font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.55rem; border-radius: 9999px; }}
        .top-nav-links {{ display: flex; align-items: center; gap: 0.75rem; }}
        .doc-tab {{
            font-size: 0.85rem; font-weight: 600; text-decoration: none; padding: 0.45rem 0.9rem; border-radius: var(--radius-sm);
            color: var(--secondary); border: 1px solid var(--border); background: #ffffff; transition: all 0.15s ease;
        }}
        .doc-tab:hover {{ background: var(--primary-light); color: var(--primary); border-color: var(--primary); }}
        .doc-tab.active {{ background: var(--primary); color: #ffffff; border-color: var(--primary); }}
        .nav-btn {{
            font-size: 0.85rem; font-weight: 500; color: var(--secondary); text-decoration: none; padding: 0.45rem 0.85rem;
            border-radius: var(--radius-sm); border: 1px solid var(--border); background: #ffffff;
        }}
        .nav-btn:hover {{ background: var(--bg-page); color: var(--primary); }}
        .layout {{ display: flex; min-height: calc(100vh - 64px); max-width: 1440px; margin: 0 auto; }}
        .sidebar {{
            width: var(--sidebar-width); flex-shrink: 0; position: sticky; top: 64px; height: calc(100vh - 64px);
            overflow-y: auto; padding: 1.5rem 1rem 3rem 1.5rem; border-right: 1px solid var(--border); background: #ffffff;
        }}
        .search-box {{ margin-bottom: 1.25rem; }}
        .search-input {{
            width: 100%; padding: 0.55rem 0.85rem; font-size: 0.85rem; border: 1px solid var(--border);
            border-radius: var(--radius-sm); background: var(--bg-page); outline: none;
        }}
        .search-input:focus {{ border-color: var(--primary); background: #ffffff; }}
        .toc-title {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 700; margin-bottom: 0.6rem; }}
        .toc-list {{ list-style: none; display: flex; flex-direction: column; gap: 0.2rem; }}
        .toc-link {{
            display: block; padding: 0.4rem 0.65rem; font-size: 0.86rem; color: var(--secondary); text-decoration: none;
            border-radius: var(--radius-sm); transition: all 0.15s ease; line-height: 1.35;
        }}
        .toc-link:hover {{ color: var(--primary); background: var(--primary-light); }}
        .toc-link.active {{ color: var(--primary-hover); background: var(--primary-light); font-weight: 600; border-left: 3px solid var(--primary); }}
        .toc-sublink {{ font-size: 0.8rem; padding-left: 1.25rem; color: var(--text-muted); }}
        .content {{ flex: 1; padding: 2.5rem 3.5rem 6rem; max-width: 980px; overflow-x: hidden; }}
        .guide-title {{ font-size: 2.25rem; font-weight: 800; color: var(--text-main); letter-spacing: -0.025em; margin-bottom: 1rem; }}
        h2 {{ font-size: 1.5rem; font-weight: 700; color: var(--text-main); margin-top: 3rem; margin-bottom: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }}
        h3 {{ font-size: 1.18rem; font-weight: 600; color: var(--text-main); margin-top: 1.75rem; margin-bottom: 0.75rem; }}
        p {{ margin-bottom: 1rem; color: #334155; font-size: 0.96rem; }}
        ul, ol {{ margin-bottom: 1.25rem; padding-left: 1.5rem; color: #334155; font-size: 0.95rem; }}
        li {{ margin-bottom: 0.45rem; }}
        hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}
        .callout {{
            border-left: 4px solid var(--primary); background: #f0f9ff; padding: 1rem 1.25rem;
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0; margin: 1.5rem 0; font-size: 0.92rem;
        }}
        .callout.tip {{ border-left-color: #10b981; background: #ecfdf5; }}
        .callout.warning {{ border-left-color: #f59e0b; background: #fffbeb; }}
        .callout.danger {{ border-left-color: #ef4444; background: #fef2f2; }}
        .callout-title {{ font-weight: 700; margin-bottom: 0.35rem; }}
        pre {{
            position: relative; background: var(--bg-code); color: #f8fafc; padding: 1.25rem 1.5rem;
            border-radius: var(--radius-md); overflow-x: auto; margin: 1.25rem 0;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.86rem; line-height: 1.55;
        }}
        code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.88em; background: #f1f5f9; color: #0f172a; padding: 0.15rem 0.35rem; border-radius: 4px; }}
        pre code {{ background: transparent; color: inherit; padding: 0; font-size: 1em; }}
        .copy-btn {{
            position: absolute; top: 0.6rem; right: 0.6rem; background: #334155; color: #cbd5e1;
            border: 1px solid #475569; font-size: 0.72rem; font-weight: 600; padding: 0.25rem 0.55rem;
            border-radius: var(--radius-sm); cursor: pointer;
        }}
        .copy-btn:hover {{ background: #475569; color: #ffffff; }}
        .table-container {{ overflow-x: auto; margin: 1.5rem 0; border: 1px solid var(--border); border-radius: var(--radius-md); background: #ffffff; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }}
        th {{ background: var(--bg-page); color: var(--text-main); font-weight: 600; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }}
        td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); color: #334155; vertical-align: top; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: #f8fafc; }}

        /* Responsive Visual Images */
        .doc-image-box {{
            margin: 2rem 0;
            text-align: center;
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            box-shadow: var(--shadow-sm);
            overflow: hidden;
        }}
        .doc-image {{
            max-width: 100%;
            height: auto;
            border-radius: var(--radius-sm);
            display: block;
            margin: 0 auto;
        }}
        .doc-image-caption {{
            margin-top: 0.75rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            font-style: italic;
        }}

        /* System Parameter Cards */
        .system-param-card {{
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-left: 4px solid #0284c7;
            border-radius: var(--radius-md);
            padding: 1.25rem 1.5rem;
            margin: 1.5rem 0;
            box-shadow: var(--shadow-sm);
        }}
        .param-header {{
            font-weight: 700;
            font-size: 0.95rem;
            color: #0f172a;
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .param-row {{
            display: grid;
            grid-template-columns: 240px 180px 1fr;
            align-items: center;
            gap: 1rem;
            padding: 0.6rem 0;
            border-top: 1px solid #f1f5f9;
            font-size: 0.88rem;
        }}
        .param-row:first-of-type {{
            border-top: none;
        }}
        .param-label {{
            color: #475569;
            font-weight: 500;
        }}
        .param-key {{
            font-family: monospace;
            color: #0f766e;
            background: #f0fdfa;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }}
        .param-value {{
            font-family: monospace;
            color: #1e293b;
            background: #f8fafc;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            border: 1px solid #e2e8f0;
        }}

        .back-to-top {{
            position: fixed; bottom: 2rem; right: 2rem; background: var(--primary); color: #ffffff;
            width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
            text-decoration: none; box-shadow: var(--shadow-lg); opacity: 0.85; transition: all 0.2s ease;
        }}
        .back-to-top:hover {{ opacity: 1; transform: translateY(-2px); }}
        @media (max-width: 900px) {{
            .sidebar {{ display: none; }}
            .content {{ padding: 1.5rem; }}
            .param-row {{
                grid-template-columns: 1fr;
                gap: 0.35rem;
            }}
        }}
    </style>
</head>
<body>
    <header class="top-navbar">
        <a href="/odoo/settings" class="brand">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                <line x1="6" y1="6" x2="6.01" y2="6"></line>
                <line x1="6" y1="18" x2="6.01" y2="18"></line>
            </svg>
            <span>Universal REST Connector</span>
            <span class="brand-badge">Odoo 19</span>
        </a>
        <div class="top-nav-links">
            <a href="/connector/docs/setup?doc=setup" class="doc-tab {'active' if active_doc == 'setup' else ''}">Setup Guide</a>
            <a href="/connector/docs/setup?doc=coding" class="doc-tab {'active' if active_doc == 'coding' else ''}">Developer Guide</a>
            <a href="/odoo/action-dn_connector_base.action_connector_inbound_endpoint" class="nav-btn">Endpoints</a>
            <a href="/odoo/action-dn_connector_base.action_connector_inbound_message" class="nav-btn">Inbox</a>
            <a href="/odoo/action-dn_connector_base.action_connector_settings" class="nav-btn">Settings</a>
        </div>
    </header>

    <div class="layout">
        <aside class="sidebar">
            <div class="search-box">
                <input type="text" id="searchDocs" class="search-input" placeholder="Search documentation..."/>
            </div>
            <div class="toc-title">Table of Contents</div>
            {toc_html}
        </aside>

        <main class="content">
            {content_html}
            <div style="margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem; text-align: center;">
                Universal REST Connector Base &bull; Odoo 19.0 Enterprise &amp; Community &bull; In-App Documentation Viewer
            </div>
        </main>
    </div>

    <a href="#" class="back-to-top" title="Back to top">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
    </a>

    <script>
        function copyCode(button) {{
            const pre = button.parentElement;
            const code = pre.querySelector('code');
            const text = code ? code.innerText : pre.innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const originalText = button.innerText;
                button.innerText = 'Copied!';
                button.style.background = '#10b981';
                button.style.borderColor = '#10b981';
                button.style.color = '#ffffff';
                setTimeout(() => {{
                    button.innerText = originalText;
                    button.style.background = '';
                    button.style.borderColor = '';
                    button.style.color = '';
                }}, 2000);
            }}).catch(err => {{
                console.error('Failed to copy text: ', err);
            }});
        }}

        document.getElementById('searchDocs').addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase().trim();
            const elements = document.querySelectorAll('.content > *');
            elements.forEach(el => {{
                if (!query) {{
                    el.style.display = '';
                    return;
                }}
                if (el.tagName === 'H2' || el.tagName === 'H3' || el.tagName === 'P' || el.tagName === 'DIV' || el.tagName === 'PRE') {{
                    const text = el.innerText.toLowerCase();
                    el.style.display = text.includes(query) ? '' : 'none';
                }}
            }});
        }});

        window.addEventListener('scroll', () => {{
            const headings = document.querySelectorAll('h2[id], h3[id]');
            const scrollPos = window.scrollY + 120;
            headings.forEach(h => {{
                const top = h.offsetTop;
                const id = h.getAttribute('id');
                if (scrollPos >= top && scrollPos < top + 250) {{
                    document.querySelectorAll('.toc-link').forEach(link => {{
                        link.classList.remove('active');
                        if (link.getAttribute('href') === '#' + id) {{
                            link.classList.add('active');
                        }}
                    }});
                }}
            }});
        }});
    </script>
</body>
</html>"""
