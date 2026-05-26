import io
import csv
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically calculate and draw total page numbers and page headers/footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4B5563"))
        
        # Header (on pages after page 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "PDF CMYK Ink Coverage Report")
            self.setStrokeColor(colors.HexColor("#E5E7EB"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
            
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_text)
        self.drawString(54, 40, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.setStrokeColor(colors.HexColor("#E5E7EB"))
        self.setLineWidth(0.5)
        self.line(54, 52, 558, 52)
        
        self.restoreState()


def generate_csv_report(page_results, cost_details, doc_totals):
    """
    Generates a CSV report string containing detailed page-by-page results.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Page", "Width (in)", "Height (in)", "Area (m2)",
        "Cyan Coverage (%)", "Magenta Coverage (%)", "Yellow Coverage (%)", "Black Coverage (%)",
        "Average TIC (%)", "Maximum TIC (%)", "Over-Inked Ratio (%)",
        "Cyan Ink (ml)", "Magenta Ink (ml)", "Yellow Ink (ml)", "Black Ink (ml)",
        "Total Ink Volume (ml)", "Estimated Cost ($)"
    ])
    
    # Rows
    for p, c in zip(page_results, cost_details):
        writer.writerow([
            p["page_num"],
            f"{p['width_in']:.2f}",
            f"{p['height_in']:.2f}",
            f"{p['area_m2']:.4f}",
            f"{p['cyan']:.2f}",
            f"{p['magenta']:.2f}",
            f"{p['yellow']:.2f}",
            f"{p['black']:.2f}",
            f"{p['avg_tic']:.2f}",
            f"{p['max_tic']:.2f}",
            f"{p['over_inked_ratio']:.2f}",
            f"{c['cyan_vol']:.4f}",
            f"{c['magenta_vol']:.4f}",
            f"{c['yellow_vol']:.4f}",
            f"{c['black_vol']:.4f}",
            f"{c['total_vol']:.4f}",
            f"{c['total_cost']:.4f}"
        ])
        
    # Summary Row
    writer.writerow([])
    writer.writerow(["DOCUMENT TOTALS / AVERAGES"])
    
    avg_cyan = sum(p["cyan"] for p in page_results) / len(page_results)
    avg_magenta = sum(p["magenta"] for p in page_results) / len(page_results)
    avg_yellow = sum(p["yellow"] for p in page_results) / len(page_results)
    avg_black = sum(p["black"] for p in page_results) / len(page_results)
    avg_tic = sum(p["avg_tic"] for p in page_results) / len(page_results)
    avg_over_inked = sum(p["over_inked_ratio"] for p in page_results) / len(page_results)
    
    writer.writerow([
        "Total/Avg", "-", "-", f"{sum(p['area_m2'] for p in page_results):.4f}",
        f"{avg_cyan:.2f} (Avg)", f"{avg_magenta:.2f} (Avg)", f"{avg_yellow:.2f} (Avg)", f"{avg_black:.2f} (Avg)",
        f"{avg_tic:.2f} (Avg)", "-", f"{avg_over_inked:.2f} (Avg)",
        f"{doc_totals['cyan_vol']:.4f}", f"{doc_totals['magenta_vol']:.4f}",
        f"{doc_totals['yellow_vol']:.4f}", f"{doc_totals['black_vol']:.4f}",
        f"{doc_totals['total_vol']:.4f}", f"{doc_totals['total_cost']:.4f}"
    ])
    
    return output.getvalue()


def generate_pdf_report(pdf_filename, page_results, cost_details, doc_totals, cartridge_specs, consumption_rate, tic_limit, engine_name):
    """
    Generates a beautifully formatted ReportLab PDF report of the analysis.
    Returns bytes of the generated PDF.
    """
    buffer = io.BytesIO()
    
    # Page setup: letter has margins (54pt = 0.75in)
    # Target height/width for contents: letter is 612 x 792 pt
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#1E3A8A")   # Deep Blue
    secondary_color = colors.HexColor("#3B82F6") # Vibrant Blue
    neutral_dark = colors.HexColor("#1F2937")    # Dark Charcoal
    neutral_light = colors.HexColor("#F9FAFB")   # Cool White/Grey
    warning_bg = colors.HexColor("#FEF2F2")      # Light Red
    warning_text = colors.HexColor("#991B1B")    # Crimson Red
    border_color = colors.HexColor("#E5E7EB")
    
    # Modify existing styles to avoid conflicts
    styles['Normal'].textColor = neutral_dark
    styles['Normal'].fontSize = 10
    styles['Normal'].leading = 14
    
    # Add new unique styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=15
    )
    
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    kpi_title_style = ParagraphStyle(
        'KPITitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4B5563"),
        alignment=1 # Center
    )
    
    kpi_value_style = ParagraphStyle(
        'KPIValue',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        alignment=1 # Center
    )
    
    tbl_header_style = ParagraphStyle(
        'TblHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1 # Center
    )
    
    tbl_cell_style = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        alignment=1 # Center
    )
    
    tbl_cell_bold = ParagraphStyle(
        'TblCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1 # Center
    )
    
    tbl_cell_warning = ParagraphStyle(
        'TblCellWarning',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=warning_text,
        alignment=1 # Center
    )

    story = []
    
    # ----------------------------------------------------
    # Header Section
    # ----------------------------------------------------
    story.append(Paragraph("PDF CMYK Print Analysis Report", title_style))
    story.append(Paragraph(f"Source Document: {pdf_filename} | Run Date: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # ----------------------------------------------------
    # KPI Grid (Summary Cards)
    # ----------------------------------------------------
    total_pages = len(page_results)
    avg_c = sum(p["cyan"] for p in page_results) / total_pages
    avg_m = sum(p["magenta"] for p in page_results) / total_pages
    avg_y = sum(p["yellow"] for p in page_results) / total_pages
    avg_k = sum(p["black"] for p in page_results) / total_pages
    avg_tic = avg_c + avg_m + avg_y + avg_k
    
    # Find dominant ink
    channel_avgs = {"Cyan": avg_c, "Magenta": avg_m, "Yellow": avg_y, "Black": avg_k}
    dom_ink = max(channel_avgs, key=channel_avgs.get)
    
    # Find highest ink consuming page
    max_page = max(page_results, key=lambda x: x["avg_tic"])
    
    kpi_data = [
        [
            Paragraph("Total Pages", kpi_title_style),
            Paragraph("Total Est. Cost", kpi_title_style),
            Paragraph("Avg. Page TIC", kpi_title_style),
            Paragraph("Dominant Ink", kpi_title_style)
        ],
        [
            Paragraph(str(total_pages), kpi_value_style),
            Paragraph(f"${doc_totals['total_cost']:.3f}", kpi_value_style),
            Paragraph(f"{avg_tic:.1f}%", kpi_value_style),
            Paragraph(f"{dom_ink} ({channel_avgs[dom_ink]:.1f}%)", kpi_value_style)
        ]
    ]
    
    # Width: total 504 (612 - 108 margin) -> 126 per column
    kpi_table = Table(kpi_data, colWidths=[126, 126, 126, 126])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), neutral_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(kpi_table)
    story.append(Spacer(1, 15))
    
    # ----------------------------------------------------
    # Configuration and Metadata
    # ----------------------------------------------------
    story.append(Paragraph("Analysis Parameters & Ink Rates", section_heading))
    
    config_data = [
        [
            Paragraph("<b>Rendering Engine:</b>", tbl_cell_style),
            Paragraph(engine_name, tbl_cell_style),
            Paragraph("<b>Ink Coverage Rate:</b>", tbl_cell_style),
            Paragraph(f"{consumption_rate:.1f} ml/m² (100% cover)", tbl_cell_style)
        ],
        [
            Paragraph("<b>Over-Inking Limit (TIC):</b>", tbl_cell_style),
            Paragraph(f"{tic_limit:.1f}%", tbl_cell_style),
            Paragraph("<b>Total Ink Consumed:</b>", tbl_cell_style),
            Paragraph(f"{doc_totals['total_vol']:.3f} ml", tbl_cell_style)
        ]
    ]
    
    config_table = Table(config_data, colWidths=[130, 122, 130, 122])
    config_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,-1), neutral_light),
        ('BACKGROUND', (2,0), (2,-1), neutral_light),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    
    story.append(config_table)
    story.append(Spacer(1, 10))
    
    # Cartridge Specs Table
    cartridge_data = [
        [
            Paragraph("Ink Channel", tbl_header_style),
            Paragraph("Cartridge Volume", tbl_header_style),
            Paragraph("Cartridge Price", tbl_header_style),
            Paragraph("Calculated Cost / ml", tbl_header_style)
        ]
    ]
    for c_name in ["cyan", "magenta", "yellow", "black"]:
        spec = cartridge_specs[c_name]
        cost_per_ml = spec["price"] / spec["volume"] if spec["volume"] > 0 else 0
        cartridge_data.append([
            Paragraph(f"<b>{c_name.capitalize()}</b>", tbl_cell_style),
            Paragraph(f"{spec['volume']:.1f} ml", tbl_cell_style),
            Paragraph(f"${spec['price']:.2f}", tbl_cell_style),
            Paragraph(f"${cost_per_ml:.3f} / ml", tbl_cell_style)
        ])
        
    cartridge_table = Table(cartridge_data, colWidths=[126, 126, 126, 126])
    cartridge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, neutral_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(cartridge_table)
    story.append(Spacer(1, 15))
    
    # ----------------------------------------------------
    # Page-by-Page Table (KeepTogether or PageBreak before)
    # ----------------------------------------------------
    page_story = []
    page_story.append(Paragraph("Detailed Page-by-Page Statistics", section_heading))
    
    page_headers = [
        Paragraph("Page", tbl_header_style),
        Paragraph("Cyan %", tbl_header_style),
        Paragraph("Mag %", tbl_header_style),
        Paragraph("Yel %", tbl_header_style),
        Paragraph("Blk %", tbl_header_style),
        Paragraph("TIC %", tbl_header_style),
        Paragraph("Max TIC", tbl_header_style),
        Paragraph("Over-Inked %", tbl_header_style),
        Paragraph("Est. Cost", tbl_header_style)
    ]
    
    page_table_data = [page_headers]
    
    for p, c in zip(page_results, cost_details):
        is_over_inked = p["over_inked_ratio"] > 0
        
        # Decide paragraph styling
        c_style = tbl_cell_style
        m_style = tbl_cell_style
        y_style = tbl_cell_style
        k_style = tbl_cell_style
        tic_style = tbl_cell_bold
        max_tic_style = tbl_cell_style
        
        over_inked_style = tbl_cell_warning if is_over_inked else tbl_cell_style
        cost_style = tbl_cell_bold
        
        row = [
            Paragraph(f"<b>{p['page_num']}</b>", tbl_cell_style),
            Paragraph(f"{p['cyan']:.1f}%", c_style),
            Paragraph(f"{p['magenta']:.1f}%", m_style),
            Paragraph(f"{p['yellow']:.1f}%", y_style),
            Paragraph(f"{p['black']:.1f}%", k_style),
            Paragraph(f"{p['avg_tic']:.1f}%", tic_style),
            Paragraph(f"{p['max_tic']:.1f}%", max_tic_style),
            Paragraph(f"{p['over_inked_ratio']:.1f}%", over_inked_style),
            Paragraph(f"${c['total_cost']:.3f}", cost_style)
        ]
        
        page_table_data.append(row)
        
    # Column widths (total must be 504)
    # Page (40), C(50), M(50), Y(50), K(50), TIC(55), MaxTIC(65), OverInked(75), Cost(69) = 504
    page_table = Table(page_table_data, colWidths=[40, 50, 50, 50, 50, 55, 65, 75, 69])
    
    # Table Styling
    page_table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, neutral_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ])
    
    # Apply warning background to over-inked pages
    for i, p in enumerate(page_results):
        if p["over_inked_ratio"] > 0.0:
            page_table_style.add('BACKGROUND', (0, i+1), (-1, i+1), warning_bg)
            
    page_table.setStyle(page_table_style)
    page_story.append(page_table)
    
    story.append(KeepTogether(page_story))
    
    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    
    buffer.seek(0)
    return buffer.getvalue()
