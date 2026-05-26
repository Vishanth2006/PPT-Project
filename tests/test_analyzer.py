import os
import sys
import tempfile
import unittest
from PIL import Image

# Adjust path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from analyzer import process_pdf, get_page_preview_rgb, generate_heatmap_overlay, validate_pdf
from cost_estimator import get_default_cartridge_specs, estimate_document_printing_costs
from report_generator import generate_csv_report, generate_pdf_report
from sample_generator import create_sample_pdf

class TestCMYKAnalyzer(unittest.TestCase):
    def setUp(self):
        # Create a temporary PDF to run tests on
        self.temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        self.temp_pdf.close()
        create_sample_pdf(self.temp_pdf.name)

    def tearDown(self):
        # Clean up temporary PDF
        if os.path.exists(self.temp_pdf.name):
            os.remove(self.temp_pdf.name)

    def test_validation(self):
        valid, msg = validate_pdf(self.temp_pdf.name)
        self.assertTrue(valid)
        self.assertIn("Valid PDF with 2 pages", msg)

        # Test non-existent file
        valid_bad, msg_bad = validate_pdf("non_existent_file.pdf")
        self.assertFalse(valid_bad)
        self.assertIn("does not exist", msg_bad.lower())

    def test_processing_and_analysis(self):
        # Run process_pdf (default to PyMuPDF fallback if Ghostscript is not in PATH)
        results, engine = process_pdf(self.temp_pdf.name, dpi=100, tic_limit=240.0)
        
        self.assertEqual(len(results), 2)
        
        page1 = results[0]
        page2 = results[1]
        
        # Verify page numbers
        self.assertEqual(page1["page_num"], 1)
        self.assertEqual(page2["page_num"], 2)
        
        # Assertions on page 1 (which contains large solid shapes C, M, Y, K)
        # It should have significant coverage on all channels
        self.assertGreater(page1["cyan"], 0.0)
        self.assertGreater(page1["magenta"], 0.0)
        self.assertGreater(page1["yellow"], 0.0)
        self.assertGreater(page1["black"], 0.0)
        
        # Page 1 contains a high TIC area (330% TIC)
        # So over-inked ratio must be greater than 0%
        self.assertGreater(page1["over_inked_ratio"], 0.0)
        self.assertGreater(page1["max_tic"], 300.0)
        
        # Assertions on page 2 (standard monochrome text)
        # It should have black coverage, but cyan/magenta/yellow should be close to 0.0
        self.assertGreater(page2["black"], 0.0)
        self.assertLess(page2["cyan"], 1.0)
        self.assertLess(page2["magenta"], 1.0)
        self.assertLess(page2["yellow"], 1.0)
        
        # Monochrome text should not exceed the over-inking limit (permitting small anti-aliasing edge artifacts)
        self.assertLess(page2["over_inked_ratio"], 1.0)

    def test_cost_estimator(self):
        results, _ = process_pdf(self.temp_pdf.name, dpi=100, tic_limit=240.0)
        specs = get_default_cartridge_specs()
        
        cost_details, doc_totals = estimate_document_printing_costs(results, specs, consumption_rate_ml_m2=1.5)
        
        # Cost details list should correspond to pages
        self.assertEqual(len(cost_details), 2)
        
        # Totals check
        self.assertGreater(doc_totals["total_vol"], 0.0)
        self.assertGreater(doc_totals["total_cost"], 0.0)
        
        # Verify that page 1 (high coverage) is more expensive than page 2 (text page)
        self.assertGreater(cost_details[0]["total_cost"], cost_details[1]["total_cost"])

    def test_reports(self):
        results, engine = process_pdf(self.temp_pdf.name, dpi=100, tic_limit=240.0)
        specs = get_default_cartridge_specs()
        cost_details, doc_totals = estimate_document_printing_costs(results, specs, consumption_rate_ml_m2=1.5)
        
        # Test CSV Report Generation
        csv_report = generate_csv_report(results, cost_details, doc_totals)
        self.assertIn("Page", csv_report)
        self.assertIn("Cyan Coverage (%)", csv_report)
        self.assertIn("DOCUMENT TOTALS", csv_report)
        
        # Test PDF Report Generation
        pdf_report = generate_pdf_report(
            "sample_cmyk_test.pdf",
            results,
            cost_details,
            doc_totals,
            specs,
            1.5,
            240.0,
            engine
        )
        self.assertIsInstance(pdf_report, bytes)
        # PDF files start with %PDF header
        self.assertTrue(pdf_report.startswith(b"%PDF"))

    def test_visualization_overlays(self):
        # Render a page and overlay heatmap
        results, _ = process_pdf(self.temp_pdf.name, dpi=100, tic_limit=240.0)
        page1 = results[0]
        
        rgb_img = get_page_preview_rgb(self.temp_pdf.name, 0, dpi=100)
        self.assertIsInstance(rgb_img, Image.Image)
        
        blended = generate_heatmap_overlay(
            rgb_img,
            page1["tic_map"],
            page1["over_inked_mask"],
            alpha=0.5
        )
        self.assertIsInstance(blended, Image.Image)
        self.assertEqual(blended.size, rgb_img.size)

if __name__ == "__main__":
    unittest.main()
