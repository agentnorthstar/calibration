"""
Invarians — Clopper-Pearson exact binomial confidence intervals.

Used to report TPR / FPR with 95% CI in all backtest_*.md files.

Usage:
    python ci_binomial.py                        # show published values + CI
    python ci_binomial.py --k 4 --n 4            # custom
    python ci_binomial.py --k 369 --n 29942      # ETH FPR case

References:
    Clopper, C. J., and E. S. Pearson (1934). "The use of confidence or fiducial
    limits illustrated in the case of the binomial." Biometrika 26 (4): 404-413.

Exact method (no normal approximation). Recommended for small k/n or k≈0/n≈n.
"""
import argparse
from scipy.stats import beta


def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    """
    Return (lo, hi) of the (1-alpha) two-sided Clopper-Pearson CI for k/n.

    k : number of successes (e.g. events detected, false alarms)
    n : total number of trials (e.g. n_events, n_normal_windows)
    alpha : significance level (0.05 = 95% CI)
    """
    if n == 0:
        return (0.0, 1.0)
    if k < 0 or k > n:
        raise ValueError(f"k must be in [0, n], got k={k}, n={n}")
    lo = beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return lo, hi


def fmt(p: float) -> str:
    return f"{p * 100:.2f}%"


def main():
    parser = argparse.ArgumentParser(description="Clopper-Pearson exact binomial CI")
    parser.add_argument("--k", type=int, default=None, help="successes")
    parser.add_argument("--n", type=int, default=None, help="trials")
    parser.add_argument("--alpha", type=float, default=0.05, help="significance (default 0.05)")
    args = parser.parse_args()

    if args.k is not None and args.n is not None:
        lo, hi = clopper_pearson(args.k, args.n, args.alpha)
        p = args.k / args.n if args.n else 0.0
        print(f"\n  k/n = {args.k}/{args.n}  point estimate = {fmt(p)}")
        print(f"  IC{(1-args.alpha)*100:.0f}% Clopper-Pearson = [{fmt(lo)} ; {fmt(hi)}]\n")
        return

    # Default: show published Invarians backtest values
    cases = [
        ("ETH — TPR",          4,       4, "4 events ground truth: DeFi Summer, NFT Mania, Merge, Shanghai"),
        ("POL — TPR",          4,       4, "4 events: Network Halt, Gas Crisis, Heimdall/Bor, Reorg Storm"),
        ("SOL τ — TPR",        4,       4, "4 outages: Sept 2021, Jan 2022, May 2022, Oct 2022"),
        ("ETH — FPR (τ+π)",  369,  29_942, "n_false_alarms / n_normal_windows (threshold_s2=1.12 + 2-of-3 D2)"),
        ("POL — FPR (τ+π)", 3226,  27_249, "n_false_alarms / n_normal_windows (threshold_s2=1.04 + 2-of-3 D2)"),
        ("SOL — FPR_τ",     2224, 127_354, "n_false_alarms / n_normal_windows (threshold_s2=1.12 rhythm-only)"),
    ]

    print("\n  Invarians — TPR / FPR with exact Clopper-Pearson IC95%\n")
    print(f"  {'Metric':<18}  {'k':>5}  {'n':>8}  {'point':>7}  {'IC95%':<24}  description")
    print(f"  {'-'*18}  {'-'*5}  {'-'*8}  {'-'*7}  {'-'*24}  {'-'*60}")
    for label, k, n, desc in cases:
        lo, hi = clopper_pearson(k, n)
        p = k / n
        ci = f"[{fmt(lo)} ; {fmt(hi)}]"
        print(f"  {label:<18}  {k:>5}  {n:>8,}  {fmt(p):>7}  {ci:<24}  {desc}")
    print()


if __name__ == "__main__":
    main()
