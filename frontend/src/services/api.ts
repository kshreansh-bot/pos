import {
  LoginRequest,
  LoginResponse,
  User,
  Product,
  Invoice,
  InvoiceCreate,
  Customer,
  SalesSummaryResponse,
  CashierPerformanceItem,
  AuditLogResponse
} from '../types';


const API_BASE = 
import.meta.env.VITE_API_URL || '/api';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('access_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    this.setToken(response.access_token);
    return response;
  }

  async logout(): Promise<void> {
    await this.request('/auth/logout', { method: 'POST' }).catch(() => {});
    this.setToken(null);
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // User endpoints
  async getUsers(): Promise<User[]> {
    return this.request<User[]>('/users/');
  }

  async getUser(userId: number): Promise<User> {
    return this.request<User>(`/users/${userId}`);
  }

  // Product endpoints
  async searchProducts(query: string, limit: number = 20): Promise<Product[]> {
    return this.request<Product[]>(`/products/search/items?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  async listProducts(skip: number = 0, limit: number = 50, categoryId?: number, search?: string): Promise<Product[]> {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (categoryId) params.append('category_id', categoryId.toString());
    if (search) params.append('search', search);
    return this.request<Product[]>(`/products/?${params.toString()}`);
  }

  async getProduct(productId: number): Promise<Product> {
    return this.request<Product>(`/products/${productId}`);
  }

  // Billing / Invoice endpoints
  async createInvoice(invoiceData: InvoiceCreate): Promise<Invoice> {
    return this.request<Invoice>('/invoices/create', {
      method: 'POST',
      body: JSON.stringify(invoiceData),
    });
  }

  async getInvoice(invoiceId: number): Promise<Invoice> {
    return this.request<Invoice>(`/invoices/${invoiceId}`);
  }

  async listInvoices(skip: number = 0, limit: number = 50): Promise<{ items: Invoice[]; total: number }> {
    return this.request<{ items: Invoice[]; total: number }>(`/invoices/?skip=${skip}&limit=${limit}`);
  }

  async cancelInvoice(invoiceId: number, reason: string): Promise<Invoice> {
    return this.request<Invoice>(`/invoices/${invoiceId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  getPublicBillHtmlUrl(publicToken: string): string {
    return `${API_BASE}/bills/${publicToken}/html`;
  }

  // Customers
  async searchCustomers(query: string): Promise<Customer[]> {
    return this.request<Customer[]>(`/customers/search?q=${encodeURIComponent(query)}`);
  }

  async listCustomers(skip: number = 0, limit: number = 50, search: string = ''): Promise<{items: Customer[], total: number}> {
    return this.request<{items: Customer[], total: number}>(`/customers/?skip=${skip}&limit=${limit}&search=${encodeURIComponent(search)}`);
  }

  async adjustLoyaltyPoints(customerId: number, points_delta: number, reason: string): Promise<Customer> {
    return this.request<Customer>(`/customers/${customerId}/loyalty/adjust`, {
      method: 'POST',
      body: JSON.stringify({ points_delta, reason })
    });
  }

  // Reports
  async getSalesSummary(startDate?: string, endDate?: string): Promise<SalesSummaryResponse> {
    let url = '/reports/sales/summary?';
    if (startDate) url += `start_date=${startDate}&`;
    if (endDate) url += `end_date=${endDate}`;
    return this.request<SalesSummaryResponse>(url);
  }

  async getCashierPerformance(startDate?: string, endDate?: string): Promise<CashierPerformanceItem[]> {
    let url = '/reports/cashiers?';
    if (startDate) url += `start_date=${startDate}&`;
    if (endDate) url += `end_date=${endDate}`;
    return this.request<CashierPerformanceItem[]>(url);
  }

  async getAuditLogs(skip: number = 0, limit: number = 50): Promise<{items: AuditLogResponse[], total: number}> {
    return this.request<{items: AuditLogResponse[], total: number}>(`/reports/audit-logs?skip=${skip}&limit=${limit}`);
  }
}

export const api = new ApiClient();
export default api;
