import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Customer } from '../types';

export const CustomersPage = () => {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      const data = await api.listCustomers(0, 50, search);
      setCustomers(data.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchCustomers();
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [search]);

  return (
    <div className="container" style={{ padding: '20px' }}>
      <button className="btn-secondary" onClick={() => navigate('/dashboard')} style={{ marginBottom: '20px' }}>
        &larr; Back to Dashboard
      </button>

      <h2>Customer Details & Loyalty</h2>
      <p className="text-muted">Search customers by name, email, or phone</p>

      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <input
          type="text"
          placeholder="Search customers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ padding: '8px', flex: 1, maxWidth: '400px' }}
        />
        <button className="btn-primary" onClick={fetchCustomers}>Refresh</button>
      </div>

      {loading ? (
        <div>Loading customers...</div>
      ) : (
        <div style={{ background: 'white', borderRadius: '4px', border: '1px solid #ddd', overflowX: 'auto' }}>
          <table className="pos-cart-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Phone</th>
                <th>Email</th>
                <th>Loyalty Points</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {customers.length === 0 ? (
                <tr><td colSpan={6} className="text-center">No customers found</td></tr>
              ) : (
                customers.map(c => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td className="font-medium">{c.name}</td>
                    <td>{c.phone || '-'}</td>
                    <td>{c.email || '-'}</td>
                    <td className="text-success font-bold">{c.loyalty_points}</td>
                    <td>{c.is_active ? 'Active' : 'Inactive'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
