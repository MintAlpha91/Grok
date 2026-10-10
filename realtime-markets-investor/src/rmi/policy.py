"""Hard boundaries. Research briefs only."""

OUT_OF_SCOPE = (
    "Brokerage API keys (including Stake)",
    "Live order placement, cancellation, or amendment",
    "Moving, withdrawing, or contributing money",
    "Reading SMSF balances or treating SMSF assets as personal cash",
    "Position sizing and buy, sell, or hold instructions",
    "Paid or licensed realtime feeds until Jason opts in",
)


class OutOfScope(RuntimeError):
    """Raised when a caller reaches a capability this build refuses."""


def place_order(*_args, **_kwargs):
    """Future opt-in only. Jason must say so before any order path exists.

    This function is the boundary marker. It cannot submit an order.
    """

    raise OutOfScope(
        "Live order placement is out of scope. "
        "This build cannot submit, cancel, or amend orders. "
        "A brokerage connection requires Jason's explicit say-so."
    )


def banner_lines():
    return [
        "Not a trade instruction. This brief does not buy, sell, hold, size, or move money.",
        "SMSF assets are not personal cash.",
        "Figures appear only when a public feed returned them. Missing data stays missing.",
    ]
