"""Money handling utilities.

All monetary amounts are stored as integer paise (1 rupee = 100 paise).
This module provides conversion and rounding functions.
"""
from decimal import Decimal, ROUND_HALF_UP


def rupees_to_paise(rupees: float) -> int:
    """Convert rupees to paise.

    Args:
        rupees: Amount in rupees (can be float)

    Returns:
        Amount in paise (integer)

    Example:
        >>> rupees_to_paise(10.50)
        1050
        >>> rupees_to_paise(99.99)
        9999
    """
    return int(round(rupees * 100))


def paise_to_rupees(paise: int) -> float:
    """Convert paise to rupees.

    Args:
        paise: Amount in paise (integer)

    Returns:
        Amount in rupees (float, 2 decimal places)

    Example:
        >>> paise_to_rupees(1050)
        10.50
        >>> paise_to_rupees(9999)
        99.99
    """
    return round(paise / 100, 2)


def round_half_up(value: float, decimals: int = 2) -> float:
    """Round a value using round-half-up strategy.

    This is the standard rounding method (not banker's rounding).
    Values exactly at 0.5 round up.

    Args:
        value: Value to round
        decimals: Number of decimal places

    Returns:
        Rounded value

    Example:
        >>> round_half_up(2.345, 2)
        2.35
        >>> round_half_up(2.355, 2)
        2.36
        >>> round_half_up(2.5, 0)
        3.0
    """
    multiplier = Decimal(10 ** decimals)
    return float((Decimal(str(value)) * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / multiplier)


def calculate_gst_inclusive_price(base_price: int, gst_rate: int) -> int:
    """Calculate GST-inclusive price from base price.

    Args:
        base_price: Base price in paise (before tax)
        gst_rate: GST rate as integer (e.g., 18 for 18%)

    Returns:
        GST-inclusive price in paise

    Example:
        >>> calculate_gst_inclusive_price(10000, 18)  # ₹100 + 18% GST
        11800
    """
    gst_amount = round_half_up((base_price * gst_rate) / 100, 0)
    return int(base_price + gst_amount)


def extract_gst_from_inclusive_price(inclusive_price: int, gst_rate: int) -> tuple[int, int]:
    """Extract GST amount from GST-inclusive price.

    Formula: GST = price - (price / (1 + rate/100))

    Args:
        inclusive_price: GST-inclusive price in paise
        gst_rate: GST rate as integer (e.g., 18 for 18%)

    Returns:
        Tuple of (base_price_paise, gst_amount_paise)

    Example:
        >>> extract_gst_from_inclusive_price(11800, 18)
        (10000, 1800)
        >>> extract_gst_from_inclusive_price(10000, 0)  # 0% GST
        (10000, 0)
    """
    if gst_rate == 0:
        return inclusive_price, 0

    # Calculate base price: price / (1 + rate/100)
    divisor = 1 + (gst_rate / 100)
    base_price = round_half_up(inclusive_price / divisor, 0)
    gst_amount = inclusive_price - int(base_price)

    return int(base_price), gst_amount


def format_currency(paise: int) -> str:
    """Format paise amount as currency string.

    Args:
        paise: Amount in paise

    Returns:
        Formatted currency string with ₹ symbol

    Example:
        >>> format_currency(10050)
        '₹100.50'
        >>> format_currency(123456)
        '₹1,234.56'
    """
    rupees = paise_to_rupees(paise)
    return f"₹{rupees:,.2f}"
