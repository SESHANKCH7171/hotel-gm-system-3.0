"""
Mock Hotel Data Generators
──────────────────────────
Generates realistic hotel operations data with injected anomalies
for PMS, RMS, Reviews, and Payroll systems.
"""

import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random

fake = Faker()


def get_occupancy_forecast(days: int = 30) -> pd.DataFrame:
    """
    Simulates PMS forward occupancy data for the next N days.
    Injects soft-date anomalies mid-month to test anomaly detection.
    """
    today = datetime.today()
    dates = [today + timedelta(days=i) for i in range(days)]

    data = []
    for date in dates:
        is_weekend = date.weekday() >= 4
        base = 75 if is_weekend else 55
        occupancy = min(100, max(20, base + random.gauss(0, 10)))

        # Inject anomaly — soft dates mid-month
        if date.day in [18, 19, 20]:
            occupancy = random.uniform(25, 38)

        rooms_available = 150
        rooms_sold = int((occupancy / 100) * rooms_available)
        adr = round(random.uniform(110, 180), 2)
        room_revenue = rooms_sold * adr
        revpar = round(room_revenue / rooms_available, 2)

        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "day_of_week": date.strftime("%A"),
            "occupancy_pct": round(occupancy, 1),
            "rooms_sold": rooms_sold,
            "rooms_available": rooms_available,
            "adr": adr,
            "room_revenue": round(room_revenue, 2),
            "revpar": revpar,
        })
    return pd.DataFrame(data)


def get_comp_set_rates(days: int = 14) -> pd.DataFrame:
    """
    Simulates competitor (comp set) rate data for the next N days.
    Compares our property against 4 competitors.
    """
    today = datetime.today()
    competitors = ["Hilton Garden Inn", "Marriott Courtyard", "Hyatt Place", "IHG Holiday Inn"]

    data = []
    for i in range(days):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        our_rate = round(random.uniform(130, 170), 2)

        for comp in competitors:
            comp_rate = round(our_rate + random.gauss(0, 25), 2)
            data.append({
                "date": date,
                "our_rate": our_rate,
                "competitor": comp,
                "comp_rate": max(80, comp_rate),
                "gap": round(our_rate - max(80, comp_rate), 2),
            })
    return pd.DataFrame(data)


def get_reviews(n: int = 20) -> pd.DataFrame:
    """
    Simulates recent guest reviews from multiple platforms.
    Each review is tagged with a department for root-cause analysis.
    """
    sentiments = [
        ("Great location, horrible check-in process", 2, "Operations"),
        ("Room was clean, breakfast was disappointing", 3, "F&B"),
        ("Staff were incredibly helpful and kind", 5, "Service"),
        ("AC not working, took 3 hours to fix", 1, "Maintenance"),
        ("Best hotel in the city, will return!", 5, "General"),
        ("Overpriced for what you get", 2, "Value"),
        ("WiFi keeps dropping, very frustrating", 2, "Tech"),
        ("Amazing spa experience", 5, "Spa"),
        ("Room was not ready at check-in time", 3, "Operations"),
        ("Noise from the street was unbearable", 2, "Rooms"),
        ("Concierge recommended a fantastic restaurant", 5, "Service"),
        ("Bathroom was not clean upon arrival", 1, "Housekeeping"),
        ("Pool area was excellent and well-maintained", 4, "Facilities"),
        ("Late checkout request was denied rudely", 2, "Front Desk"),
        ("Loved the rooftop bar atmosphere", 5, "F&B"),
    ]

    reviews = []
    for _ in range(n):
        text, score, dept = random.choice(sentiments)
        reviews.append({
            "date": (datetime.today() - timedelta(days=random.randint(0, 14))).strftime("%Y-%m-%d"),
            "platform": random.choice(["Google", "TripAdvisor", "Booking.com"]),
            "score": score,
            "text": text,
            "department": dept,
            "responded": random.choice([True, False]),
        })
    return pd.DataFrame(reviews)


def get_payroll_data() -> pd.DataFrame:
    """
    Simulates departmental payroll vs budget.
    Injects a cost spike in Housekeeping to test anomaly detection.
    """
    departments = ["Front Office", "Housekeeping", "F&B", "Maintenance", "Sales"]
    data = []
    for dept in departments:
        budget = random.uniform(18000, 45000)
        # Inject anomaly in Housekeeping — overtime spike
        if dept == "Housekeeping":
            actual = budget * random.uniform(1.12, 1.22)
        else:
            actual = budget * random.uniform(0.92, 1.05)

        data.append({
            "department": dept,
            "budget": round(budget, 2),
            "actual": round(actual, 2),
            "variance_pct": round(((actual - budget) / budget) * 100, 1),
            "headcount_budget": random.randint(5, 25),
            "headcount_actual": random.randint(5, 25),
        })
    return pd.DataFrame(data)


def get_arrivals_today() -> pd.DataFrame:
    """
    Generates today's arrival list with VIP flags, special requests,
    booking channels, and room types.
    """
    arrivals = []
    for _ in range(random.randint(15, 35)):
        arrivals.append({
            "guest_name": fake.name(),
            "room_type": random.choice(["Standard", "Deluxe", "Suite", "Executive"]),
            "nights": random.randint(1, 7),
            "rate": round(random.uniform(120, 280), 2),
            "channel": random.choice(["Direct", "OTA", "Corporate", "GDS"]),
            "vip": random.choice([True, False, False, False]),
            "special_request": random.choice([
                "High floor", "Early check-in", "Extra pillows",
                "Anniversary setup", "Late checkout", "", "", "",
            ]),
        })
    return pd.DataFrame(arrivals)


def get_booking_pace(days: int = 14) -> pd.DataFrame:
    """
    Simulates booking pace — new bookings received per day
    for future arrival dates. Used for pickup analysis.
    """
    today = datetime.today()
    data = []
    for i in range(days):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        # This year's pace
        this_year = random.randint(3, 18)
        # Last year's pace (generally slightly different)
        last_year = this_year + random.randint(-5, 5)
        data.append({
            "arrival_date": date,
            "bookings_this_year": max(0, this_year),
            "bookings_last_year": max(0, last_year),
            "pickup_variance": this_year - last_year,
        })
    return pd.DataFrame(data)


def get_channel_mix() -> pd.DataFrame:
    """
    Simulates booking channel distribution for margin analysis.
    OTA bookings have higher commission costs.
    """
    channels = {
        "Direct Website": {"bookings": random.randint(80, 150), "commission_pct": 0},
        "OTA - Booking.com": {"bookings": random.randint(60, 120), "commission_pct": 15},
        "OTA - Expedia": {"bookings": random.randint(40, 90), "commission_pct": 18},
        "Corporate": {"bookings": random.randint(30, 70), "commission_pct": 5},
        "GDS": {"bookings": random.randint(20, 50), "commission_pct": 10},
        "Walk-in": {"bookings": random.randint(10, 30), "commission_pct": 0},
    }
    data = []
    for channel, info in channels.items():
        avg_rate = round(random.uniform(120, 200), 2)
        revenue = round(info["bookings"] * avg_rate, 2)
        net_revenue = round(revenue * (1 - info["commission_pct"] / 100), 2)
        data.append({
            "channel": channel,
            "bookings": info["bookings"],
            "avg_rate": avg_rate,
            "gross_revenue": revenue,
            "commission_pct": info["commission_pct"],
            "net_revenue": net_revenue,
        })
    return pd.DataFrame(data)
