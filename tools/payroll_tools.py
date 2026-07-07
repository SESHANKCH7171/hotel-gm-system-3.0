"""
Payroll Tools — Labour Cost Intelligence
─────────────────────────────────────────
Plain, deterministic function for departmental payroll vs budget analysis.
"""

from data.mock_hotel_data import get_payroll_data
from config import PAYROLL_SPIKE_THRESHOLD


def get_payroll_analysis() -> dict:
    """
    Current month payroll vs budget by department. Flags departments with
    labour cost spikes above PAYROLL_SPIKE_THRESHOLD.
    """
    df = get_payroll_data().fillna("")

    spikes = df[df['variance_pct'] > PAYROLL_SPIKE_THRESHOLD]
    total_budget = df['budget'].sum()
    total_actual = df['actual'].sum()
    total_variance = round(total_actual - total_budget, 2)
    total_variance_pct = round((total_variance / max(total_budget, 1)) * 100, 1)

    worst_dept = df.loc[df['variance_pct'].idxmax()] if not df.empty else None
    worst_info = {
        "department": worst_dept['department'],
        "budget": worst_dept['budget'],
        "actual": worst_dept['actual'],
        "variance_pct": worst_dept['variance_pct'],
        "dollar_overrun": round(worst_dept['actual'] - worst_dept['budget'], 2),
    } if worst_dept is not None else {}

    return {
        "total_payroll_budget": round(total_budget, 2),
        "total_payroll_actual": round(total_actual, 2),
        "total_variance_dollars": total_variance,
        "total_variance_pct": total_variance_pct,
        "overall_status": "OVER BUDGET" if total_variance_pct > 5 else "ON TRACK",
        "departments_over_budget": len(spikes),
        "flagged_departments": spikes[['department', 'budget', 'actual', 'variance_pct']].to_dict('records'),
        "worst_offender": worst_info,
    }
