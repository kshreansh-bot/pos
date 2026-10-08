import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Product, CartItem, Cart, Invoice } from '../types';
import { api } from '../services/api';
import { extractGstFromInclusive, roundHalfUp } from '../utils/money';
import { ProductSearch } from '../components/pos/ProductSearch';
import { CartTable } from '../components/pos/CartTable';
import { CartSummary } from '../components/pos/CartSummary';
import { PaymentModal } from '../components/pos/PaymentModal';
import { InvoiceSuccessModal } from '../components/pos/InvoiceSuccessModal';
import './POSPage.css';

interface POSPageProps {
  user: User;
  onLogout: () => void;
}

export default function POSPage({ user, onLogout }: POSPageProps) {
  const navigate = useNavigate();

  // Cart state
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [billDiscountPaise, setBillDiscountPaise] = useState<number>(0);

  // Modals & UI state
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isProcessingPayment, setIsProcessingPayment] = useState(false);
  const [completedInvoice, setCompletedInvoice] = useState<Invoice | null>(null);
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: 'error' | 'success'; message: string } | null>(null);

  const searchInputRef = useRef<HTMLInputElement>(null);

  // Focus search bar on initial mount
  useEffect(() => {
    searchInputRef.current?.focus();
  }, []);

  // Calculate live cart totals
  const calculateCart = useCallback((): Cart => {
    let subtotal_paise = 0;
    let total_discount_paise = 0;
    let total_tax_paise = 0;
    let total_amount_paise = 0;

    const updatedItems = cartItems.map((item) => {
      const lineGross = item.product.selling_price_paise * item.quantity;
      const lineDiscount = roundHalfUp((lineGross * item.discount_percent) / 100);
      const lineTotal = lineGross - lineDiscount;
      const lineTax = extractGstFromInclusive(lineTotal, item.product.gst_rate);

      subtotal_paise += lineGross;
      total_discount_paise += lineDiscount;
      total_tax_paise += lineTax;
      total_amount_paise += lineTotal;

      return {
        ...item,
        unit_price_paise: item.product.selling_price_paise,
        discount_paise: lineDiscount,
        tax_amount_paise: lineTax,
        line_total_paise: lineTotal,
      };
    });

    const finalPayable = Math.max(0, total_amount_paise - billDiscountPaise);

    return {
      items: updatedItems,
      subtotal_paise,
      total_discount_paise: total_discount_paise + billDiscountPaise,
      total_tax_paise,
      total_amount_paise: finalPayable,
      bill_discount_paise: billDiscountPaise,
    };
  }, [cartItems, billDiscountPaise]);

  const cart = calculateCart();

  // Add Product to Cart
  const handleAddProduct = (product: Product) => {
    setNotification(null);
    setCartItems((prevItems) => {
      const existingIndex = prevItems.findIndex((i) => i.product.id === product.id);
      if (existingIndex >= 0) {
        // ... (rest of logic remains same)
        const updated = [...prevItems];
        const existing = updated[existingIndex];
        const newQty = existing.quantity + 1;
        const lineGross = product.selling_price_paise * newQty;
        const lineDiscount = roundHalfUp((lineGross * existing.discount_percent) / 100);
        const lineTotal = lineGross - lineDiscount;
        const lineTax = extractGstFromInclusive(lineTotal, product.gst_rate);

        updated[existingIndex] = {
          ...existing,
          quantity: newQty,
          discount_paise: lineDiscount,
          tax_amount_paise: lineTax,
          line_total_paise: lineTotal,
        };
        return updated;
      }

      // Add new item with default discount if any
      const defaultDiscount = Math.min(product.default_discount_percent || 0, user.max_discount_percent);
      const lineGross = product.selling_price_paise * 1;
      const lineDiscount = roundHalfUp((lineGross * defaultDiscount) / 100);
      const lineTotal = lineGross - lineDiscount;
      const lineTax = extractGstFromInclusive(lineTotal, product.gst_rate);

      return [
        ...prevItems,
        {
          product,
          quantity: 1,
          unit_price_paise: product.selling_price_paise,
          discount_percent: defaultDiscount,
          discount_paise: lineDiscount,
          tax_amount_paise: lineTax,
          line_total_paise: lineTotal,
        },
      ];
    });
    // Refocus search input for next scan
    setTimeout(() => searchInputRef.current?.focus(), 50);
  };

  // Update Quantity for an item
  const handleUpdateQuantity = (productId: number, newQty: number) => {
    if (newQty <= 0) {
      handleRemoveItem(productId);
      return;
    }

    setCartItems((prevItems) =>
      prevItems.map((item) => {
        if (item.product.id !== productId) return item;
        const lineGross = item.product.selling_price_paise * newQty;
        const lineDiscount = roundHalfUp((lineGross * item.discount_percent) / 100);
        const lineTotal = lineGross - lineDiscount;
        const lineTax = extractGstFromInclusive(lineTotal, item.product.gst_rate);

        return {
          ...item,
          quantity: newQty,
          discount_paise: lineDiscount,
          tax_amount_paise: lineTax,
          line_total_paise: lineTotal,
        };
      })
    );
  };

  // Update Line Discount %
  const handleUpdateDiscount = (productId: number, newDiscountPercent: number) => {
    const validDiscount = Math.min(newDiscountPercent, user.max_discount_percent);
    setCartItems((prevItems) =>
      prevItems.map((item) => {
        if (item.product.id !== productId) return item;
        const lineGross = item.product.selling_price_paise * item.quantity;
        const lineDiscount = roundHalfUp((lineGross * validDiscount) / 100);
        const lineTotal = lineGross - lineDiscount;
        const lineTax = extractGstFromInclusive(lineTotal, item.product.gst_rate);

        return {
          ...item,
          discount_percent: validDiscount,
          discount_paise: lineDiscount,
          tax_amount_paise: lineTax,
          line_total_paise: lineTotal,
        };
      })
    );
  };

  // Remove Item
  const handleRemoveItem = (productId: number) => {
    setCartItems((prev) => prev.filter((item) => item.product.id !== productId));
  };

  // Clear Cart
  const handleClearCart = () => {
    if (cartItems.length === 0) return;
    if (window.confirm('Are you sure you want to clear the current cart?')) {
      setCartItems([]);
      setBillDiscountPaise(0);
      setNotification(null);
      searchInputRef.current?.focus();
    }
  };

  // Handle Checkout & Confirm Payment
  const handleOpenPayment = () => {
    if (cart.items.length === 0) {
      setNotification({ type: 'error', message: 'Cart is empty. Please add items first.' });
      return;
    }
    setIsPaymentModalOpen(true);
  };

  const handleConfirmPayment = async (
    paymentMethod: 'cash' | 'card' | 'upi',
    amountTenderedPaise: number
  ) => {
    setIsProcessingPayment(true);
    setNotification(null);

    try {
      const invoicePayload = {
        items: cart.items.map((i) => ({
          product_id: i.product.id,
          quantity: i.quantity,
          discount_percent: i.discount_percent,
        })),
        payment_method: paymentMethod,
        discount_paise: billDiscountPaise,
        amount_tendered_paise: amountTenderedPaise,
      };

      const createdInvoice = await api.createInvoice(invoicePayload);
      setCompletedInvoice(createdInvoice);
      setIsPaymentModalOpen(false);
      setIsSuccessModalOpen(true);

      // Reset cart
      setCartItems([]);
      setBillDiscountPaise(0);
    } catch (err: any) {
      console.error('Invoice creation failed:', err);
      setNotification({
        type: 'error',
        message: err.message || 'Failed to complete invoice. Please check stock and try again.',
      });
      setIsPaymentModalOpen(false);
    } finally {
      setIsProcessingPayment(false);
    }
  };

  const handleStartNewBill = () => {
    setIsSuccessModalOpen(false);
    setCompletedInvoice(null);
    setNotification(null);
    searchInputRef.current?.focus();
  };

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if modals are open
      if (isPaymentModalOpen || isSuccessModalOpen) return;

      if (e.key === 'F2') {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      } else if (e.key === 'F8') {
        e.preventDefault();
        if (cartItems.length > 0) {
          handleOpenPayment();
        }
      } else if (e.key === 'F9') {
        e.preventDefault();
        handleClearCart();
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [isPaymentModalOpen, isSuccessModalOpen, cartItems.length]);

  return (
    <div className="pos-layout">
      {/* Top POS Header */}
      <header className="pos-topbar">
        <div className="pos-brand">
          <h1>🛒 Supermarket POS</h1>
          <span className="pos-badge">Terminal Active</span>
        </div>

        {/* Global Keyboard Shortcut Hints */}
        <div className="pos-hotkeys-bar">
          <span className="hotkey-pill"><kbd>F2</kbd> Search / Scan</span>
          <span className="hotkey-pill"><kbd>F8</kbd> Pay Bill</span>
          <span className="hotkey-pill"><kbd>F9</kbd> Clear Cart</span>
          <span className="hotkey-pill"><kbd>Esc</kbd> Close</span>
        </div>

        <div className="pos-user-bar">
          <div className="pos-cashier-meta">
            <span className="pos-cashier-name">{user.full_name}</span>
            <span className="pos-cashier-role">Cashier (Max Disc: {user.max_discount_percent}%)</span>
          </div>
          <button
            type="button"
            className="btn-nav-dashboard"
            onClick={() => navigate('/dashboard')}
          >
            📊 Dashboard
          </button>
          <button type="button" className="btn-logout" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Main POS Interface (Split Screen) */}
      <div className="pos-main-container">
        {/* Left Panel: Search & Line Items */}
        <section className="pos-left-panel">
          <div className="pos-search-box">
            <ProductSearch
              inputRef={searchInputRef}
              onSelectProduct={handleAddProduct}
            />
          </div>

          {notification && (
            <div className={`pos-notification ${notification.type}`}>
              {notification.message}
              <button
                type="button"
                className="pos-notification-dismiss"
                onClick={() => setNotification(null)}
              >
                ✕
              </button>
            </div>
          )}

          <div className="pos-cart-container">
            <CartTable
              items={cart.items}
              maxDiscountPercent={user.max_discount_percent}
              onUpdateQuantity={handleUpdateQuantity}
              onUpdateDiscount={handleUpdateDiscount}
              onRemoveItem={handleRemoveItem}
            />
          </div>
        </section>

        {/* Right Panel: Live Totals & Action Controls */}
        <aside className="pos-right-panel">
          <CartSummary
            cart={cart}
            billDiscountPaise={billDiscountPaise}
            maxDiscountPercent={user.max_discount_percent}
            onUpdateBillDiscount={setBillDiscountPaise}
            onCheckout={handleOpenPayment}
            onClearCart={handleClearCart}
          />
        </aside>
      </div>

      {/* Payment Modal */}
      <PaymentModal
        isOpen={isPaymentModalOpen}
        isProcessing={isProcessingPayment}
        totalAmountPaise={cart.total_amount_paise}
        onConfirmPayment={handleConfirmPayment}
        onClose={() => setIsPaymentModalOpen(false)}
      />

      {/* Invoice Created Success Modal */}
      <InvoiceSuccessModal
        isOpen={isSuccessModalOpen}
        invoice={completedInvoice}
        onNewBill={handleStartNewBill}
      />
    </div>
  );
}
