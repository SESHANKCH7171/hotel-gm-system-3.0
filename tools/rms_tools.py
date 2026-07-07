"""
RMS Tools — Revenue Management System
──────────────────────────────────────
Plain, deterministic functions for competitor rate analysis and channel mix.
"""

from data.mock_hotel_data import get_comp_set_rates, get_channel_mix
from config import COMP_SET_RATE_GAP


def get_comp_set_analysis(days: int = 14) -> dict:
    """
    Competitor (comp set) rate data vs our property. Flags dates where we
    are significantly under- or over-priced vs the market.
    """
    df = get_comp_set_rates(days).fillna("")

    underpriced = df[df['gap'] < -COMP_SET_RATE_GAP].groupby('date').first().reset_index()
    overpriced = df[df['gap'] > COMP_SET_RATE_GAP].groupby('date').first().reset_index()
    avg_gap = round(df['gap'].mean(), 2)

    return {
        "analysis_period": f"Next {days} days",
        "avg_rate_gap_vs_market": avg_gap,
        "position": "UNDERPRICED" if avg_gap < -10 else "OVERPRICED" if avg_gap > 10 else "ALIGNED",
        "underpriced_dates_count": len(underpriced),
        "underpriced_dates": underpriced[['date', 'our_rate', 'comp_rate', 'gap']].to_dict('records') if not underpriced.empty else [],
        "overpriced_dates_count": len(overpriced),
        "overpriced_dates": overpriced[['date', 'our_rate', 'comp_rate', 'gap']].to_dict('records') if not overpriced.empty else [],
        "competitor_avg_gap": df.groupby('competitor')['gap'].mean().round(2).to_dict(),
    }


def get_channel_mix_analysis() -> dict:
    """
    Booking channel distribution and margin analysis. Flags OTA-driven
    commission leak.
    """
    df = get_channel_mix().fillna("")

    total_gross = df['gross_revenue'].sum()
    total_net = df['net_revenue'].sum()
    commission_leak = round(total_gross - total_net, 2)
    ota_bookings = df[df['channel'].str.contains('OTA')]['bookings'].sum()
    total_bookings = df['bookings'].sum()
    ota_pct = round(ota_bookings / max(total_bookings, 1) * 100, 1)

    return {
        "total_bookings": int(total_bookings),
        "total_gross_revenue": round(total_gross, 2),
        "total_net_revenue": round(total_net, 2),
        "total_commission_cost": commission_leak,
        "commission_leak_pct": round(commission_leak / max(total_gross, 1) * 100, 1),
        "ota_share_pct": ota_pct,
        "ota_warning": ota_pct > 50,
    }
