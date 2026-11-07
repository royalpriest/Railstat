"""Regenerate samples/bookings_sample.xlsx: made-up bookings, including a few bad rows.

Run: python samples/make_sample.py
"""

import datetime as dt
import random
from pathlib import Path

import openpyxl

ROUTES = ["Toronto-Montreal", "Toronto-Ottawa", "Ottawa-Montreal", "Montreal-Quebec City", "Toronto-Kingston"]
CLASSES = [("Economy", 70), ("Business", 140), ("First", 210)]
FIRST = ["Ann", "Bo", "Cy", "Di", "Ed", "Fay", "Gus", "Hana", "Ivo", "Jo", "Kai", "Lea", "Max", "Noor"]
LAST = ["Lee", "Chan", "Diaz", "Eng", "Fox", "Gray", "Hill", "Ito", "Jones", "Khan", "Lopez", "Moss", "Nash"]


def main() -> None:
    rng = random.Random(1002)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Bookings"
    sheet.append(
        [
            "TicketID",
            "PassengerName",
            "Route",
            "Class",
            "Price",
            "Status",
            "Date",
            "DiscountApplied",
            "LoyaltyMember",
        ]
    )
    start = dt.datetime(2026, 9, 7)
    for n in range(1, 61):
        ticket_class, base = rng.choices(CLASSES, weights=[65, 26, 9])[0]
        sheet.append(
            [
                f"TB-{1000 + n}",
                f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                rng.choices(ROUTES, weights=[35, 26, 18, 12, 9])[0],
                ticket_class,
                round(base * rng.uniform(0.9, 1.3), 2),
                rng.choices(["Confirmed", "Cancelled"], weights=[86, 14])[0],
                start + dt.timedelta(days=rng.randrange(56)),
                rng.choice([0, 0, 0, 5, 10, 15]),
                rng.choice(["Yes", "No"]),
            ]
        )
    # Messy rows the report should flag instead of crashing on.
    sheet.append(["TB-1061", "Pat Quinn", "Toronto-Ottawa", "Economy", "$5O", "Confirmed", start, 0, "Yes"])
    sheet.append(["TB-1062", "Ria Shah", "Ottawa-Montreal", "Economy", 72.5, None, start, 0, "No"])
    sheet.append(["TB-1063", "Sam Tran", "Toronto-Kingston", "First", 230, "Pending", start, 0, "Yes"])
    workbook.save(Path(__file__).with_name("bookings_sample.xlsx"))


if __name__ == "__main__":
    main()
