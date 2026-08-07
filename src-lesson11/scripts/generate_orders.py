"""Generate INSERT/UPDATE/DELETE OLTP traffic; Debezium observes the WAL."""

from __future__ import annotations

import argparse
import random
import re
import time
from decimal import Decimal

from _common import PG_DSN, pg_connect

STATUSES = ("pending", "paid", "shipped", "delivered", "cancelled")
# MAGNUM11 and VERIFY11 are deliberately absent: the migration and the verifier
# use them as unique canaries, so ordinary load must never be able to forge one.
DISCOUNTS = (None, "WELCOME10", "VIP20", "FREESHIP")


def redacted_dsn() -> str:
    """Show where we are writing without printing the password on a projector."""
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", PG_DSN)


def run(rate: float, duration: float, seed: int, log_every: float = 2.0) -> None:
    rng = random.Random(seed)
    counts = {"insert": 0, "update": 0, "delete": 0}
    horizon = "continuous — Ctrl-C to stop" if duration <= 0 else f"{duration:g}s"
    print(f"load generator → {redacted_dsn()}", flush=True)
    print(f"  rate={rate:g}/s  duration={horizon}  seed={seed}", flush=True)
    with pg_connect() as conn:
        has_discount = bool(
            conn.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='orders'
                  AND column_name='discount_code'
                """
            ).fetchone()
        )
        ids = [row[0] for row in conn.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 5000")]
        schema = "present" if has_discount else "absent (pre-migration writer)"
        print(f"  orders.discount_code: {schema}", flush=True)
        print(f"  id pool: {len(ids)} existing rows (updates/deletes draw from here)", flush=True)
        started = time.monotonic()
        next_tick = started
        last_log = started
        last_op = "-"
        stopped_by = "duration reached"
        try:
            while duration <= 0 or time.monotonic() - started < duration:
                choice = rng.random()
                if choice < 0.62 or not ids:
                    if has_discount:
                        row = conn.execute(
                            """
                            INSERT INTO orders
                                (customer_id, amount, status, discount_code)
                            VALUES (%s, %s, %s, %s) RETURNING id
                            """,
                            (
                                rng.randint(1, 1000), Decimal(rng.randrange(500, 50000)) / 100,
                                rng.choice(STATUSES[:3]), rng.choice(DISCOUNTS),
                            ),
                        ).fetchone()
                    else:
                        row = conn.execute(
                            """
                            INSERT INTO orders (customer_id, amount, status)
                            VALUES (%s, %s, %s) RETURNING id
                            """,
                            (
                                rng.randint(1, 1000), Decimal(rng.randrange(500, 50000)) / 100,
                                rng.choice(STATUSES[:3]),
                            ),
                        ).fetchone()
                    ids.append(row[0])
                    counts["insert"] += 1
                    last_op = f"INSERT id={row[0]}"
                elif choice < 0.92:
                    order_id = rng.choice(ids)
                    conn.execute(
                        "UPDATE orders SET status=%s WHERE id=%s",
                        (rng.choice(STATUSES), order_id),
                    )
                    counts["update"] += 1
                    last_op = f"UPDATE id={order_id}"
                else:
                    index = rng.randrange(len(ids))
                    order_id = ids.pop(index)
                    conn.execute("DELETE FROM orders WHERE id=%s", (order_id,))
                    counts["delete"] += 1
                    last_op = f"DELETE id={order_id}"
                conn.commit()
                # Heartbeat: without this the process looks hung for the whole
                # lesson. "actual" is the achieved commit rate — during the
                # backpressure demo it visibly falls short of the requested one.
                now = time.monotonic()
                if log_every > 0 and now - last_log >= log_every:
                    elapsed = now - started
                    total = sum(counts.values())
                    print(
                        f"[{elapsed:6.1f}s] {total:6d} commits  {total / elapsed:5.1f}/s actual"
                        f"  insert={counts['insert']} update={counts['update']}"
                        f" delete={counts['delete']}  pool={len(ids)}  last={last_op}",
                        flush=True,
                    )
                    last_log = now
                if rate > 0:
                    next_tick += 1 / rate
                    time.sleep(max(0, next_tick - time.monotonic()))
        except KeyboardInterrupt:
            stopped_by = "Ctrl-C"
        elapsed = max(time.monotonic() - started, 1e-9)
    total = sum(counts.values())
    print(
        f"stopped ({stopped_by}) after {elapsed:.1f}s — generated "
        + ", ".join(f"{key}={value}" for key, value in counts.items())
        + f", total={total} at {total / elapsed:.1f}/s",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=10, help="committed changes per second")
    parser.add_argument("--duration", type=float, default=60, help="seconds; 0 runs until Ctrl-C")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument(
        "--log-every", type=float, default=2.0, help="progress line every N seconds; 0 = silent"
    )
    args = parser.parse_args()
    run(args.rate, args.duration, args.seed, args.log_every)

