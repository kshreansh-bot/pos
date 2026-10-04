import { CartItem } from '../../types';
import { formatRupees } from '../../utils/money';

interface CartTableProps {
  items: CartItem[];
  maxDiscountPercent: number;
  onUpdateQuantity: (productId: number, newQty: number) => void;
  onUpdateDiscount: (productId: number, newDiscountPercent: number) => void;
  onRemoveItem: (productId: number) => void;
}

export const CartTable = ({
  items,
  maxDiscountPercent,
  onUpdateQuantity,
  onUpdateDiscount,
  onRemoveItem,
}: CartTableProps) => {
  if (items.length === 0) {
    return (
      <div className="pos-cart-empty">
        <div className="pos-cart-empty-icon">🛒</div>
        <h3>Cart is empty</h3>
        <p>Scan a barcode or search for items using the bar above (or press <strong>F2</strong>)</p>
      </div>
    );
  }

  return (
    <div className="pos-cart-table-wrapper">
      <table className="pos-cart-table">
        <thead>
          <tr>
            <th style={{ width: '5%' }}>#</th>
            <th style={{ width: '35%' }}>Product</th>
            <th style={{ width: '12%' }} className="text-right">Price</th>
            <th style={{ width: '15%' }} className="text-center">Qty</th>
            <th style={{ width: '10%' }} className="text-center">Disc %</th>
            <th style={{ width: '10%' }} className="text-right">GST</th>
            <th style={{ width: '13%' }} className="text-right">Total</th>
            <th style={{ width: '5%' }} className="text-center"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.product.id} className="pos-cart-row">
              <td className="text-muted">{index + 1}</td>
              <td>
                <div className="pos-item-name">{item.product.name}</div>
                <div className="pos-item-meta">
                  {item.product.barcode && <span>🏷️ {item.product.barcode}</span>}
                  <span>Unit: {item.product.unit}</span>
                </div>
              </td>
              <td className="text-right font-medium">
                {formatRupees(item.unit_price_paise)}
              </td>
              <td className="text-center">
                <div className="pos-qty-control">
                  <button
                    type="button"
                    className="pos-qty-btn"
                    onClick={() => onUpdateQuantity(item.product.id, item.quantity - 1)}
                    disabled={item.quantity <= 1}
                    title="Decrease (or remove)"
                  >
                    -
                  </button>
                  <input
                    type="number"
                    min="1"
                    className="pos-qty-input"
                    value={item.quantity}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      if (!isNaN(val) && val > 0) {
                        onUpdateQuantity(item.product.id, val);
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="pos-qty-btn"
                    onClick={() => onUpdateQuantity(item.product.id, item.quantity + 1)}
                    title="Increase"
                  >
                    +
                  </button>
                </div>
              </td>
              <td className="text-center">
                <div className="pos-disc-input-wrapper">
                  <input
                    type="number"
                    min="0"
                    max={maxDiscountPercent}
                    className="pos-disc-input"
                    value={item.discount_percent || 0}
                    onChange={(e) => {
                      let val = parseInt(e.target.value, 10);
                      if (isNaN(val) || val < 0) val = 0;
                      if (val > maxDiscountPercent) val = maxDiscountPercent;
                      onUpdateDiscount(item.product.id, val);
                    }}
                  />
                  <span>%</span>
                </div>
              </td>
              <td className="text-right">
                <div className="pos-tax-val">{formatRupees(item.tax_amount_paise)}</div>
                <div className="text-muted text-xs">({item.product.gst_rate}%)</div>
              </td>
              <td className="text-right font-bold pos-line-total">
                {formatRupees(item.line_total_paise)}
              </td>
              <td className="text-center">
                <button
                  type="button"
                  className="pos-remove-btn"
                  onClick={() => onRemoveItem(item.product.id)}
                  title="Remove item"
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
