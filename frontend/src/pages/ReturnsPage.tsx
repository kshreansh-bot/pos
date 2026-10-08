import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Invoice } from '../types';
import { formatRupees } from '../utils/money';

export const ReturnsPage = () => {
  const navigate = useNavigate();
  const [invoiceId, setInvoiceId] = useState('');
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState('');

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!invoiceId.trim()) return;

    setLoading(true);
    setError(null);
    setInvoice(null);
    setMessage('');

    try {
      // In a real app we might search by invoice_number, but here we query by ID for simplicity
      const data = await api.getInvoice(parseInt(invoiceId, 10));
      setInvoice(data);
    } catch (err: any) {
      setError(err.message || 'Invoice not found');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!invoice || !reason.trim()) {
      setError('Please provide a cancellation reason');
      return;
    }

    if (!window.confirm(`Are you sure you want to cancel Invoice #${invoice.invoice_number}?`)) {
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const data = await api.cancelInvoice(invoice.id, reason);
      setInvoice(data);
      setMessage(`Successfully cancelled invoice ${data.invoice_number}`);
      setReason('');
    } catch (err: any) {
      setError(err.message || 'Failed to cancel invoice');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="container" style={{ padding: '20px' }}>
      <button className="btn-secondary" onClick={() => navigate('/dashboard')} style={{ marginBottom: '20px' }}>
        &larr; Back to Dashboard
      </button>

      <h2>Returns &amp; Cancellations</h2>
      <p className="text-muted">Find an invoice by ID to process a cancellation.</p>

      <div style={{  padding: '20px', borderRadius: '4px', border: '1px solid #ddd', marginBottom: '20px' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px' }}>
          <input
            type="number"
            placeholder="Enter Invoice ID (e.g. 1)"
            value={invoiceId}
            onChange={(e) => setInvoiceId(e.target.value)}
            style={{ padding: '8px', flex: 1, maxWidth: '300px' }}
          />
          <button type="submit" className="btn-primary" disabled={loading || !invoiceId.trim()}>
            {loading ? 'Searching...' : 'Lookup Invoice'}
          </button>
        </form>
        {error && <div className="text-danger" style={{ marginTop: '10px' }}>{error}</div>}
        {message && <div className="text-success" style={{ marginTop: '10px' }}>{message}</div>}
      </div>

      {invoice && (
        <div style={{ padding: '20px', borderRadius: '4px', border: '1px solid #ddd' }}>
          <h3>Invoice #{invoice.invoice_number}</h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            <div>
              <p><strong>Date:</strong> {new Date(invoice.created_at).toLocaleString()}</p>
              <p><strong>Status:</strong> <span style={{
                color: invoice.status === 'cancelled' ? 'red' : invoice.status === 'completed' ? 'green' : 'orange',
                fontWeight: 'bold',
                textTransform: 'uppercase'
              }}>{invoice.status}</span></p>
              <p><strong>Payment Method:</strong> {invoice.payment_method}</p>
            </div>
            <div>
              <p><strong>Total Amount:</strong> {formatRupees(invoice.total_amount_paise)}</p>
              <p><strong>Items:</strong> {invoice.items.length}</p>
              <p><strong>GST:</strong> {formatRupees(invoice.total_tax_paise)}</p>
            </div>
          </div>

          <h4>Line Items</h4>
          <table className="pos-cart-table" style={{ marginBottom: '20px' }}>
            <thead>
              <tr>
                <th>Product</th>
                <th className="text-center">Qty</th>
                <th className="text-right">Price</th>
                <th className="text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {invoice.items.map(item => (
                <tr key={item.id}>
                  <td>{item.product_name} <br/><small className="text-muted">{item.product_barcode}</small></td>
                  <td className="text-center">{item.quantity} {item.product_unit}</td>
                  <td className="text-right">{formatRupees(item.unit_price_paise)}</td>
                  <td className="text-right font-medium">{formatRupees(item.line_total_paise)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {invoice.status === 'completed' && (
            <div style={{ padding: '20px', background: '#ffecec', borderRadius: '4px', border: '1px solid #fecaca' }}>
              <h4 style={{ color: '#dc2626', marginTop: 0 }}>Process Full Cancellation</h4>
              <p>This will permanently mark the invoice as cancelled and restore all items back to their respective stock batches.</p>
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <input
                  type="text"
                  placeholder="Reason for cancellation"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  style={{ padding: '8px', flex: 1 }}
                />
                <button
                  className="btn-primary"
                  style={{ background: '#dc2626' }}
                  onClick={handleCancel}
                  disabled={processing || !reason.trim()}
                >
                  {processing ? 'Processing...' : 'Void Invoice'}
                </button>
              </div>
            </div>
          )}

          {invoice.status === 'cancelled' && (
            <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '4px' }}>
              <strong>Cancellation Reason:</strong> {invoice.notes || 'N/A'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
