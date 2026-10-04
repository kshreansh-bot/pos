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
  stock_quantity?: number;
  reorder_level: number;
  supplier_id?: number;
  default_discount_percent: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
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
  bill_discount_paise: number;
}

// Invoice creation types
export interface InvoiceItemCreate {
  product_id: number;
  quantity: number;
  discount_percent?: number;
}

export interface InvoiceCreate {
  items: InvoiceItemCreate[];
  customer_id?: number | null;
  payment_method: 'cash' | 'card' | 'upi';
  discount_paise?: number;
  amount_tendered_paise?: number | null;
}

// Invoice response types
export interface InvoiceItemResponse {
  id: number;
  product_id: number;
  product_name: string;
  product_barcode?: string;
  product_unit: string;
  quantity: number;
  unit_price_paise: number;
  gst_rate: number;
  discount_percent: number;
  discount_paise: number;
  tax_amount_paise: number;
  line_total_paise: number;
  created_at: string;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  customer_id?: number | null;
  user_id: number;
  subtotal_paise: number;
  total_discount_paise: number;
  total_tax_paise: number;
  total_amount_paise: number;
  payment_method: string;
  amount_tendered_paise?: number | null;
  change_due_paise?: number | null;
  status: 'completed' | 'cancelled' | 'returned';
  notes?: string;
  public_token: string;
  items: InvoiceItemResponse[];
  created_at: string;
}

// Tax breakdown for invoices
export interface TaxBreakdown {
  rate: number;
  base_amount_paise: number;
  tax_amount_paise: number;
  total_paise: number;
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

export interface LoyaltyAdjustRequest {
  points_delta: number;
  reason: string;
}

export interface CustomerInvoiceBrief {
  id: number;
  invoice_number: string;
  total_amount_paise: number;
  payment_method: string;
  status: string;
  created_at: string;
}

export interface CustomerDetail extends Customer {
  invoices: CustomerInvoiceBrief[];
}

// Report Types
export interface GstTaxSlabSummary {
  gst_rate: number;
  base_amount_paise: number;
  tax_amount_paise: number;
  total_amount_paise: number;
}

export interface PaymentMethodSummary {
  method: string;
  count: number;
  total_amount_paise: number;
}

export interface SalesSummaryResponse {
  period_start: string;
  period_end: string;
  total_invoices_completed: number;
  total_invoices_cancelled: number;
  total_invoices_returned: number;
  gross_sales_paise: number;
  total_discount_paise: number;
  total_tax_paise: number;
  net_sales_paise: number;
  average_order_value_paise: number;
  payment_methods: PaymentMethodSummary[];
  tax_slabs: GstTaxSlabSummary[];
}

export interface CashierPerformanceItem {
  user_id: number;
  username: string;
  full_name: string;
  role: string;
  invoices_count: number;
  completed_count: number;
  cancelled_count: number;
  total_sales_paise: number;
  average_ticket_paise: number;
}

export interface AuditLogResponse {
  id: number;
  user_id: number;
  username?: string;
  action: string;
  entity_type: string;
  entity_id: number;
  old_values?: string;
  new_values?: string;
  reason?: string;
  created_at: string;
}
