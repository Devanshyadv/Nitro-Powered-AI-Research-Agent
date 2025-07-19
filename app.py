
import streamlit as st
import os
import logging
import io
import re
from datetime import datetime
from fpdf import FPDF

from main import run_full_research

# Load .env and support st.secrets fallback
from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY   =   os.getenv("GROQ_API_KEY")
GEMINI_API_KEY =  os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY =  os.getenv("TAVILY_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Nitro AI Research",
    page_icon="🚀",
    layout="wide",
)

# Markdown to HTML converter
def convert_markdown_to_html(text: str) -> str:
    # Headings
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(?!\*)(.+?)\*', r'<em>\1</em>', text)
    # Bullets
    lines = text.split('\n')
    in_list = False
    html_lines = []
    for line in lines:
        if line.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{line[2:]}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(line)
    if in_list:
        html_lines.append('</ul>')
    return '<br>'.join(html_lines)

# Custom CSS
st.markdown("""
<style>
body {font-family:'Segoe UI',sans-serif;background:#121212;color:#e0e0e0;}
.hero {background:linear-gradient(135deg,#667eea,#764ba2);padding:60px 20px;text-align:center;color:#fff;border-radius:12px;margin-bottom:40px;}
.input-area, .report-box {background:#1e1e1e;padding:30px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.5);margin-bottom:30px;}
.stats-area {margin-bottom:40px;}
.stat-card {background:#1e1e1e;padding:20px;border-radius:8px;text-align:center;box-shadow:0 1px 6px rgba(0,0,0,0.5);color:#fff;}
.stat-card h3 {margin:0;font-size:24px;}
.stat-card p {margin:5px 0 0;color:#a0a0a0;}
.report-box h1, .report-box h2, .report-box h3 {color:#fff;margin-top:16px;}
.report-box strong {font-weight:bold;color:#fff;}
.report-box em {font-style:italic;color:#ccc;}
.report-box ul {padding-left:20px;margin:8px 0;}
.report-box li {margin-bottom:5px;}
.stButton>button {background:#667eea;color:#fff;padding:12px 24px;border:none;border-radius:6px;font-size:16px;}
.stTextInput>div>div>input {background:#2a2a2a;color:#e0e0e0;border:none;}
.footer {text-align:center;color:#888;padding:40px 0;}
</style>
""", unsafe_allow_html=True)

# Hero + Input
st.markdown("""
<div class="hero">
  <h1>🚀 Nitro-Powered AI Research Agent</h1>
  <p>Get instant, AI-driven research reports in seconds.</p>
</div>
""", unsafe_allow_html=True)

topic = st.text_input("Enter your research topic", placeholder="e.g., AI in Healthcare 2025")
start = st.button("Start Research")

# Stats
col1, col2, col3 = st.columns(3)
stats = [("⚡","Fast","Reports in 30s"),("🆓","Free","Always free tier"),("🔄","Live","Up-to-date data")]
for col, (icon, title, subtitle) in zip((col1, col2, col3), stats):
    with col:
        st.markdown(
            f"<div class='stat-card'><h3>{icon} {title}</h3><p>{subtitle}</p></div>",
            unsafe_allow_html=True
        )

# Generate and Display Report
if start and topic:
    with st.spinner("Generating report..."):
        raw_report = run_full_research(topic)
    st.success(f"Completed at {datetime.now():%Y-%m-%d %H:%M:%S}")
    html_report = convert_markdown_to_html(raw_report)
    st.markdown(f"<div class='report-box'>{html_report}</div>", unsafe_allow_html=True)

    # PDF Generation
    pdf = FPDF()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()
    pdf.set_font('Arial','',12)
    for line in raw_report.split('\n'):
        if line.startswith('# '):
            pdf.set_font('Arial','B',16)
            pdf.cell(0,10,line[2:])
            pdf.ln()
        elif line.startswith('## '):
            pdf.set_font('Arial','B',14)
            pdf.cell(0,8,line[3:])
            pdf.ln()
        elif line.startswith('* '):
            pdf.set_font('Arial','',12)
            pdf.cell(5)
            pdf.cell(0,6,line[2:])
            pdf.ln()
        else:
            pdf.set_font('Arial','',12)
            pdf.multi_cell(0,6,line)
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_buf = io.BytesIO(pdf_bytes)
    st.download_button("Download Report as PDF", data=pdf_buf, file_name=f"AI_Report_{datetime.now():%Y%m%d}.pdf", mime='application/pdf')

# Footer
st.markdown("""
<div class='footer'>Powered by Groq • Google Gemini • Tavily</div>
""", unsafe_allow_html=True)
