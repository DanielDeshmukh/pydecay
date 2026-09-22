"""Runnable pydecay quickstart (mirrors docs/quickstart.md)."""

from pydecay import DecayChain, Nuclide, decayed_activity, remaining_fraction


def main() -> None:
    i131 = Nuclide.load("I-131")
    a = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)
    print(f"I-131 after one half-life: {a:.1f} Bq (expect 500.0)")

    f = remaining_fraction(half_life=i131.half_life, time=5 * i131.half_life)
    print(f"fraction after 5 half-lives: {f:.5f} (expect 0.03125)")

    chain = DecayChain([0.693, 0.0], names=["parent", "stable"])
    print("chain at t=1 day:", chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))


if __name__ == "__main__":
    main()
