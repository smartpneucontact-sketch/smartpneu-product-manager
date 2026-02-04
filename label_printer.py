from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, black, white
import qrcode
import io
import os
import platform
from datetime import datetime

class TireLabelPrinter:
    def __init__(self, printer_name="Brother_DCP_L2530DW_series", black_and_white=True):
        self.width = 120 * mm
        self.height = 220 * mm
        self.printer_name = printer_name
        self.black_and_white = black_and_white  # Default to B&W for testing
        
        # Logo path - look in same directory as this script
        self.logo_path = os.path.join(os.path.dirname(__file__) or '.', 'smartpneu_logo.png')
        # Branded QR code path
        self.qr_code_path = os.path.join(os.path.dirname(__file__) or '.', 'smartpneu_qr.png')
        
    def generate_qr_code(self, url):
        """Generate QR code and return as image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Use black for QR code (works for both color and B&W)
        fill_color = "black" if self.black_and_white else "#cf343b"
        img = qr.make_image(fill_color=fill_color, back_color="white")
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return ImageReader(img_buffer)
    
    def create_label(self, product_data, output_path="label.pdf"):
        """
        Create a tire label PDF matching the smartpneu.com design
        
        product_data should contain:
        - brand: Marque (from vendor or metafield)
        - model: Model (from title or metafield)
        - largeur: Width (e.g., "205")
        - hauteur: Height (e.g., "55")
        - rayon: Radius (e.g., "16" or "R16")
        - indice_charge: Load index (e.g., "91")
        - indice_vitesse: Speed index (e.g., "V")
        - dot: DOT number
        - profondeur: Tread depth (e.g., "7mm")
        - sku: Reference/SKU
        - product_url: URL for QR code
        """
        
        c = canvas.Canvas(output_path, pagesize=(self.width, self.height))
        
        # Color scheme based on mode
        if self.black_and_white:
            header_bg = HexColor("#000000")
            accent_color = HexColor("#000000")
            border_color = HexColor("#333333")
        else:
            header_bg = HexColor("#CC0000")
            accent_color = HexColor("#CC0000")
            border_color = HexColor("#0099CC")
        
        # Header - White background for logo visibility
        c.setFillColor(HexColor("#FFFFFF"))
        c.rect(0, self.height - 30*mm, self.width, 30*mm, fill=True, stroke=False)
        
        # Draw the SmartPneu logo
        try:
            if os.path.exists(self.logo_path):
                logo_width = 100 * mm
                logo_height = 20 * mm
                logo_x = (self.width - logo_width) / 2
                logo_y = self.height - 24 * mm
                
                c.drawImage(self.logo_path, logo_x, logo_y, 
                           width=logo_width, height=logo_height,
                           preserveAspectRatio=True, mask='auto')
            else:
                c.setFillColor(HexColor("#CF343B"))
                c.setFont("Helvetica-Bold", 18)
                c.drawCentredString(self.width / 2, self.height - 18*mm, "smartpneu.com")
        except Exception as e:
            print(f"⚠️ Logo error: {e}")
            c.setFillColor(HexColor("#CF343B"))
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(self.width / 2, self.height - 18*mm, "smartpneu.com")
        
        # Tagline below logo
        c.setFillColor(HexColor("#666666"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(self.width / 2, self.height - 28*mm, "Pneus d'occasion certifiés à prix imbattables")
        
        # Body - White background
        c.setFillColor(HexColor("#FFFFFF"))
        c.rect(0, 0, self.width, self.height - 30*mm, fill=True, stroke=False)
        
        # Border
        c.setStrokeColor(border_color)
        c.setLineWidth(2)
        c.rect(2*mm, 2*mm, self.width - 4*mm, self.height - 32*mm, fill=False, stroke=True)
        
        # ── Product information ──
        y_position = self.height - 38*mm
        
        # Format dimensions properly
        rayon = product_data.get('rayon', '').replace('R', '').replace('r', '')
        dimensions = f"{product_data.get('largeur', '')} / {product_data.get('hauteur', '')} R{rayon}"
        if dimensions == " /  R":
            dimensions = "—"
        
        fields = [
            ("Marque", product_data.get('brand', '—')),
            ("Modèle", product_data.get('model', '—')),
            ("Dimensions", dimensions),
            ("Réf", product_data.get('sku', '—')),
            ("Indice de charge", product_data.get('indice_charge', '—')),
            ("Indice de vitesse", product_data.get('indice_vitesse', '—')),
            ("DOT", product_data.get('dot', '—')),
            ("Profondeur", product_data.get('profondeur', '—')),
        ]
        
        label_font_size = 10
        big_value_font_size = 26
        dimensions_font_size = 48
        ref_font_size = 42
        
        for label, value in fields:
            # Label in italic, gray
            c.setFillColor(HexColor("#666666"))
            c.setFont("Helvetica-Oblique", label_font_size)
            c.drawString(8*mm, y_position + 2*mm, label)
            
            # Value in bold, black
            c.setFillColor(HexColor("#000000"))
            if label == "Dimensions":
                c.setFont("Helvetica-Bold", dimensions_font_size)
                c.drawString(8*mm, y_position - 14*mm, str(value) if value else "—")
                y_position -= 30*mm
            elif label == "Réf":
                c.setFont("Helvetica-Bold", ref_font_size)
                c.drawString(8*mm, y_position - 12*mm, str(value) if value else "—")
                y_position -= 28*mm
            else:
                c.setFont("Helvetica-Bold", big_value_font_size)
                c.drawString(8*mm, y_position - 7*mm, str(value) if value else "—")
                y_position -= 18*mm
        
        # QR Code - branded image, bottom right
        qr_size = 30*mm
        try:
            if os.path.exists(self.qr_code_path):
                c.drawImage(self.qr_code_path, 
                           self.width - qr_size - 6*mm,
                           6*mm,
                           width=qr_size, 
                           height=qr_size,
                           preserveAspectRatio=True,
                           mask='auto')
            else:
                qr_image = self.generate_qr_code(product_data.get('product_url', 'https://smartpneu.com'))
                c.drawImage(qr_image, 
                           self.width - qr_size - 6*mm,
                           6*mm,
                           width=qr_size, 
                           height=qr_size)
        except Exception as e:
            print(f"⚠️ QR code error: {e}")
        
        # Phone number at bottom left
        c.setFont("Helvetica-Bold", 14)
        c.drawString(8*mm, 8*mm, "Tel : 09 70 70 71 36")
        
        c.save()
        return output_path
    
    def print_label(self, pdf_path):
        """Send PDF to printer"""
        system = platform.system()
        
        try:
            if system == "Windows":
                # Windows printing using win32print
                import win32print
                import win32api
                
                win32api.ShellExecute(
                    0,
                    "print",
                    pdf_path,
                    f'/d:"{self.printer_name}"',
                    ".",
                    0
                )
                return True
                
            elif system == "Linux" or system == "Darwin":  # Linux or macOS
                # Use CUPS/lp command
                # Brother DCP-L2530DW: Custom size + labels + manual tray
                media_options = "-o media=Custom.120x220mm,labels -o InputSlot=manual"
                if self.black_and_white:
                    # B&W printing options
                    bw_options = "-o print-color-mode=monochrome -o ColorModel=Gray"
                    cmd = f'lp -d {self.printer_name} {media_options} {bw_options} {pdf_path}'
                else:
                    # Color printing
                    cmd = f'lp -d {self.printer_name} {media_options} {pdf_path}'
                
                print(f"🖨️  Print command: {cmd}")
                result = os.system(cmd)
                return result == 0
            else:
                print(f"Unsupported OS: {system}")
                return False
                
        except Exception as e:
            print(f"Error printing: {str(e)}")
            return False
    
    def generate_and_print(self, product_data, print_enabled=True):
        """
        Generate label and optionally print it automatically
        
        Args:
            product_data: Dictionary with tire information
            print_enabled: If True, automatically print. If False, only generate PDF
            
        Returns:
            Path to generated PDF file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sku = product_data.get('sku', timestamp)
        pdf_path = f"labels/label_{sku}.pdf"
        
        # Create labels directory if it doesn't exist
        os.makedirs("labels", exist_ok=True)
        
        # Generate label
        self.create_label(product_data, pdf_path)
        mode = "B&W" if self.black_and_white else "Color"
        print(f"✅ Label generated ({mode}): {pdf_path}")
        
        # Print label if enabled
        if print_enabled:
            success = self.print_label(pdf_path)
            if success:
                print(f"🖨️  Label sent to printer: {self.printer_name}")
            else:
                print("⚠️  Failed to print label - PDF saved for manual printing")
        
        return pdf_path


# Standalone test function
if __name__ == "__main__":
    # Test the label printer in B&W mode
    printer = TireLabelPrinter(black_and_white=True)
    
    test_data = {
        'brand': 'Michelin',
        'model': 'Pilot Sport 4',
        'largeur': '225',
        'hauteur': '45',
        'rayon': '17',
        'indice_charge': '94',
        'indice_vitesse': 'Y',
        'dot': '3419',
        'profondeur': '7mm',
        'sku': 'TEST-001',
        'product_url': 'https://smartpneu.com/products/test'
    }
    
    # Generate without printing (for testing)
    pdf_path = printer.generate_and_print(test_data, print_enabled=False)
    print(f"\nTest label created at: {pdf_path}")
    print("Open this file to verify the label design before enabling automatic printing.")
