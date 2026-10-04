"""QR code generation service."""
import io
import base64
from typing import Optional

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
        base_url: str = "http://localhost:3000"
    ) -> str:
        """
        Generate QR code as base64 data URI.

        Args:
            public_token: Public token for the invoice
            size: QR code size (box_size parameter)
            base_url: Base URL for bill page link

        Returns:
            data:image/png;base64,... string
        """
        if not QRCODE_AVAILABLE:
            raise RuntimeError("qrcode library not installed")

        # QR code contains URL to public bill page
        qr_url = f"{base_url}/bill/{public_token}"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=2,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        img_base64 = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_base64}"

    def generate_qr_png(
        self,
        public_token: str,
        size: int = 10,
        base_url: str = "http://localhost:3000"
    ) -> bytes:
        """
        Generate QR code as PNG bytes.

        Args:
            public_token: Public token for the invoice
            size: QR code size (box_size parameter)
            base_url: Base URL for bill page link

        Returns:
            PNG image bytes
        """
        if not QRCODE_AVAILABLE:
            raise RuntimeError("qrcode library not installed")

        # QR code contains URL to public bill page
        qr_url = f"{base_url}/bill/{public_token}"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=2,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to PNG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


# Global instance
qr_service = QRService()
