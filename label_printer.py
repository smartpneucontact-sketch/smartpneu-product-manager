from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
import qrcode
import io
import os
import platform
from datetime import datetime

class TireLabelPrinter:
    def __init__(self, printer_name="HP_Color_LaserJet_MFP_M179fnw"):
        self.width = 70 * mm
        self.height = 170 * mm
        self.printer_name = printer_name
        
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
        
        # Create image with red fill color
        img = qr.make_image(fill_color="#CC0000", back_color="white")
        
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
        
        # Header - Red background with smartpneu branding
        c.setFillColor(HexColor("#CC0000"))
        c.rect(0, self.height - 35*mm, self.width, 35*mm, fill=True, stroke=False)
        
        # White "sp" logo area (simplified as text, you can replace with actual logo)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 20)
        c.drawString(5*mm, self.height - 18*mm, "sp")
        
        # Company name and info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(15*mm, self.height - 12*mm, "smartpneu.com")
        
        c.setFont("Helvetica", 6)
        c.drawString(15*mm, self.height - 17*mm, "Point d'occasion certifiée à prix imbattables.")
        c.drawString(15*mm, self.height - 21*mm, "Livraison rapide et retours gratuits sous 21 jours.")
        c.drawString(15*mm, self.height - 25*mm, "Qualité, sécurité et économie garanties.")
        
        # Body - White background
        c.setFillColor(HexColor("#FFFFFF"))
        c.rect(0, 0, self.width, self.height - 35*mm, fill=True, stroke=False)
        
        # Blue border
        c.setStrokeColor(HexColor("#0099CC"))
        c.setLineWidth(2)
        c.rect(2*mm, 2*mm, self.width - 4*mm, self.height - 37*mm, fill=False, stroke=True)
        
        # Product information
        c.setFillColor(HexColor("#000000"))
        c.setFont("Helvetica", 9)
        
        y_position = self.height - 45*mm
        line_height = 10*mm
        
        # Format dimensions properly
        rayon = product_data.get('rayon', '').replace('R', '').replace('r', '')
        dimensions = f"{product_data.get('largeur', '')}/"
        dimensions += f"{product_data.get('hauteur', '')} R{rayon}"
        
        fields = [
            ("Marque :", product_data.get('brand', '.....................').ljust(20, '.')),
            ("Model :", product_data.get('model', '.....................').ljust(20, '.')),
            ("Dimensions :", dimensions if dimensions != "/ R" else '.....................'),
            ("Indice de charge :", product_data.get('indice_charge', '...............').ljust(15, '.')),
            ("Indice de vitesse :", product_data.get('indice_vitesse', '...............').ljust(15, '.')),
            ("DOT :", product_data.get('dot', '.....................').ljust(20, '.')),
            ("Profondeur :", product_data.get('profondeur', '.....................').ljust(20, '.')),
            ("Ref :", product_data.get('sku', '.....................').ljust(20, '.')),
        ]
        
        for label, value in fields:
            c.drawString(5*mm, y_position, f"{label} {value}")
            y_position -= line_height
        
        # QR Code
        qr_image = self.generate_qr_code(product_data.get('product_url', 'https://smartpneu.com'))
        qr_size = 30*mm
        c.drawImage(qr_image, 
                   (self.width - qr_size) / 2,  # Center horizontally
                   25*mm,
                   width=qr_size, 
                   height=qr_size)
        
        # Phone number at bottom
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(self.width / 2, 15*mm, "09 70 70 71 36")
        
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
                result = os.system(f'lp -d "{self.printer_name}" "{pdf_path}"')
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
        print(f"✅ Label generated: {pdf_path}")
        
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
    # Test the label printer
    printer = TireLabelPrinter()
    
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
