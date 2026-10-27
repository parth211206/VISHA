from datetime import date, datetime, timedelta, timezone

from app.core.inventory_status import derive_inventory_status


TODAY = date(2026, 10, 26)
NOW = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)


def inventory_status(**overrides):
    values = {
        "verification_status": "FACILITY_REPORTED_CONFIRMED",
        "last_verified_at": NOW,
        "expiry_date": TODAY + timedelta(days=200),
        "quantity_units": 20,
        "low_stock_threshold": 5,
        "today": TODAY,
        "now": NOW,
    }
    values.update(overrides)
    return derive_inventory_status(**values)


def test_unverified_stock_is_never_labelled_in_stock():
    assert inventory_status(
        verification_status="UNVERIFIED",
        quantity_units=100,
    ) == "UNVERIFIED"


def test_manually_reported_stock_is_distinguished():
    assert inventory_status(
        verification_status="MANUALLY_REPORTED",
        quantity_units=100,
    ) == "MANUALLY_REPORTED"


def test_confirmed_status_without_timestamp_is_unverified():
    assert inventory_status(last_verified_at=None) == "UNVERIFIED"


def test_old_confirmation_is_stale():
    assert inventory_status(
        last_verified_at=NOW - timedelta(days=31)
    ) == "STALE"


def test_future_confirmation_timestamp_is_stale():
    assert inventory_status(
        last_verified_at=NOW + timedelta(minutes=10)
    ) == "STALE"


def test_expired_product_is_identified():
    assert inventory_status(
        verification_status="UNVERIFIED",
        expiry_date=TODAY - timedelta(days=1),
    ) == "EXPIRED"


def test_confirmed_zero_quantity_is_out_of_stock():
    assert inventory_status(quantity_units=0) == "OUT_OF_STOCK"


def test_confirmed_product_expiring_within_30_days():
    assert inventory_status(
        expiry_date=TODAY + timedelta(days=20)
    ) == "EXPIRING_SOON"


def test_quantity_at_low_stock_threshold():
    assert inventory_status(quantity_units=5) == "LOW_STOCK"


def test_recently_confirmed_stock_above_threshold():
    assert inventory_status(quantity_units=20) == "IN_STOCK"
