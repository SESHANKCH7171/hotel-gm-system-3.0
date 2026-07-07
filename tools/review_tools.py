"""
Review Tools — Guest Reputation Intelligence
─────────────────────────────────────────────
Plain, deterministic function for multi-platform review analysis.
"""

from data.mock_hotel_data import get_reviews


def get_review_analysis(days: int = 30) -> dict:
    """
    Recent guest reviews from all platforms: sentiment breakdown, recurring
    complaint themes, flagged departments, and unresponded negative reviews.
    """
    df = get_reviews(days).fillna("")

    avg_score = round(df['score'].mean(), 2)
    low_reviews = df[df['score'] <= 2]
    unresponded = df[(df['score'] <= 3) & (df['responded'] == False)]
    dept_scores = df.groupby('department')['score'].mean().round(2).to_dict()
    platform_avg = df.groupby('platform')['score'].mean().round(2).to_dict()
    worst_dept = min(dept_scores, key=dept_scores.get) if dept_scores else "N/A"

    return {
        "total_reviews_analysed": len(df),
        "avg_score": avg_score,
        "score_status": "CRITICAL" if avg_score < 3.0 else "WARNING" if avg_score < 3.8 else "HEALTHY",
        "low_score_reviews_count": len(low_reviews),
        "unresponded_negative_reviews": len(unresponded),
        "urgent_responses_needed": unresponded[['date', 'platform', 'score', 'text']].to_dict('records')[:5],
        "department_scores": dept_scores,
        "worst_department": worst_dept,
        "worst_department_score": dept_scores.get(worst_dept, 0),
        "platform_breakdown": platform_avg,
        "recurring_complaints": low_reviews['text'].tolist()[:5],
        "response_rate_pct": round(df['responded'].mean() * 100, 1),
    }
