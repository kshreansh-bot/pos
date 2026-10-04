import { useState, useEffect, useRef, FormEvent, KeyboardEvent } from 'react';
import { formatRupees, rupeesToPaise } from '../../utils/money';

interface PaymentModalProps {
  totalAmountPaise: number;
  isOpen: boolean;
  isProcessing: boolean;
  onConfirmPayment: (
    paymentMethod: 'cash' | 'card' | 'upi',
    amountTenderedPaise: number
  ) => void;
  onClose: () => void;
}

export const PaymentModal = ({
  totalAmountPaise,
  isOpen,
  isProcessing,
  onConfirmPayment,
  onClose,
}: PaymentModalProps) => {
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'card' | 'upi'>('cash');
  const [tenderedInput, setTenderedInput] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const tenderedPaise = paymentMethod === 'cash'
    ? (tenderedInput ? rupeesToPaise(parseFloat(tenderedInput)) : 0)
    : totalAmountPaise;

  const changeDuePaise = tenderedPaise - totalAmountPaise;
  const isSufficient = tenderedPaise >= totalAmountPaise;

  const cashInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setPaymentMethod('cash');
      setTenderedInput((totalAmountPaise / 100).toString());
      setErrorMsg(null);
      setTimeout(() => {
        cashInputRef.current?.focus();
        cashInputRef.current?.select();
      }, 50);
    }
  }, [isOpen, totalAmountPaise]);

  if (!isOpen) return null;

  const handlePresetAdd = (amountRupees: number) => {
    const current = parseFloat(tenderedInput) || 0;
    setTenderedInput((current + amountRupees).toString());
  };

  const handleExactAmount = () => {
    setTenderedInput((totalAmountPaise / 100).toString());
  };

  const handleNextHundred = () => {
    const totalRupees = totalAmountPaise / 100;
    const next100 = Math.ceil(totalRupees / 100) * 100;
    setTenderedInput(next100.toString());
  };

  const handleNextFiveHundred = () => {
    const totalRupees = totalAmountPaise / 100;
    const next500 = Math.ceil(totalRupees / 500) * 500;
    setTenderedInput(next500.toString());
  };

  const handleSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (paymentMethod === 'cash' && !isSufficient) {
      setErrorMsg('Tendered amount cannot be less than total amount due.');
      return;
    }
    setErrorMsg(null);
    onConfirmPayment(paymentMethod, tenderedPaise);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'Enter' && !isProcessing && (paymentMethod !== 'cash' || isSufficient)) {
      handleSubmit();
    }
  };

  return (
    <div className="pos-modal-backdrop" onKeyDown={handleKeyDown}>
      <div className="pos-modal-card">
        <div className="pos-modal-header">
          <h2>Complete Payment</h2>
          <button type="button" className="pos-modal-close" onClick={onClose} disabled={isProcessing}>
            ✕
          </button>
        </div>

        <div className="pos-modal-total-banner">
          <span className="pos-modal-total-label">Total Amount Due</span>
          <span className="pos-modal-total-value">{formatRupees(totalAmountPaise)}</span>
        </div>

        <div className="pos-payment-tabs">
          <button
            type="button"
            className={`pos-payment-tab ${paymentMethod === 'cash' ? 'active' : ''}`}
            onClick={() => setPaymentMethod('cash')}
          >
            💵 Cash (1)
          </button>
          <button
            type="button"
            className={`pos-payment-tab ${paymentMethod === 'card' ? 'active' : ''}`}
            onClick={() => setPaymentMethod('card')}
          >
            💳 Card (2)
          </button>
          <button
            type="button"
            className={`pos-payment-tab ${paymentMethod === 'upi' ? 'active' : ''}`}
            onClick={() => setPaymentMethod('upi')}
          >
            📱 UPI / QR (3)
          </button>
        </div>

        {paymentMethod === 'cash' ? (
          <div className="pos-cash-payment-form">
            <label className="pos-input-label">Cash Tendered by Customer (₹)</label>
            <div className="pos-tendered-input-wrapper">
              <span className="currency-prefix">₹</span>
              <input
                ref={cashInputRef}
                type="number"
                step="any"
                min="0"
                className="pos-tendered-input"
                value={tenderedInput}
                onChange={(e) => {
                  setTenderedInput(e.target.value);
                  setErrorMsg(null);
                }}
                placeholder="0.00"
              />
            </div>

            {/* Quick denomination helpers */}
            <div className="pos-quick-denominations">
              <button type="button" onClick={handleExactAmount} className="btn-preset">
                Exact (₹{(totalAmountPaise / 100).toFixed(2)})
              </button>
              <button type="button" onClick={handleNextHundred} className="btn-preset">
                Round ₹100
              </button>
              <button type="button" onClick={handleNextFiveHundred} className="btn-preset">
                Round ₹500
              </button>
              <button type="button" onClick={() => handlePresetAdd(100)} className="btn-preset">
                +₹100
              </button>
              <button type="button" onClick={() => handlePresetAdd(500)} className="btn-preset">
                +₹500
              </button>
            </div>

            {/* Change Due / Balance calculation */}
            <div className="pos-change-box">
              {isSufficient ? (
                <div className="pos-change-row success">
                  <span>Change Due to Customer:</span>
                  <span className="pos-change-amount">{formatRupees(changeDuePaise)}</span>
                </div>
              ) : (
                <div className="pos-change-row danger">
                  <span>Remaining Balance:</span>
                  <span className="pos-change-amount">{formatRupees(Math.abs(changeDuePaise))}</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="pos-digital-payment-info">
            <div className="pos-digital-icon">{paymentMethod === 'card' ? '💳' : '📱'}</div>
            <p>
              Please swipe/tap card or scan store UPI QR code for{' '}
              <strong>{formatRupees(totalAmountPaise)}</strong>.
            </p>
            <p className="text-muted text-sm">
              Press Confirm below once transaction is verified on POS terminal.
            </p>
          </div>
        )}

        {errorMsg && <div className="error-alert mt-2">{errorMsg}</div>}

        <div className="pos-modal-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={onClose}
            disabled={isProcessing}
          >
            Cancel (Esc)
          </button>
          <button
            type="button"
            className="btn-primary btn-confirm-pay"
            onClick={() => handleSubmit()}
            disabled={isProcessing || (paymentMethod === 'cash' && !isSufficient)}
          >
            {isProcessing ? 'Processing Invoice...' : `Complete Bill (Enter)`}
          </button>
        </div>
      </div>
    </div>
  );
};
