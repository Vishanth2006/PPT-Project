from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def create_sample_pdf(file_path):
    """
    Generates a 2-page sample PDF with CMYK elements to test the analyzer.
    """
    c = canvas.Canvas(file_path, pagesize=letter)
    
    # Page 1: CMYK Solid shapes & Over-inking box
    c.setFont("Helvetica-Bold", 24)
    c.drawString(80, 720, "CMYK Ink Analyzer Test Page 1")
    
    c.setFont("Helvetica", 10.5)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawString(80, 690, "This page simulates solid printer inks to test CMYK channel split logic.")
    
    # 1. Cyan Block
    c.setFillColor(colors.CMYKColor(1, 0, 0, 0)) # 100% Cyan
    c.rect(80, 520, 90, 120, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(80, 500, "Cyan (100%)")
    
    # 2. Magenta Block
    c.setFillColor(colors.CMYKColor(0, 1, 0, 0)) # 100% Magenta
    c.rect(190, 520, 90, 120, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(190, 500, "Magenta (100%)")
    
    # 3. Yellow Block
    c.setFillColor(colors.CMYKColor(0, 0, 1, 0)) # 100% Yellow
    c.rect(300, 520, 90, 120, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(300, 500, "Yellow (100%)")
    
    # 4. Black Block
    c.setFillColor(colors.CMYKColor(0, 0, 0, 1)) # 100% Black
    c.rect(410, 520, 90, 120, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(410, 500, "Black (100%)")
    
    # 5. Over-inking Zone (TIC = 85% C + 85% M + 80% Y + 80% K = 330% TIC)
    c.setFillColor(colors.CMYKColor(0.85, 0.85, 0.80, 0.80))
    c.rect(80, 260, 420, 180, fill=True, stroke=False)
    
    # Label over-inking
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 360, "High Total Ink Coverage Zone")
    c.setFont("Helvetica", 10.5)
    c.drawString(100, 340, "TIC: 330% (C:85%, M:85%, Y:80%, K:80%)")
    c.drawString(100, 320, "This area triggers the over-inking warning threshold (>240%).")
    
    c.showPage()
    
    # Page 2: Text page with typical ink densities
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(80, 720, "CMYK Ink Analyzer Test Page 2")
    
    c.setFont("Helvetica", 10.5)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawString(80, 690, "This page simulates a standard monochrome text document layout.")
    
    # Text lines (90% Black)
    c.setFillColor(colors.CMYKColor(0, 0, 0, 0.9))
    c.setFont("Helvetica", 11)
    y = 630
    for i in range(20):
        c.drawString(80, y, f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Line {i+1} of simulated page body text.")
        y -= 22
        
    c.showPage()
    c.save()
