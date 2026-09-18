"""Indian number formatting for report text."""


def inr(amount: float) -> str:
    """139700 -> '₹1,39,700'"""
    rupees = int(round(amount))
    sign, s = ("-", str(-rupees)) if rupees < 0 else ("", str(rupees))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{sign}₹{s}"


def plural(n: int, word: str, plural_word: str | None = None) -> str:
    return f"{n} {word if n == 1 else (plural_word or word + 's')}"
