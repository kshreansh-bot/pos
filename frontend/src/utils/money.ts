/**
 * Money utilities for frontend.
 * All backend amounts are integers in paise (1 INR = 100 paise).
 */

export function paiseToRupees(paise: number): number {
  return paise / 100;
}

export function rupeesToPaise(rupees: number): number {
  return Math.round(rupees * 100);
}

export function formatRupees(paise: number): string {
  const rupees = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rupees);
}

/**
 * Extract GST from an inclusive price in paise.
 * Formula: Tax = Price - (Price / (1 + Rate / 100))
 * Uses round-half-up.
 */
export function extractGstFromInclusive(pricePaise: number, gstRatePercent: number): number {
  if (gstRatePercent <= 0 || pricePaise <= 0) return 0;
  const rate = gstRatePercent / 100;
  const base = pricePaise / (1 + rate);
  const tax = pricePaise - base;
  return Math.round(tax);
}

/**
 * Round half up (standard POS math).
 */
export function roundHalfUp(value: number): number {
  return Math.round(value);
}
