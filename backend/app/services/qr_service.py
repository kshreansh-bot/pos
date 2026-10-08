"""QR code generation service."""
import io
import base64

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class QRService:
    """Service for generating QR codes for invoices."""

    def generate_qr_data_uri(
        self,
        public_token: str,
        size: int = 10,
        base_url: str  = "http://10.86.185.246:5173"
    ) -> str:
        """
        Generate QR code as base64 data URI.
        """
        if not QRCODE_AVAILABLE:
            raise RuntimeError("qrcode library not installed")

        # URL to the digital bill
        qr_url =f"http://10.86.185.246:5173/api/bills/{public_token}/html"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=2,
        )

        qr.add_data(qr_url)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        img_base64 = base64.b64encode(
            buffer.read()
        ).decode()

        return f"data:image/png;base64,{img_base64}"

    def generate_qr_png(
        self,
        public_token: str,
        size: int = 10,
        base_url: str = "http://localhost:5173"
    ) -> bytes:
        """
        Generate QR code as PNG bytes.
        """
        if not QRCODE_AVAILABLE:
            raise RuntimeError("qrcode library not installed")

        # URL to the digital bill
        qr_url = f"http://10.86.185.246:5173/api/bills/{public_token}/html"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=2,
        )

        qr.add_data(qr_url)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        return buffer.getvalue()


# Global instance
qr_service = QRService()