import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { SalesSummaryResponse, CashierPerformanceItem } from '../types';
import { formatRupees } from '../utils/money';

export const ReportsPage = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'sales' | 'cashiers'>('sales');

  const [salesData, setSalesData] = useState<SalesSummaryResponse | null>(null);
  const [cashierData, setCashierData] = useState<CashierPerformanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      if (activeTab === 'sales') {
        const data = await api.getSalesSummary();
        setSalesData(data);
      } else {
        const data = await api.getCashierPerformance();
        setCashierData(data);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ padding: '20px' }}>
      <button className="btn-secondary" onClick={() => navigate('/dashboard')} style={{ marginBottom: '20px' }}>
        &larr; Back to Dashboard
      </button>

      <h2>Store Reports & Analytics</h2>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button
          className={activeTab === 'sales' ? 'btn-primary' : 'btn-secondary'}
          onClick={() => setActiveTab('sales')}
        >
          Sales Summary (Today)
        </button>
        <button
          className={activeTab === 'cashiers' ? 'btn-primary' : 'btn-secondary'}
          onClick={() => setActiveTab('cashiers')}
        >
          Cashier Performance
        </button>
      </div>

      {loading && <div>Loading report data...</div>}
      {error && <div className="text-danger">{error}</div>}

      {!loading && !error && activeTab === 'sales' && salesData && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '20px' }}>
            <div style={{ padding: '20px', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
              <div className="text-muted">Net Sales</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#166534' }}>
                {formatRupees(salesData.net_sales_paise)}
              </div>
            </div>
            <div style={{  padding: '20px', borderRadius: '8px', border: '1px solid #bae6fd' }}>
              <div className="text-muted">Total Invoices</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#0369a1' }}>
                {salesData.total_invoices_completed}
              </div>
            </div>
            <div style={{padding: '20px', borderRadius: '8px', border: '1px solid #fecaca' }}>
              <div className="text-muted">Returns / Cancels</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#991b1b' }}>
                {salesData.total_invoices_returned + salesData.total_invoices_cancelled}
              </div>
            </div>
            <div style={{  padding: '20px', borderRadius: '8px', border: '1px solid #fbcfe8' }}>
              <div className="text-muted">Avg Order Value</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#86198f' }}>
                {formatRupees(salesData.average_order_value_paise)}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div style={{ padding: '20px', borderRadius: '8px', border: '1px solid #ddd' }}>
              <h3>GST Tax Breakdown</h3>
              <table className="pos-cart-table" style={{ width: '100%' }}>
                <thead>
                  <tr>
                    <th>Slab</th>
                    <th className="text-right">Base Amount</th>
                    <th className="text-right">Tax Collected</th>
                  </tr>
                </thead>
                <tbody>
                  {salesData.tax_slabs.map(slab => (
                    <tr key={slab.gst_rate}>
                      <td>{slab.gst_rate}% GST</td>
                      <td className="text-right">{formatRupees(slab.base_amount_paise)}</td>
                      <td className="text-right font-medium">{formatRupees(slab.tax_amount_paise)}</td>
                    </tr>
                  ))}
                  <tr style={{  fontWeight: 'bold' }}>
                    <td>Total</td>
                    <td className="text-right">-</td>
                    <td className="text-right">{formatRupees(salesData.total_tax_paise)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div style={{  padding: '20px', borderRadius: '8px', border: '1px solid #ddd' }}>
              <h3>Payment Methods</h3>
              <table className="pos-cart-table" style={{ width: '100%' }}>
                <thead>
                  <tr>
                    <th>Method</th>
                    <th className="text-center">Count</th>
                    <th className="text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {salesData.payment_methods.map(pm => (
                    <tr key={pm.method}>
                      <td style={{ textTransform: 'uppercase' }}>{pm.method}</td>
                      <td className="text-center">{pm.count}</td>
                      <td className="text-right font-medium">{formatRupees(pm.total_amount_paise)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {!loading && !error && activeTab === 'cashiers' && (
        <div style={{ padding: '20px', borderRadius: '8px', border: '1px solid #ddd' }}>
          <h3>Staff Performance (Trailing 30 Days)</h3>
          <table className="pos-cart-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Cashier</th>
                <th>Role</th>
                <th className="text-center">Total Bills</th>
                <th className="text-center">Completed</th>
                <th className="text-center">Voided</th>
                <th className="text-right">Total Net Sales</th>
                <th className="text-right">Avg Ticket Size</th>
              </tr>
            </thead>
            <tbody>
              {cashierData.map(c => (
                <tr key={c.user_id}>
                  <td><strong>{c.full_name}</strong> <br/><small className="text-muted">@{c.username}</small></td>
                  <td style={{ textTransform: 'capitalize' }}>{c.role}</td>
                  <td className="text-center">{c.invoices_count}</td>
                  <td className="text-center text-success">{c.completed_count}</td>
                  <td className="text-center text-danger">{c.cancelled_count}</td>
                  <td className="text-right font-bold">{formatRupees(c.total_sales_paise)}</td>
                  <td className="text-right">{formatRupees(c.average_ticket_paise)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};