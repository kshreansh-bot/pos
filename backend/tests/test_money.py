"""Tests for money handling utilities."""
import pytest
from app.utils.money import (
    rupees_to_paise,
    paise_to_rupees,
    round_half_up,
    calculate_gst_inclusive_price,
    extract_gst_from_inclusive_price,
    format_currency,
)


class TestRupeesToPaise:
    """Test rupee to paise conversion."""

    def test_basic_conversion(self):
        assert rupees_to_paise(10.50) == 1050
        assert rupees_to_paise(100) == 10000
        assert rupees_to_paise(0.01) == 1

    def test_rounding(self):
        assert rupees_to_paise(10.999) == 1100
        assert rupees_to_paise(10.001) == 1000


class TestPaiseToRupees:
    """Test paise to rupee conversion."""

    def test_basic_conversion(self):
        assert paise_to_rupees(1050) == 10.50
        assert paise_to_rupees(10000) == 100.00
        assert paise_to_rupees(1) == 0.01

    def test_zero(self):
        assert paise_to_rupees(0) == 0.00


class TestRoundHalfUp:
    """Test round-half-up function."""

    def test_standard_rounding(self):
        assert round_half_up(2.345, 2) == 2.35
        assert round_half_up(2.355, 2) == 2.36  # Round half up
        assert round_half_up(2.344, 2) == 2.34

    def test_whole_numbers(self):
        assert round_half_up(2.5, 0) == 3.0
        assert round_half_up(2.4, 0) == 2.0
        assert round_half_up(2.0, 0) == 2.0

    def test_zero(self):
        assert round_half_up(0, 2) == 0.0

    def test_negative(self):
        assert round_half_up(-2.5, 0) == -3.0  # Round half up (symmetric)
        assert round_half_up(-2.6, 0) == -3.0


class TestGstCalculation:
    """Test GST calculations."""

    def test_gst_inclusive_price(self):
        # 100 + 18% = 118
        assert calculate_gst_inclusive_price(10000, 18) == 11800
        # 100 + 5% = 105
        assert calculate_gst_inclusive_price(10000, 5) == 10500
        # 100 + 0% = 100
        assert calculate_gst_inclusive_price(10000, 0) == 10000

    def test_extract_gst_from_inclusive(self):
        # 118 with 18% rate: base = 100, gst = 18
        base, gst = extract_gst_from_inclusive_price(11800, 18)
        assert base == 10000
        assert gst == 1800

        # Zero rate
        base, gst = extract_gst_from_inclusive_price(10000, 0)
        assert base == 10000
        assert gst == 0

        # 5% rate
        base, gst = extract_gst_from_inclusive_price(10500, 5)
        assert base == 10000
        assert gst == 500


class TestFormatCurrency:
    """Test currency formatting."""

    def test_format_currency(self):
        assert format_currency(10050) == "₹100.50"
        assert format_currency(100) == "₹1.00"
        assert format_currency(123456) == "₹1,234.56"
        assert format_currency(0) == "₹0.00"


class TestMoneyEdgeCases:
    """Test edge cases in money handling."""

    def test_large_numbers(self):
        assert rupees_to_paise(999999.99) == 99999999

    def test_zero_amounts(self):
        assert rupees_to_paise(0) == 0
        assert paise_to_rupees(0) == 0.0

    def test_very_small_amounts(self):
        # Less than 1 paise should round to 0
        assert rupees_to_paise(0.001) == 0