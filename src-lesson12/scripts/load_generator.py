"""Stable lesson entry point for the OLTP load generator."""

from generate_orders import run

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=10, help="committed changes per second")
    parser.add_argument("--duration", type=float, default=60, help="seconds; 0 = continuous")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument(
        "--log-every", type=float, default=2.0, help="progress line every N seconds; 0 = silent"
    )
    args = parser.parse_args()
    run(args.rate, args.duration, args.seed, args.log_every)

