"""
Script para compilar la documentación oficial de SIVARH a un documento HTML con diseño editorial
impecable y exportarlo a PDF de alta resolución listo para imprimir mediante Chrome headless.
"""

import os
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DOC_MD = ROOT_DIR / "documentacio.md"
HTML_OUTPUT = ROOT_DIR / "docs" / "documentacion_imprimible.html"
PDF_OUTPUT = ROOT_DIR / "docs" / "SIVARH_Documentacion_Tecnica.pdf"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def markdown_to_html(md_text: str) -> str:
    # Convert markdown headers
    html_lines = []
    in_code_block = False
    code_block_lang = ""
    code_block_lines = []
    
    in_table = False
    table_lines = []
    
    for line in md_text.splitlines():
        # Code blocks
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_lang = line[3:].strip()
                code_block_lines = []
            else:
                in_code_block = False
                code_content = "\n".join(code_block_lines)
                # Escape html
                code_content = code_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f'<pre class="code-block {code_block_lang}"><code>{code_content}</code></pre>')
            continue
            
        if in_code_block:
            code_block_lines.append(line)
            continue
            
        # Tables
        if "|" in line and not in_code_block:
            if not in_table:
                in_table = True
                table_lines = [line]
            else:
                table_lines.append(line)
            continue
        elif in_table:
            in_table = False
            # Render table
            if len(table_lines) >= 2:
                header_row = [c.strip() for c in table_lines[0].split("|")[1:-1]]
                html_lines.append('<div class="table-container"><table>')
                html_lines.append('<thead><tr>')
                for h in header_row:
                    h = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', h)
                    html_lines.append(f'<th>{h}</th>')
                html_lines.append('</tr></thead><tbody>')
                
                for row_str in table_lines[2:]:
                    cols = [c.strip() for c in row_str.split("|")[1:-1]]
                    if not cols:
                        continue
                    html_lines.append('<tr>')
                    for c in cols:
                        c = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', c)
                        c = re.sub(r'\*(.*?)\*', r'<em>\1</em>', c)
                        c = re.sub(r'`(.*?)`', r'<code>\1</code>', c)
                        html_lines.append(f'<td>{c}</td>')
                    html_lines.append('</tr>')
                html_lines.append('</tbody></table></div>')
            table_lines = []

        # Empty lines
        if not line.strip():
            html_lines.append('')
            continue

        # Horizontal rule
        if line.strip() == "---":
            html_lines.append('<hr class="divider"/>')
            continue

        # Headers
        if line.startswith("# "):
            title = line[2:].strip()
            html_lines.append(f'<h1 class="chapter-title">{title}</h1>')
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            html_lines.append(f'<h2 class="section-title">{title}</h2>')
            continue
        if line.startswith("### "):
            title = line[4:].strip()
            html_lines.append(f'<h3 class="subsection-title">{title}</h3>')
            continue
        if line.startswith("#### "):
            title = line[5:].strip()
            html_lines.append(f'<h4 class="subsubsection-title">{title}</h4>')
            continue

        # Lists
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            content = line.strip()[2:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
            content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
            html_lines.append(f'<li class="bullet-item">{content}</li>')
            continue
            
        m = re.match(r'^\s*(\d+)\.\s+(.*)', line)
        if m:
            num = m.group(1)
            content = m.group(2)
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
            content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
            html_lines.append(f'<li class="numbered-item" value="{num}">{content}</li>')
            continue

        # Paragraphs with inline styling
        p = line.strip()
        p = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', p)
        p = re.sub(r'\*(.*?)\*', r'<em>\1</em>', p)
        p = re.sub(r'`(.*?)`', r'<code>\1</code>', p)
        p = re.sub(r'\[(.*?)\]\((.*?)\)', r'<span class="doc-link">\1</span>', p)
        html_lines.append(f'<p>{p}</p>')

    # Wrap isolated list items
    rendered = "\n".join(html_lines)
    rendered = re.sub(r'(<li class="bullet-item">.*?</li>\n?)+', r'<ul class="styled-list">\g<0></ul>', rendered, flags=re.DOTALL)
    rendered = re.sub(r'(<li class="numbered-item".*?</li>\n?)+', r'<ol class="styled-list">\g<0></ol>', rendered, flags=re.DOTALL)
    
    return rendered

def build_full_html():
    with open(DOC_MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    body_content = markdown_to_html(md_text)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>SIVARH — Documentación Técnica y Arquitectura</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 20mm 16mm 20mm 16mm;
            @top-right {{
                content: "SIVARH — UNHEVAL (2026)";
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
            @bottom-right {{
                content: "Página " counter(page);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
            @bottom-left {{
                content: "Documento Técnico de Investigación CyT";
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
        }}

        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        body {{
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.55;
            color: #1e293b;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
        }}

        /* Portada */
        .cover-page {{
            page-break-after: always;
            min-height: 90vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 40px 20px 20px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        }}

        .cover-header {{
            text-align: center;
            border-bottom: 3px solid #0284c7;
            padding-bottom: 25px;
        }}

        .institution {{
            font-size: 14pt;
            font-weight: 700;
            color: #0f172a;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin: 0;
        }}

        .faculty {{
            font-size: 11pt;
            color: #0369a1;
            font-weight: 600;
            margin-top: 6px;
        }}

        .program {{
            font-size: 9.5pt;
            color: #64748b;
            margin-top: 4px;
        }}

        .cover-body {{
            text-align: center;
            margin: 40px 0;
        }}

        .cover-logo-wrapper {{
            width: 150px;
            margin: 0 auto 18px;
        }}

        .cover-logo-img {{
            width: 100%;
            height: auto;
            object-fit: contain;
        }}

        .badge {{
            display: inline-block;
            background: #e0f2fe;
            color: #0369a1;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin-bottom: 20px;
            border: 1px solid #bae6fd;
        }}

        .project-acronym {{
            font-size: 34pt;
            font-weight: 900;
            color: #0f172a;
            letter-spacing: 2px;
            margin: 10px 0;
            background: linear-gradient(90deg, #0284c7, #0f766e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .project-title {{
            font-size: 14pt;
            font-weight: 700;
            color: #334155;
            max-width: 90%;
            margin: 0 auto;
            line-height: 1.4;
        }}

        .project-subtitle {{
            font-size: 11pt;
            color: #0d9488;
            font-weight: 600;
            margin-top: 15px;
        }}

        .cover-footer {{
            border-top: 1px solid #e2e8f0;
            padding-top: 20px;
            display: flex;
            justify-content: space-between;
            font-size: 9pt;
            color: #475569;
        }}

        .cover-footer-column {{
            flex: 1;
        }}

        .cover-footer-right {{
            text-align: right;
        }}

        /* Tipografía y secciones */
        h1.chapter-title {{
            font-size: 18pt;
            font-weight: 800;
            color: #0f172a;
            border-bottom: 2px solid #0284c7;
            padding-bottom: 6px;
            margin-top: 30px;
            margin-bottom: 15px;
            page-break-before: always;
        }}

        /* Evitar salto de página en el primer h1 después de la portada */
        .cover-page + h1.chapter-title {{
            page-break-before: avoid;
        }}

        h2.section-title {{
            font-size: 13pt;
            font-weight: 700;
            color: #0369a1;
            margin-top: 22px;
            margin-bottom: 10px;
            border-left: 4px solid #0284c7;
            padding-left: 10px;
            page-break-after: avoid;
        }}

        h3.subsection-title {{
            font-size: 11pt;
            font-weight: 600;
            color: #334155;
            margin-top: 16px;
            margin-bottom: 8px;
            page-break-after: avoid;
        }}

        p {{
            margin: 0 0 10px 0;
            text-align: justify;
        }}

        .divider {{
            border: 0;
            height: 1px;
            background: #e2e8f0;
            margin: 24px 0;
        }}

        /* Listas */
        .styled-list {{
            margin: 8px 0 14px 20px;
            padding: 0;
        }}

        li {{
            margin-bottom: 5px;
        }}

        /* Tablas */
        .table-container {{
            margin: 16px 0;
            width: 100%;
            overflow-x: auto;
            page-break-inside: avoid;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
            line-height: 1.4;
        }}

        th {{
            background-color: #0f172a;
            color: #ffffff;
            font-weight: 600;
            text-align: left;
            padding: 7px 10px;
            border: 1px solid #1e293b;
        }}

        td {{
            padding: 6px 10px;
            border: 1px solid #e2e8f0;
            vertical-align: top;
        }}

        tr:nth-child(even) {{
            background-color: #f8fafc;
        }}

        /* Bloques de código y pre */
        pre.code-block {{
            background-color: #0f172a;
            color: #f8fafc;
            padding: 12px 14px;
            border-radius: 6px;
            font-family: "Consolas", "Courier New", monospace;
            font-size: 8pt;
            line-height: 1.4;
            overflow-x: hidden;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 14px 0;
            page-break-inside: avoid;
            border: 1px solid #334155;
        }}

        code {{
            font-family: "Consolas", "Courier New", monospace;
            font-size: 8.5pt;
            background-color: #f1f5f9;
            color: #0369a1;
            padding: 1px 4px;
            border-radius: 4px;
            border: 1px solid #e2e8f0;
        }}

        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
            border: 0;
        }}

        .doc-link {{
            color: #0284c7;
            font-weight: 600;
        }}
    </style>
</head>
<body>

    <!-- PORTADA FORMAL PARA IMPRESIÓN -->
    <div class="cover-page">
        <div class="cover-header">
            <h1 class="institution">Universidad Nacional Hermilio Valdizán</h1>
            <div class="faculty">Facultad de Ingeniería Industrial y de Sistemas</div>
            <div class="program">Proyecto de Investigación Aplicada en Ciencia y Tecnología (CyT 2026-II)</div>
        </div>

        <div class="cover-body">
            <div class="cover-logo-wrapper">
                <img src="../assets/imagotipo_sivarh.png" alt="SIVARH" class="cover-logo-img">
            </div>
            <div class="badge">Documentación Técnica Oficial &bull; Versión 2.0</div>
            <div class="project-title">
                Sistema Inteligente de Vigilancia Ambiental para las Riberas del Río Huallaga orientado a la detección preventiva del arrojo directo de residuos sólidos
            </div>
            <div class="project-subtitle">
                Sector Crítico: Puente Huallaga &mdash; UNHEVAL (Huánuco &ndash; Amarilis &ndash; Pillco Marca)
            </div>
        </div>

        <div class="cover-footer">
            <div class="cover-footer-column">
                <strong>Área Temática:</strong> Visión Computacional, Inteligencia Artificial Multimodal e Intervención Preventiva Ambiental.<br>
                <strong>Entorno:</strong> Edge Computing (Local) + Multimodal Cloud Reasoning (OpenAI Vision &amp; TTS).
            </div>
            <div class="cover-footer-column cover-footer-right">
                <strong>Ubicación:</strong> Huánuco, Perú<br>
                <strong>Fecha:</strong> Septiembre 2026<br>
                <strong>Estado:</strong> Prototipo Autónomo Operativo (Fases 1 a 4 Completadas)
            </div>
        </div>
    </div>

    <!-- CONTENIDO TÉCNICO -->
    {body_content}

</body>
</html>
"""
    os.makedirs(HTML_OUTPUT.parent, exist_ok=True)
    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML imprimible generado con éxito en: {HTML_OUTPUT}")

def export_to_pdf():
    build_full_html()
    print("Exportando a PDF mediante Chrome Headless...")
    
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(PDF_OUTPUT)}",
        f"file:///{str(HTML_OUTPUT).replace(os.sep, '/')}"
    ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if PDF_OUTPUT.exists():
            size_kb = PDF_OUTPUT.stat().st_size / 1024
            print(f"PDF generado con éxito en: {PDF_OUTPUT} ({size_kb:.1f} KB)")
            return True
        else:
            print(f"Error generando PDF: {res.stderr}")
            return False
    except subprocess.TimeoutExpired:
        if PDF_OUTPUT.exists():
            size_kb = PDF_OUTPUT.stat().st_size / 1024
            print(f"PDF generado con éxito en: {PDF_OUTPUT} ({size_kb:.1f} KB)")
            return True
        print("Timeout esperando a Chrome")
        return False

if __name__ == "__main__":
    export_to_pdf()
