// User types
export enum UserRole {
  ADMIN = 'admin',
  MANAGER = 'manager',
  CASHIER = 'cashier',
  INVENTORY_MANAGER = 'inventory_manager',
  CUSTOMER = 'customer',
}

export interface User {
  id: number;
  username: string;
  email?: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  max_discount_percent: number;
  created_at: string;
  updated_at?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
  expires_in: number;
}

// Product types
export interface Product {
  id: number;
  barcode?: string;
  name: string;
  brand?: string;
  category_id: number;
  category_name?: string;
  unit: string;
  mrp_paise: number;
  purchase_price_paise: number;
  selling_price_paise: number;
  gst_rate: number;
  stock_quantity: number;
  reorder_level: number;
  is_active: boolean;
  default_discount_percent: number;
}

// Cart types
export interface CartItem {
  product: Product;
  quantity: number;
  unit_price_paise: number;
  discount_percent: number;
  discount_paise: number;
  tax_amount_paise: number;
  line_total_paise: number;
}

export interface Cart {
  items: CartItem[];
  subtotal_paise: number;
  total_discount_paise: number;
  total_tax_paise: number;
  total_amount_paise: number;
}

// Invoice types
export interface InvoiceItem {
  id: number;
  product_id: number;
  product_name: string;
  product_barcode?: string;
  quantity: number;
  unit_price_paise: number;
  gst_rate: number;
  discount_percent: number;
  discount_paise: number;
  tax_amount_paise: number;
  line_total_paise: number;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  customer_id?: number;
  customer_name?: string;
  user_id: number;
  user_name?: string;
  subtotal_paise: number;
  total_discount_paise: number;
  total_tax_paise: number;
  total_amount_paise: number;
  payment_method: string;
  amount_tendered_paise?: number;
  change_due_paise?: number;
  status: 'completed' | 'cancelled' | 'returned';
  notes?: string;
  public_token: string;
  created_at: string;
  items: InvoiceItem[];
}

// API Response types
export interface ApiError {
  detail: string;
  error_code?: string;
  status_code: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Category types
export interface Category {
  id: number;
  name: string;
  description?: string;
  created_at: string;
}

// Supplier types
export interface Supplier {
  id: number;
  name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  gst_number?: string;
  is_active: boolean;
  created_at: string;
}

// Stock types
export interface StockBatch {
  id: number;
  product_id: number;
  batch_number: string;
  quantity: number;
  initial_quantity: number;
  purchase_price_paise: number;
  expiry_date?: string;
  is_active: boolean;
  created_at: string;
  is_expired?: boolean;
  is_expiring_soon?: boolean;
}

// Customer types
export interface Customer {
  id: number;
  name: string;
  phone?: string;
  email?: string;
  address?: string;
  loyalty_points: number;
  is_active: boolean;
  created_at: string;
}

// Tax breakdown for invoices
export interface TaxBreakdown {
  rate: number;
  taxable_amount_paise: number;
  tax_amount_paise: number;
}