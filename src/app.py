import os
import tempfile
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image

# Import custom backend modules
from analyzer import process_pdf, get_page_preview_rgb, generate_heatmap_overlay
from cost_estimator import get_default_cartridge_specs, estimate_document_printing_costs
from report_generator import generate_csv_report, generate_pdf_report
from sample_generator import create_sample_pdf

# ----------------------------------------------------
# Page Configuration & Design System
# ----------------------------------------------------
st.set_page_config(
    page_title="PDF CMYK Ink Analyzer",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS for premium styling (glassmorphism cards, metric badges)
st.markdown("""
<style>
    /* Gradient headers */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    
    /* Custom KPI Cards */
    .kpi-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .kpi-card {
        flex: 1;
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #E5E7EB;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #6B7280;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-top: 0.25rem;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #9CA3AF;
        margin-top: 0.25rem;
    }
    
    /* Color tags for channels */
    .badge-c { background-color: #E0F2FE; color: #0369A1; padding: 2px 8px; border-radius: 6px; font-weight: bold; }
    .badge-m { background-color: #FCE7F3; color: #BE185D; padding: 2px 8px; border-radius: 6px; font-weight: bold; }
    .badge-y { background-color: #FEF9C3; color: #854D0E; padding: 2px 8px; border-radius: 6px; font-weight: bold; }
    .badge-k { background-color: #F3F4F6; color: #1F2937; padding: 2px 8px; border-radius: 6px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Sample PDF generation is imported from sample_generator.py

# ----------------------------------------------------
# Main Code & Interface
# ----------------------------------------------------
st.markdown("<h1 class='main-title'>PDF CMYK Ink Coverage Analyzer</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Analyze document-level and page-by-page CMYK ink coverage, detect over-inking, and estimate printing costs.</p>", unsafe_allow_html=True)

# Initialize Session State
if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'analysis_filename' not in st.session_state:
    st.session_state.analysis_filename = None
if 'engine_name' not in st.session_state:
    st.session_state.engine_name = None

# ----------------------------------------------------
# Sidebar Configurations
# ----------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/144/cmyk.png", width=72)
st.sidebar.header("📁 Document Source")

# Uploader
uploaded_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

# Sample PDF Button
use_sample = st.sidebar.button("💡 Use Sample CMYK PDF")

# Process Configurations
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Processing Settings")
dpi = st.sidebar.selectbox("DPI (Rendering Resolution)", [72, 100, 150, 200, 300], index=2, help="Higher DPI improves analysis precision but increases processing time.")
tic_limit = st.sidebar.slider("Over-Inking TIC Limit (%)", 100.0, 400.0, 240.0, step=10.0, help="Total Ink Coverage limit above which printer paper issues or smudging occur (typically 240% for uncoated, 300% for coated paper).")

# Pricing Configuration
st.sidebar.markdown("---")
st.sidebar.header("💰 Cost Configurator")
consumption_rate = st.sidebar.number_input("Ink Consumption Rate (ml/m²)", min_value=0.5, max_value=5.0, value=1.5, step=0.1, help="Volume of ink in ml consumed per 1m² for 100% solid coverage.")

st.sidebar.markdown("**Cartridge Specifications**")
specs = get_default_cartridge_specs()

c_price = st.sidebar.number_input("Cyan Cartridge Price ($)", value=specs["cyan"]["price"], step=0.5, format="%.2f")
c_vol = st.sidebar.number_input("Cyan Volume (ml)", value=specs["cyan"]["volume"], step=1.0)

m_price = st.sidebar.number_input("Magenta Cartridge Price ($)", value=specs["magenta"]["price"], step=0.5, format="%.2f")
m_vol = st.sidebar.number_input("Magenta Volume (ml)", value=specs["magenta"]["volume"], step=1.0)

y_price = st.sidebar.number_input("Yellow Cartridge Price ($)", value=specs["yellow"]["price"], step=0.5, format="%.2f")
y_vol = st.sidebar.number_input("Yellow Volume (ml)", value=specs["yellow"]["volume"], step=1.0)

k_price = st.sidebar.number_input("Black Cartridge Price ($)", value=specs["black"]["price"], step=0.5, format="%.2f")
k_vol = st.sidebar.number_input("Black Volume (ml)", value=specs["black"]["volume"], step=1.0)

user_specs = {
    "cyan": {"price": c_price, "volume": c_vol},
    "magenta": {"price": m_price, "volume": m_vol},
    "yellow": {"price": y_price, "volume": y_vol},
    "black": {"price": k_price, "volume": k_vol}
}

# ----------------------------------------------------
# Upload & Sample PDF File Handling
# ----------------------------------------------------
if uploaded_file is not None:
    # Save uploaded file to temp path
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tfile.write(uploaded_file.read())
    tfile.close()
    
    # If the file path changed, clear cache
    if st.session_state.uploaded_file_path != tfile.name:
        st.session_state.uploaded_file_path = tfile.name
        st.session_state.analysis_results = None
        st.session_state.analysis_filename = uploaded_file.name

elif use_sample:
    # Generate sample PDF
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    create_sample_pdf(tfile.name)
    tfile.close()
    
    st.session_state.uploaded_file_path = tfile.name
    st.session_state.analysis_results = None
    st.session_state.analysis_filename = "sample_cmyk_test.pdf"
    st.sidebar.info("Using Sample CMYK PDF.")

# ----------------------------------------------------
# Run Analysis
# ----------------------------------------------------
if st.session_state.uploaded_file_path:
    # Clear previous results if configs have changed (handled implicitly if user clicks "Analyze" or automatically on path change)
    st.markdown(f"**Loaded File:** `{st.session_state.analysis_filename}`")
    
    run_btn = st.button("🚀 Analyze CMYK Ink Coverage", type="primary")
    
    if run_btn or st.session_state.analysis_results is None:
        with st.spinner("Analyzing PDF pages and extracting CMYK channels..."):
            progress_bar = st.progress(0)
            
            def update_progress(current, total):
                progress_bar.progress(int((current / total) * 100))
                
            try:
                results, engine = process_pdf(
                    st.session_state.uploaded_file_path,
                    dpi=dpi,
                    tic_limit=tic_limit,
                    progress_cb=update_progress
                )
                
                # Store in session state
                st.session_state.analysis_results = results
                st.session_state.engine_name = engine
                st.success(f"Analysis completed successfully using **{engine}** engine!")
            except Exception as e:
                st.error(f"Failed to process PDF: {e}")
                st.session_state.analysis_results = None
                
    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        engine = st.session_state.engine_name
        
        # Calculate costs based on current sidebar inputs
        cost_details, doc_totals = estimate_document_printing_costs(
            results,
            user_specs,
            consumption_rate_ml_m2=consumption_rate
        )
        
        # ----------------------------------------------------
        # Dashboard Dashboard KPIs
        # ----------------------------------------------------
        total_pages = len(results)
        avg_c = sum(p["cyan"] for p in results) / total_pages
        avg_m = sum(p["magenta"] for p in results) / total_pages
        avg_y = sum(p["yellow"] for p in results) / total_pages
        avg_k = sum(p["black"] for p in results) / total_pages
        avg_tic = avg_c + avg_m + avg_y + avg_k
        
        # Find dominant ink
        channel_avgs = {"Cyan": avg_c, "Magenta": avg_m, "Yellow": avg_y, "Black": avg_k}
        dom_ink = max(channel_avgs, key=channel_avgs.get)
        
        # Find highest ink consuming page
        max_page = max(results, key=lambda x: x["avg_tic"])
        
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-label">Total Pages</div>
                <div class="kpi-value">{total_pages}</div>
                <div class="kpi-sub">Pages Rendered</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Est. Document Cost</div>
                <div class="kpi-value">${doc_totals['total_cost']:.3f}</div>
                <div class="kpi-sub">Total Ink Cost</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Average Page TIC</div>
                <div class="kpi-value">{avg_tic:.1f}%</div>
                <div class="kpi-sub">Cyan {avg_c:.1f}% | Mag {avg_m:.1f}% | Yel {avg_y:.1f}% | Blk {avg_k:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Dominant Ink</div>
                <div class="kpi-value">{dom_ink}</div>
                <div class="kpi-sub">Avg. Coverage: {channel_avgs[dom_ink]:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs
        tab1, tab2 = st.tabs(["📊 Interactive Dashboard & Visualization", "📄 Tabular Reports & Download"])
        
        with tab1:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### Per-Page Ink Coverage Distribution")
                
                # Plotly clustered bar chart for C, M, Y, K coverage per page
                df_bar = pd.DataFrame(results)
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=df_bar["page_num"], y=df_bar["cyan"], name="Cyan", marker_color="#0EA5E9"))
                fig_bar.add_trace(go.Bar(x=df_bar["page_num"], y=df_bar["magenta"], name="Magenta", marker_color="#EC4899"))
                fig_bar.add_trace(go.Bar(x=df_bar["page_num"], y=df_bar["yellow"], name="Yellow", marker_color="#EAB308"))
                fig_bar.add_trace(go.Bar(x=df_bar["page_num"], y=df_bar["black"], name="Black", marker_color="#1F2937"))
                
                fig_bar.update_layout(
                    barmode='group',
                    xaxis_title="Page Number",
                    yaxis_title="Coverage Percentage (%)",
                    height=350,
                    margin=dict(l=20, r=20, t=10, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_bar, width="stretch")
                
            with col2:
                st.markdown("### Total Ink Distribution Ratio")
                # Pie chart of average channel composition
                fig_pie = px.pie(
                    names=["Cyan", "Magenta", "Yellow", "Black"],
                    values=[avg_c, avg_m, avg_y, avg_k],
                    color=["Cyan", "Magenta", "Yellow", "Black"],
                    color_discrete_map={"Cyan": "#0EA5E9", "Magenta": "#EC4899", "Yellow": "#EAB308", "Black": "#1F2937"},
                    hole=0.4
                )
                fig_pie.update_layout(
                    height=350,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pie, width="stretch")
                
            st.markdown("---")
            
            # ----------------------------------------------------
            # Interactive Page Explorer
            # ----------------------------------------------------
            st.markdown("### 🔍 Page Explorer & Ink Density Heatmap")
            
            selected_page_num = st.selectbox("Select Page to View", range(1, total_pages + 1), index=0)
            p_idx = selected_page_num - 1
            page_data = results[p_idx]
            page_cost_data = cost_details[p_idx]
            
            # Get background layout RGB image
            rgb_img = get_page_preview_rgb(st.session_state.uploaded_file_path, p_idx, dpi=120)
            
            # Generate blended heatmap image
            blended_heatmap = generate_heatmap_overlay(
                rgb_img,
                page_data["tic_map"],
                page_data["over_inked_mask"],
                alpha=0.55
            )
            
            exp_col1, exp_col2, exp_col3 = st.columns([1, 1, 1])
            with exp_col1:
                st.markdown("**Original Layout Preview**")
                st.image(rgb_img, width="stretch")
            with exp_col2:
                st.markdown("**CMYK Density Heatmap & Over-Inking**")
                st.image(blended_heatmap, width="stretch")
                st.caption("🔴 Red/Magenta highlights indicate pixels exceeding the over-inking TIC limit.")
                
            with exp_col3:
                st.markdown("**Page Details**")
                
                st.metric("Total Page Print Cost", f"${page_cost_data['total_cost']:.4f}")
                st.metric("Average Page TIC", f"{page_data['avg_tic']:.2f}%")
                
                # Show individual channels progress bars
                st.markdown(f"**Cyan Channel:** {page_data['cyan']:.2f}%")
                st.progress(page_data['cyan'] / 100.0)
                st.markdown(f"**Magenta Channel:** {page_data['magenta']:.2f}%")
                st.progress(page_data['magenta'] / 100.0)
                st.markdown(f"**Yellow Channel:** {page_data['yellow']:.2f}%")
                st.progress(page_data['yellow'] / 100.0)
                st.markdown(f"**Black Channel:** {page_data['black']:.2f}%")
                st.progress(page_data['black'] / 100.0)
                
                st.markdown("---")
                st.markdown(f"**Over-Inked Area:** `{page_data['over_inked_ratio']:.2f}%` of page pixels")
                st.markdown(f"**Peak TIC:** `{page_data['max_tic']:.1f}%` (Threshold: `{tic_limit:.1f}%`)")
                st.markdown(f"**Page Dimensions:** `{page_data['width_in']:.2f}\" x {page_data['height_in']:.2f}\"` ({page_data['area_m2']:.4f} m²)")
                st.markdown(f"**Ink Volume Consumed:** `{page_cost_data['total_vol']:.4f} ml`")
                
        with tab2:
            st.markdown("### Complete Analysis Records")
            
            # Combine stats for tabular view
            tbl_rows = []
            for p, c in zip(results, cost_details):
                tbl_rows.append({
                    "Page": p["page_num"],
                    "Cyan (%)": f"{p['cyan']:.2f}%",
                    "Magenta (%)": f"{p['magenta']:.2f}%",
                    "Yellow (%)": f"{p['yellow']:.2f}%",
                    "Black (%)": f"{p['black']:.2f}%",
                    "Average TIC (%)": f"{p['avg_tic']:.2f}%",
                    "Max TIC (%)": f"{p['max_tic']:.2f}%",
                    "Over-Inked (%)": f"{p['over_inked_ratio']:.2f}%",
                    "Total Ink (ml)": f"{c['total_vol']:.4f} ml",
                    "Print Cost": f"${c['total_cost']:.4f}"
                })
            df_report = pd.DataFrame(tbl_rows)
            st.dataframe(df_report, width="stretch", hide_index=True)
            
            # Download section
            st.markdown("### 📥 Download Reports")
            d_col1, d_col2 = st.columns(2)
            
            # CSV Download
            csv_str = generate_csv_report(results, cost_details, doc_totals)
            with d_col1:
                st.download_button(
                    label="📥 Download CSV Detailed Report",
                    data=csv_str,
                    file_name=f"cmyk_analysis_{st.session_state.analysis_filename.replace('.pdf','')}.csv",
                    mime="text/csv",
                    width="stretch"
                )
                
            # PDF Download
            pdf_bytes = generate_pdf_report(
                st.session_state.analysis_filename,
                results,
                cost_details,
                doc_totals,
                user_specs,
                consumption_rate,
                tic_limit,
                engine
            )
            with d_col2:
                st.download_button(
                    label="📥 Download PDF Summary Report",
                    data=pdf_bytes,
                    file_name=f"cmyk_report_{st.session_state.analysis_filename}",
                    mime="application/pdf",
                    width="stretch"
                )
else:
    # ----------------------------------------------------
    # Welcome Layout (When no PDF is loaded)
    # ----------------------------------------------------
    st.markdown("""
    <div style="background-color: #EFF6FF; border-left: 6px solid #3B82F6; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
        <h4 style="color: #1E3A8A; margin-top: 0;">ℹ️ Get Started</h4>
        <p style="color: #1E3A8A; margin-bottom: 0;">
            Please <b>upload a PDF file</b> in the left sidebar, or click <b>"Use Sample CMYK PDF"</b> to generate a test document and preview the analytics system immediately.
        </p>
    </div>
    
    <h3>💡 How does this work?</h3>
    <p>
        Physical printers reproduce color images using <b>Cyan (C), Magenta (M), Yellow (Y), and Black (K)</b> inks. 
        Most digital PDF documents are stored in the RGB color space. To estimate print ink consumption, this system:
    </p>
    <ol>
        <li>Renders the PDF pages into high-fidelity CMYK images (using Ghostscript or a PyMuPDF vector renderer).</li>
        <li>Splits the image into individual Cyan, Magenta, Yellow, and Black channel arrays.</li>
        <li>Computes the intensity sum of each channel to determine exact coverage percentage.</li>
        <li>Checks for <b>Over-Inking</b>: Points on the page where the Total Ink Coverage (C+M+Y+K) exceeds print media absorption thresholds (e.g., 240% or 300%). Over-inking can cause wet ink smudging, paper bleeding, or mechanical damage.</li>
        <li>Calculates exact ink volumes (ml) and financial costs based on standard paper dimensions and customizable cartridge specs.</li>
    </ol>
    """, unsafe_allow_html=True)
    
    # Showcase image overlay logic with sample diagram or graphics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("##### 🎨 CMYK Split Analysis")
        st.caption("Splits vector layouts into CMYK plates to evaluate density balance.")
    with col2:
        st.markdown("##### 🔥 Peak Density Heatmaps")
        st.caption("Visually tracks saturation and ink load over individual zones.")
    with col3:
        st.markdown("##### 💰 Cost Projections")
        st.caption("Computes coverage to ml ink mapping and prints costs.")
