import { User } from '../types'
import { api } from '../services/api'
import '../App.css'

interface DashboardPageProps {
  user: User
  onLogout: () => void
}

export default function DashboardPage({ user, onLogout }: DashboardPageProps) {
  const handleLogout = async () => {
    await api.logout()
    onLogout()
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>Supermarket POS</h1>
          <div className="user-info">
            <div>
              <p className="font-bold">{user.full_name}</p>
              <p className="text-sm">{user.role}</p>
            </div>
            <button onClick={handleLogout} className="btn-secondary">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="main-content">
        <h2>Welcome, {user.full_name}!</h2>
        <p className="text-muted mt-2">Dashboard under development. Phase 2+ features coming soon.</p>

        <div className="card mt-4">
          <h3>Your Information</h3>
          <table>
            <tbody>
              <tr>
                <td><strong>Username:</strong></td>
                <td>{user.username}</td>
              </tr>
              <tr>
                <td><strong>Email:</strong></td>
                <td>{user.email || 'N/A'}</td>
              </tr>
              <tr>
                <td><strong>Role:</strong></td>
                <td>{user.role}</td>
              </tr>
              <tr>
                <td><strong>Max Discount:</strong></td>
                <td>{user.max_discount_percent}%</td>
              </tr>
              <tr>
                <td><strong>Status:</strong></td>
                <td>{user.is_active ? 'Active' : 'Inactive'}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card mt-4">
          <h3>Phase Progress</h3>
          <ul style={{ marginLeft: '1.5rem' }}>
            <li>✅ Phase 1: Foundation (Auth, DB models)</li>
            <li>⏳ Phase 2: Products & Inventory</li>
            <li>⏳ Phase 3: Billing Engine & QR</li>
            <li>⏳ Phase 4: POS UI</li>
            <li>⏳ Phase 5: Returns & Audit Log</li>
            <li>⏳ Phase 6: Reports & Demo</li>
          </ul>
        </div>
      </main>
    </div>
  )
}