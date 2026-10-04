import { ChangeEvent } from 'react';
import { Cart } from '../../types';
import { formatRupees, paiseToRupees, rupeesToPaise } from '../../utils/money';

interface CartSummaryProps {
  cart: Cart;
  billDiscountPaise: number;
  maxDiscountPercent: number;
  onUpdateBillDiscount: (discountPaise: number) => void;
  onCheckout: () => void;
  onClearCart: () => void;
}

export const CartSummary = ({
  cart,
  billDiscountPaise,
  maxDiscountPercent,
  onUpdateBillDiscount,
  onCheckout,
  onClearCart,
}: CartSummaryProps) => {
  const totalItemsCount = cart.items.length;
  const totalUnitsCount = cart.items.reduce((sum, item) => sum + item.quantity, 0);

  // Group tax by GST rate
  const taxByRate: Record<number, { base: number; tax: number; total: number }> = {};
  for (const item of cart.items) {
    const rate = item.product.gst_rate;
    if (!taxByRate[rate]) {
      taxByRate[rate] = { base: 0, tax: 0, total: 0 };
    }
    const base = item.line_total_paise - item.tax_amount_paise;
    taxByRate[rate].base += base;
    taxByRate[rate].tax += item.tax_amount_paise;
    taxByRate[rate].total += item.line_total_paise;
  }

  // Max allowed bill discount in paise
  const maxDiscountPaise = Math.round((cart.subtotal_paise * maxDiscountPercent) / 100);

  const handleDiscountChange = (e: ChangeEvent<HTMLInputElement>) => {
    const enteredRupees = parseFloat(e.target.value) || 0;
    let paise = rupeesToPaise(enteredRupees);
    if (paise < 0) paise = 0;
    if (paise > maxDiscountPaise) paise = maxDiscountPaise;
    onUpdateBillDiscount(paise);
  };

  return (
    <div className="pos-summary-card">
      <div className="pos-summary-header">
        <h3>Order Summary</h3>
        <span className="pos-summary-count">
          {totalItemsCount} items ({totalUnitsCount} units)
        </span>
      </div>

      <div className="pos-summary-breakdown">
        <div className="pos-summary-row">
          <span>Subtotal</span>
          <span className="font-medium">{formatRupees(cart.subtotal_paise)}</span>
        </div>

        {cart.total_discount_paise > 0 && (
          <div className="pos-summary-row text-success">
            <span>Line Discounts</span>
            <span>-{formatRupees(cart.total_discount_paise)}</span>
          </div>
        )}

        <div className="pos-summary-row pos-discount-row">
          <div className="pos-discount-label">
            <span>Bill Discount (₹)</span>
            <span className="text-muted text-xs">Max {maxDiscountPercent}% (₹{paiseToRupees(maxDiscountPaise).toFixed(2)})</span>
          </div>
          <div className="pos-discount-input-box">
            <span>₹</span>
            <input
              type="number"
              min="0"
              max={paiseToRupees(maxDiscountPaise)}
              step="1"
              value={billDiscountPaise > 0 ? (billDiscountPaise / 100).toString() : ''}
              placeholder="0.00"
              onChange={handleDiscountChange}
              disabled={cart.items.length === 0}
            />
          </div>
        </div>

        <div className="pos-summary-row">
          <span>Total GST (Inclusive)</span>
          <span className="font-medium">{formatRupees(cart.total_tax_paise)}</span>
        </div>

        {/* GST Grouped Details Accordion */}
        {Object.keys(taxByRate).length > 0 && (
          <div className="pos-tax-breakdown-box">
            <div className="pos-tax-breakdown-title">GST Tax Extraction:</div>
            {Object.entries(taxByRate).map(([rate, data]) => (
              <div key={rate} className="pos-tax-breakdown-row">
                <span>GST {rate}%:</span>
                <span>
                  Base: {formatRupees(data.base)} | Tax: {formatRupees(data.tax)}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="pos-summary-divider" />

        <div className="pos-summary-row pos-grand-total">
          <span>Total Payable</span>
          <span className="pos-total-amount">{formatRupees(cart.total_amount_paise)}</span>
        </div>
      </div>

      <div className="pos-summary-actions">
        <button
          type="button"
          className="btn-pos-clear"
          onClick={onClearCart}
          disabled={cart.items.length === 0}
          title="Clear Cart (F9)"
        >
          Clear (F9)
        </button>
        <button
          type="button"
          className="btn-pos-checkout"
          onClick={onCheckout}
          disabled={cart.items.length === 0}
          title="Proceed to Payment (F8)"
        >
          Pay {formatRupees(cart.total_amount_paise)} (F8)
        </button>
      </div>
    </div>
  );
};
