"""Conservative status calculation for facility-reported stock."""

from datetime import date, datetime, timedelta, timezone


VERIFICATION_STALE_AFTER_DAYS = 30
EXPIRING_SOON_DAYS = 30


def derive_inventory_status(
    *,
    verification_status: str,
    last_verified_at: datetime | None,
    expiry_date: date | None,
    quantity_units: int,
    low_stock_threshold: int,
    today: date | None = None,
    now: datetime | None = None,
) -> str:
    """Return a descriptive status, never a clinical treatment recommendation."""
    current_date = today or date.today()

    # An explicitly recorded expired product remains expired regardless of
    # the verification state.
    if expiry_date is not None and expiry_date < current_date:
        return "EXPIRED"

    if verification_status == "UNVERIFIED":
        return "UNVERIFIED"

    if verification_status == "MANUALLY_REPORTED":
        return "MANUALLY_REPORTED"

    if (
        verification_status != "FACILITY_REPORTED_CONFIRMED"
        or last_verified_at is None
    ):
        return "UNVERIFIED"

    current_time = now or datetime.now(timezone.utc)
    verified_time = last_verified_at

    if verified_time.tzinfo is None:
        verified_time = verified_time.replace(tzinfo=timezone.utc)

    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    if verified_time > current_time + timedelta(minutes=5):
        return "STALE"

    if current_time - verified_time > timedelta(
        days=VERIFICATION_STALE_AFTER_DAYS
    ):
        return "STALE"

    if quantity_units == 0:
        return "OUT_OF_STOCK"

    if expiry_date is not None and (
        expiry_date <= current_date + timedelta(days=EXPIRING_SOON_DAYS)
    ):
        return "EXPIRING_SOON"

    if quantity_units <= low_stock_threshold:
        return "LOW_STOCK"

    return "IN_STOCK"
