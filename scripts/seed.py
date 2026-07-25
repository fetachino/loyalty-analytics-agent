"""Seed the database with deterministic, realistic sample data."""

import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy import delete

from loyalty_analytics.database import SessionLocal
from loyalty_analytics.models import Customer, Reward, Transaction

CUSTOMER_COUNT = 100
TRANSACTION_COUNT = 1_000
REWARD_COUNT = 100
SEED = 42

MERCHANTS = {
    "Dining": ["Harbor Bistro", "Juniper Cafe", "Copper Table"],
    "Grocery": ["Fresh Market", "Green Valley Foods", "Daily Basket"],
    "Travel": ["Skyline Airlines", "Horizon Hotels", "Metro Rail"],
    "Retail": ["Northstar Outfitters", "Modern Home", "Parkside Books"],
    "Entertainment": ["Grand Cinema", "Soundstage", "City Arts"],
}
REWARDS = [
    ("$5 Account Credit", 500),
    ("Free Beverage", 750),
    ("$10 Account Credit", 1_000),
    ("Priority Boarding", 1_500),
    ("Complimentary Night", 5_000),
]


def seed() -> None:
    fake = Faker("en_US")
    Faker.seed(SEED)
    random.seed(SEED)
    now = datetime.now(UTC)

    customers: list[Customer] = []
    for index in range(CUSTOMER_COUNT):
        profile = fake.simple_profile()
        joined = fake.date_between(start_date="-5y", end_date="-30d")
        customers.append(
            Customer(
                first_name=str(profile["name"]).split()[0],
                last_name=str(profile["name"]).split()[-1],
                email=f"customer{index + 1}@example.com",
                city=fake.city(),
                state=fake.state_abbr(),
                loyalty_tier=random.choices(
                    ["Bronze", "Silver", "Gold", "Platinum"], weights=[40, 30, 20, 10]
                )[0],
                points_balance=random.randint(100, 20_000),
                join_date=joined if isinstance(joined, date) else joined.date(),
            )
        )

    with SessionLocal.begin() as session:
        session.execute(delete(Reward))
        session.execute(delete(Transaction))
        session.execute(delete(Customer))
        session.add_all(customers)
        session.flush()

        transactions: list[Transaction] = []
        for _ in range(TRANSACTION_COUNT):
            customer = random.choice(customers)
            category = random.choice(list(MERCHANTS))
            amount = Decimal(str(round(random.uniform(5, 500), 2)))
            earliest = datetime.combine(customer.join_date, datetime.min.time(), tzinfo=UTC)
            transactions.append(
                Transaction(
                    customer_id=customer.id,
                    merchant=random.choice(MERCHANTS[category]),
                    category=category,
                    purchase_amount=amount,
                    points_earned=int(amount),
                    purchase_date=fake.date_time_between(
                        start_date=earliest, end_date=now, tzinfo=UTC
                    ),
                )
            )
        session.add_all(transactions)

        rewards: list[Reward] = []
        for _ in range(REWARD_COUNT):
            customer = random.choice(customers)
            reward_name, points = random.choice(REWARDS)
            rewards.append(
                Reward(
                    customer_id=customer.id,
                    reward_name=reward_name,
                    points_used=points,
                    redeemed_at=now - timedelta(days=random.randint(0, 365)),
                )
            )
        session.add_all(rewards)

    print(
        f"Seeded {CUSTOMER_COUNT} customers, {TRANSACTION_COUNT} transactions, "
        f"and {REWARD_COUNT} rewards."
    )


if __name__ == "__main__":
    seed()
