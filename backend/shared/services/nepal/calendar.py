"""Bikram Sambat (BS) calendar: month lengths, AD conversion, and Nepal's Shrawan-to-Asar fiscal year.

BS month lengths change every year and can't be computed, so they come from a published table
(the `calendar_bs.csv` dataset shipped with the nepali-datetime package). Extend MONTH_DAYS when a new
year's calendar is published.
"""
from dataclasses import dataclass
from datetime import date, timedelta

MONTHS = ("Baisakh", "Jestha", "Asar", "Shrawan", "Bhadra", "Asoj",
          "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra")
SHRAWAN = 4  # first month of the fiscal year

MONTH_DAYS: dict[int, tuple[int, ...]] = {
    2078: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2079: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2080: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2081: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2082: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2083: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2084: (31, 31, 32, 31, 31, 30, 30, 30, 29, 30, 30, 30),
    2085: (31, 32, 31, 32, 30, 31, 30, 30, 29, 30, 30, 30),
    2086: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
    2087: (31, 31, 32, 31, 31, 31, 30, 29, 30, 30, 30, 30),
    2088: (30, 31, 32, 32, 30, 31, 30, 30, 29, 30, 30, 30),
    2089: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
    2090: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
}
EPOCH_BS_YEAR = 2078
EPOCH_AD = date(2021, 4, 14)  # 1 Baisakh 2078


@dataclass(frozen=True)
class BSMonth:
    year: int
    month: int  # 1 = Baisakh … 12 = Chaitra

    @property
    def name(self) -> str:
        return MONTHS[self.month - 1]

    @property
    def label(self) -> str:
        return f"{self.name} {self.year}"

    @property
    def days(self) -> int:
        return _days(self.year)[self.month - 1]

    @property
    def start(self) -> date:
        offset = sum(sum(_days(y)) for y in range(EPOCH_BS_YEAR, self.year))
        offset += sum(_days(self.year)[: self.month - 1])
        return EPOCH_AD + timedelta(days=offset)

    @property
    def end(self) -> date:
        return self.start + timedelta(days=self.days - 1)

    @property
    def fiscal_year(self) -> str:
        """e.g. '2083/84' for any month from Shrawan 2083 to Asar 2084."""
        first = self.year if self.month >= SHRAWAN else self.year - 1
        return f"{first}/{(first + 1) % 100:02d}"

    @property
    def fiscal_index(self) -> int:
        """1 for Shrawan … 12 for Asar."""
        return (self.month - SHRAWAN) % 12 + 1

    def next(self) -> "BSMonth":
        return BSMonth(self.year + 1, 1) if self.month == 12 else BSMonth(self.year, self.month + 1)

    def previous(self) -> "BSMonth":
        return BSMonth(self.year - 1, 12) if self.month == 1 else BSMonth(self.year, self.month - 1)


def _days(year: int) -> tuple[int, ...]:
    if year not in MONTH_DAYS:
        raise ValueError(f"No Bikram Sambat calendar loaded for {year} BS")
    return MONTH_DAYS[year]


def month_of(day: date) -> BSMonth:
    """The BS month that contains an AD date."""
    left = (day - EPOCH_AD).days
    if left < 0:
        raise ValueError(f"{day} is before {EPOCH_BS_YEAR} BS")
    year = EPOCH_BS_YEAR
    while left >= sum(_days(year)):
        left -= sum(_days(year))
        year += 1
    for month, length in enumerate(_days(year), start=1):
        if left < length:
            return BSMonth(year, month)
        left -= length
    raise AssertionError("unreachable")


def last_completed_month(today: date) -> BSMonth:
    return month_of(today).previous()
