from decimal import Decimal

import pytest

from bot import calculate_month_total, parse_expense


def test_calculate_month_total_sums_values_without_float_rounding() -> None:
    assert calculate_month_total([Decimal("15.00"), Decimal("8.90"), 1.1]) == Decimal("25.00")


def test_parse_expense_accepts_decimal_comma() -> None:
    assert parse_expense("  Uber 15,50  ") == ("Uber", Decimal("15.50"))


@pytest.mark.parametrize("message", ["Uber", "Uber 0", "Uber -15", " 15", "Uber abc"])
def test_parse_expense_rejects_invalid_messages(message: str) -> None:
    with pytest.raises(ValueError):
        parse_expense(message)