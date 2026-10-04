import { useEffect } from 'react';
import { Invoice } from '../../types';
import { formatRupees } from '../../utils/money';
import { api } from '../../services/api';

interface InvoiceSuccessModalProps {
  invoice: Invoice | null;
  isOpen: boolean;
  onNewBill: () => void;
}

export const InvoiceSuccessModal = ({
  invoice,
  isOpen,
  onNewBill,
}: InvoiceSuccessModalProps) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        onNewBill();
      } else if (e.key === 'p' || e.key === 'P') {
        if (invoice?.public_token) {
          window.open(api.getPublicBillHtmlUrl(invoice.public_token), '_blank');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onNewBill, invoice]);

  if (!isOpen || !invoice) return null;

  const publicBillUrl = api.getPublicBillHtmlUrl(invoice.public_token);

  return (
    <div className="pos-modal-backdrop">
      <div className="pos-modal-card pos-success-card">
        <div className="pos-success-badge">✓</div>
        <h2>Invoice Created Successfully!</h2>
        <div className="pos-invoice-badge">{invoice.invoice_number}</div>

        <div className="pos-success-summary">
          <div className="pos-success-row">
            <span>Total Amount:</span>
            <span className="font-bold text-lg">{formatRupees(invoice.total_amount_paise)}</span>
          </div>

          <div className="pos-success-row">
            <span>Payment Method:</span>
            <span className="text-uppercase font-medium">{invoice.payment_method}</span>
          </div>

          {invoice.amount_tendered_paise !== undefined && invoice.amount_tendered_paise !== null && (
            <div className="pos-success-row">
              <span>Amount Paid:</span>
              <span>{formatRupees(invoice.amount_tendered_paise)}</span>
            </div>
          )}

          {invoice.change_due_paise !== undefined && invoice.change_due_paise !== null && (
            <div className="pos-success-row text-success font-medium">
              <span>Change Returned:</span>
              <span>{formatRupees(invoice.change_due_paise)}</span>
            </div>
          )}

          <div className="pos-success-row">
            <span>Items Billed:</span>
            <span>{invoice.items.length} items</span>
          </div>
        </div>

        <div className="pos-success-actions">
          <a
            href={publicBillUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-print-bill"
          >
            🖨️ View / Print Digital Bill (P)
          </a>
          <button
            type="button"
            className="btn-primary btn-new-bill"
            onClick={onNewBill}
            autoFocus
          >
            Start New Bill (Enter)
          </button>
        </div>
      </div>
    </div>
  );
};
