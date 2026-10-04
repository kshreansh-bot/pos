"""API routes for public bill pages (no authentication required)."""
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.services.billing_service import billing_service
from app.services.qr_service import qr_service
from app.utils.errors import AppException
from app.utils.money import paise_to_rupees
from datetime import datetime

router = APIRouter(prefix="/api/bills", tags=["public"])


@router.get("/{public_token}", response_model=dict)
async def get_bill_json(
    public_token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get bill details as JSON (no authentication required).

    Rate limit: 100 per IP per minute (to be implemented at middleware level)
    """
    invoice = await billing_service.get_invoice_by_token(session, public_token)
    if not invoice:
        raise AppException("Bill not found", status_code=404)

    # Group items by tax rate
    tax_groups = billing_service.group_tax_by_rate(invoice.items)

    return {
        "invoice_number": invoice.invoice_number,
        "created_at": invoice.created_at.isoformat(),
        "customer": {
            "name": invoice.customer.name if invoice.customer else "Walk-in Customer"
        },
        "items": [
            {
                "product_name": item.product_name,
                "product_barcode": item.product_barcode,
                "product_unit": item.product_unit,
                "quantity": item.quantity,
                "unit_price_rupees": paise_to_rupees(item.unit_price_paise),
                "gst_rate": item.gst_rate,
                "discount_percent": item.discount_percent,
                "discount_rupees": paise_to_rupees(item.discount_paise),
                "tax_amount_rupees": paise_to_rupees(item.tax_amount_paise),
                "line_total_rupees": paise_to_rupees(item.line_total_paise),
            }
            for item in invoice.items
        ],
        "subtotal_rupees": paise_to_rupees(invoice.subtotal_paise),
        "discount_rupees": paise_to_rupees(invoice.total_discount_paise),
        "tax_breakdown": [
            {
                "gst_rate": rate,
                "base_amount_rupees": paise_to_rupees(data["base_amount_paise"]),
                "tax_amount_rupees": paise_to_rupees(data["tax_amount_paise"]),
                "total_rupees": paise_to_rupees(data["total_paise"]),
            }
            for rate, data in sorted(tax_groups.items())
        ],
        "total_tax_rupees": paise_to_rupees(invoice.total_tax_paise),
        "total_amount_rupees": paise_to_rupees(invoice.total_amount_paise),
        "payment_method": invoice.payment_method,
        "amount_tendered_rupees": paise_to_rupees(invoice.amount_tendered_paise) if invoice.amount_tendered_paise else None,
        "change_due_rupees": paise_to_rupees(invoice.change_due_paise) if invoice.change_due_paise else None,
        "status": invoice.status.value,
        "public_token": invoice.public_token,
    }


@router.get("/{public_token}/html", response_class=HTMLResponse)
async def get_bill_html(
    public_token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get bill as mobile-friendly HTML page (no authentication required).

    Rate limit: 100 per IP per minute (to be implemented at middleware level)
    """
    invoice = await billing_service.get_invoice_by_token(session, public_token)
    if not invoice:
        raise AppException("Bill not found", status_code=404)

    # Group items by tax rate
    tax_groups = billing_service.group_tax_by_rate(invoice.items)

    # Generate QR code as data URI
    qr_data_uri = qr_service.generate_qr_data_uri(
        public_token,
        base_url="/bill"  # Relative URL for public page
    )

    customer_name = invoice.customer.name if invoice.customer else "Walk-in Customer"

    # Build items table rows
    items_html = ""
    for item in invoice.items:
        items_html += f"""
        <tr>
            <td class="product-name">{item.product_name}</td>
            <td class="quantity">{item.quantity}</td>
            <td class="unit-price">₹{paise_to_rupees(item.unit_price_paise):.2f}</td>
            <td class="gst">{item.gst_rate}%</td>
            <td class="line-total">₹{paise_to_rupees(item.line_total_paise):.2f}</td>
        </tr>
        """

    # Build tax breakdown rows
    tax_breakdown_html = ""
    for rate, data in sorted(tax_groups.items()):
        tax_breakdown_html += f"""
        <tr>
            <td>{rate}%</td>
            <td class="amount">₹{paise_to_rupees(data['base_amount_paise']):.2f}</td>
            <td class="amount">₹{paise_to_rupees(data['tax_amount_paise']):.2f}</td>
            <td class="amount">₹{paise_to_rupees(data['total_paise']):.2f}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Invoice {invoice.invoice_number}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f5f5f5;
                color: #333;
                padding: 16px;
            }}

            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: white;
                border-radius: 8px;
                padding: 24px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}

            .header {{
                text-align: center;
                border-bottom: 2px solid #2c3e50;
                padding-bottom: 16px;
                margin-bottom: 20px;
            }}

            .header h1 {{
                font-size: 24px;
                margin-bottom: 4px;
                color: #2c3e50;
            }}

            .header p {{
                font-size: 14px;
                color: #666;
                margin: 4px 0;
            }}

            .customer-info {{
                background-color: #f9f9f9;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 16px;
                font-size: 14px;
            }}

            .customer-info label {{
                font-weight: 600;
                color: #666;
            }}

            .customer-info value {{
                color: #333;
                display: block;
            }}

            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                font-size: 13px;
            }}

            .items-table thead {{
                background-color: #2c3e50;
                color: white;
            }}

            .items-table th {{
                padding: 10px;
                text-align: left;
                font-weight: 600;
            }}

            .items-table td {{
                padding: 10px;
                border-bottom: 1px solid #eee;
            }}

            .items-table tbody tr:hover {{
                background-color: #f9f9f9;
            }}

            .product-name {{
                font-weight: 500;
            }}

            .quantity, .unit-price, .gst, .line-total {{
                text-align: right;
            }}

            .summary-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                font-size: 14px;
            }}

            .summary-table tr td:first-child {{
                padding: 8px 0;
            }}

            .summary-table tr td:last-child {{
                text-align: right;
                padding: 8px 0;
                font-weight: 500;
            }}

            .summary-divider {{
                border-top: 2px solid #2c3e50;
            }}

            .total-row {{
                font-size: 18px;
                font-weight: 700;
                color: #2c3e50;
            }}

            .tax-breakdown {{
                background-color: #f9f9f9;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 12px;
            }}

            .tax-breakdown-table {{
                width: 100%;
                border-collapse: collapse;
            }}

            .tax-breakdown-table th {{
                background-color: #e8e8e8;
                padding: 8px;
                text-align: left;
                font-weight: 600;
            }}

            .tax-breakdown-table td {{
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }}

            .tax-breakdown-table .amount {{
                text-align: right;
            }}

            .payment-info {{
                background-color: #f0f8ff;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 14px;
            }}

            .payment-info-row {{
                display: flex;
                justify-content: space-between;
                margin: 6px 0;
            }}

            .payment-info-label {{
                font-weight: 600;
                color: #666;
            }}

            .payment-info-value {{
                color: #333;
            }}

            .qr-code {{
                text-align: center;
                margin: 20px 0;
                padding: 16px;
                background-color: #f9f9f9;
                border-radius: 4px;
            }}

            .qr-code img {{
                max-width: 200px;
                width: 100%;
            }}

            .footer {{
                text-align: center;
                padding-top: 16px;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #999;
            }}

            @media print {{
                body {{
                    background-color: white;
                    padding: 0;
                }}
                .container {{
                    box-shadow: none;
                    padding: 0;
                    max-width: 100%;
                }}
                .no-print {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Invoice</h1>
                <p><strong>{invoice.invoice_number}</strong></p>
                <p>{invoice.created_at.strftime('%d-%m-%Y %H:%M:%S')}</p>
            </div>

            <div class="customer-info">
                <label>Customer:</label>
                <value>{customer_name}</value>
            </div>

            <table class="items-table">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th class="quantity">Qty</th>
                        <th class="unit-price">Price</th>
                        <th class="gst">GST</th>
                        <th class="line-total">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <table class="summary-table">
                <tr>
                    <td>Subtotal</td>
                    <td>₹{paise_to_rupees(invoice.subtotal_paise):.2f}</td>
                </tr>
                <tr>
                    <td>Discount</td>
                    <td>₹{paise_to_rupees(invoice.total_discount_paise):.2f}</td>
                </tr>
                <tr>
                    <td>Total Tax</td>
                    <td>₹{paise_to_rupees(invoice.total_tax_paise):.2f}</td>
                </tr>
                <tr class="summary-divider total-row">
                    <td>Total Amount</td>
                    <td>₹{paise_to_rupees(invoice.total_amount_paise):.2f}</td>
                </tr>
            </table>

            <div class="tax-breakdown">
                <strong>Tax Breakdown:</strong>
                <table class="tax-breakdown-table">
                    <thead>
                        <tr>
                            <th>GST Rate</th>
                            <th class="amount">Base</th>
                            <th class="amount">Tax</th>
                            <th class="amount">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tax_breakdown_html}
                    </tbody>
                </table>
            </div>

            <div class="payment-info">
                <div class="payment-info-row">
                    <span class="payment-info-label">Payment Method:</span>
                    <span class="payment-info-value">{invoice.payment_method.upper()}</span>
                </div>
                {f'<div class="payment-info-row"><span class="payment-info-label">Amount Paid:</span><span class="payment-info-value">₹{paise_to_rupees(invoice.amount_tendered_paise):.2f}</span></div>' if invoice.amount_tendered_paise else ''}
                {f'<div class="payment-info-row"><span class="payment-info-label">Change Due:</span><span class="payment-info-value">₹{paise_to_rupees(invoice.change_due_paise):.2f}</span></div>' if invoice.change_due_paise else ''}
            </div>

            <div class="qr-code">
                <img src="{qr_data_uri}" alt="QR Code">
                <p style="margin-top: 8px; font-size: 12px; color: #999;">Scan for digital receipt</p>
            </div>

            <div class="footer">
                <p>Thank you for your purchase!</p>
                <p>Invoice #{invoice.invoice_number} • {invoice.created_at.strftime('%d-%m-%Y')}</p>
            </div>
        </div>

        <script>
            // Print friendly - offer to print on page load
            // Uncomment to auto-prompt
            // window.addEventListener('load', () => {{
            //   if (confirm('Would you like to print this invoice?')) {{
            //     window.print();
            //   }}
            // }});
        </script>
    </body>
    </html>
    """

    return html
