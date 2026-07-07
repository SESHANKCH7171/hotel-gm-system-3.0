"""
PMS Tools — Property Management System
───────────────────────────────────────
Plain, deterministic functions for occupancy forecasts, arrivals, and
booking pace. No LLM involved here — the graph nodes call these directly
and hand the resulting dict to the LLM as context. This is the same
"Metrics Layer" from v2.0, just without the CrewAI @tool wrapper, which
existed only so an LLM agent could decide when to call it. Since the
LangGraph nodes call these deterministically in code, that indirection
is gone.
"""

import math
from data.mock_hotel_data import get_occupancy_forecast, get_arrivals_today, get_booking_pace


def _clean(obj):
    """Recursively replace NaN/inf values with None so the dict stays JSON-safe."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    return obj


def get_occupancy_forecast_analysis(days: int = 30) -> dict:
    """
    Forward-looking occupancy data for the next N days: dates, occupancy %,
    rooms sold, ADR, room revenue, RevPAR. Flags soft dates (<50% occupancy)
    and high-demand dates (>85%).
    """
    df = get_occupancy_forecast(days).fillna("")

    soft_dates = df[df['occupancy_pct'] < 50][['date', 'day_of_week', 'occupancy_pct', 'adr']].to_dict('records')
    strong_dates = df[df['occupancy_pct'] > 85][['date', 'day_of_week', 'occupancy_pct', 'adr']].to_dict('records')

    result = {
        "period": f"Next {days} days",
        "avg_occupancy_pct": round(df['occupancy_pct'].mean(), 1),
        "avg_adr": round(df['adr'].mean(), 2),
        "avg_revpar": round(df['revpar'].mean(), 2),
        "projected_total_revenue": round(df['room_revenue'].sum(), 2),
        "soft_dates_count": len(soft_dates),
        "soft_dates": soft_dates[:5],
        "high_demand_dates_count": len(strong_dates),
        "high_demand_dates": strong_dates[:5],
    }
    return _clean(result)


def get_arrivals_analysis() -> dict:
    """
    Today's arrival list: guest names, room types, rates, channels, VIP
    flags, special requests. Flags OTA dependency if >60% of arrivals.
    """
    df = get_arrivals_today().fillna("")

    vips = df[df['vip'] == True].to_dict('records')
    special_requests = df[df['special_request'] != ""].to_dict('records')
    channel_mix = df['channel'].value_counts().to_dict()
    ota_pct = round(channel_mix.get('OTA', 0) / len(df) * 100, 1) if len(df) > 0 else 0

    result = {
        "total_arrivals": len(df),
        "vip_guests_count": len(vips),
        "vip_details": vips,
        "guests_with_requests": len(special_requests),
        "special_requests": special_requests[:5],
        "channel_mix": channel_mix,
        "ota_percentage": ota_pct,
        "ota_warning": ota_pct > 60,
        "avg_rate": round(df['rate'].mean(), 2) if len(df) else 0,
        "room_type_mix": df['room_type'].value_counts().to_dict(),
    }
    return _clean(result)


def get_booking_pace_analysis(days: int = 14) -> dict:
    """
    New bookings this year vs same period last year, for pickup analysis.
    """
    df = get_booking_pace(days).fillna("")

    total_this_year = int(df['bookings_this_year'].sum())
    total_last_year = int(df['bookings_last_year'].sum())
    pace_variance = total_this_year - total_last_year
    pace_pct = round((pace_variance / max(total_last_year, 1)) * 100, 1)

    behind_pace = df[df['pickup_variance'] < -3][
        ['arrival_date', 'bookings_this_year', 'bookings_last_year', 'pickup_variance']
    ].to_dict('records')

    result = {
        "period": f"Next {days} days",
        "total_bookings_this_year": total_this_year,
        "total_bookings_last_year": total_last_year,
        "pace_variance": pace_variance,
        "pace_pct_change": pace_pct,
        "pace_status": "AHEAD" if pace_pct > 5 else "BEHIND" if pace_pct < -5 else "ON PACE",
        "dates_behind_pace": behind_pace[:5],
    }
    return _clean(result)
