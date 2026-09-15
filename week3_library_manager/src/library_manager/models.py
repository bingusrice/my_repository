from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, date as datetime_date, datetime, timedelta
from enum import Enum

from .exceptions import (
    AlreadyReturnedError,
    BookUnavailableError,
    InsufficientFundsError,
    InvalidBookError,
    InvalidDateError,
    InvalidMoneyError,
    LibraryError,
    LoanExtensionLimitError,
    OverdueError,
)

DAILY_OVERDUE_FEE: int = 2000
DEFAULT_LOAN_DAYS: int = 7
MAX_EXTENSION_DAYS: int = 7


@dataclass(slots=True, frozen=True)
class Date:
    """날짜를 표현하는 클래스.

    요구사항:
    - 1~12월, 1~31일 범위만 날짜가 지정되도록 범위를 제한합니다.
    - 유효하지 않은 월이나 일에 대해 InvalidDateError를 발생시킵니다.
    """
    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        if not isinstance(self.year, int) or self.year < 1:
            raise InvalidDateError(f"연도는 1 이상의 정수여야 합니다: {self.year}")
        if not isinstance(self.month, int) or not (1 <= self.month <= 12):
            raise InvalidDateError(f"월은 1~12월 범위 내여야 합니다: {self.month}")
        if not isinstance(self.day, int) or not (1 <= self.day <= 31):
            raise InvalidDateError(f"일은 1~31일 범위 내여야 합니다: {self.day}")

        max_day = calendar.monthrange(self.year, self.month)[1]
        if self.day > max_day:
            raise InvalidDateError(
                f"{self.year}년 {self.month}월은 {max_day}일까지 있습니다. (입력값: {self.day}일)"
            )

    @classmethod
    def today(cls) -> Date:
        now = datetime.now()
        return cls(now.year, now.month, now.day)

    @classmethod
    def from_date(cls, d: datetime_date | datetime) -> Date:
        return cls(d.year, d.month, d.day)

    @classmethod
    def from_isoformat(cls, date_str: str) -> Date:
        clean = date_str.split("T")[0]
        parts = clean.split("-")
        if len(parts) != 3:
            raise InvalidDateError(f"올바른 날짜 형식이 아닙니다 (YYYY-MM-DD): {date_str}")
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError as exc:
            raise InvalidDateError(f"날짜 형식이 올바르지 않습니다: {date_str}") from exc
        return cls(year, month, day)

    def to_date(self) -> datetime_date:
        return datetime_date(self.year, self.month, self.day)

    def isoformat(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def next_day(self) -> Date:
        return self.add_days(1)

    def add_days(self, days: int) -> Date:
        new_d = self.to_date() + timedelta(days=days)
        return Date(new_d.year, new_d.month, new_d.day)

    def days_between(self, other: Date) -> int:
        return (self.to_date() - other.to_date()).days

    def __sub__(self, other: Date | int) -> int | Date:
        if isinstance(other, Date):
            return self.days_between(other)
        if isinstance(other, int):
            return self.add_days(-other)
        return NotImplemented

    def __add__(self, days: int) -> Date:
        if isinstance(days, int):
            return self.add_days(days)
        return NotImplemented

    def __lt__(self, other: Date) -> bool:
        if not isinstance(other, Date):
            return NotImplemented
        return (self.year, self.month, self.day) < (other.year, other.month, other.day)

    def __le__(self, other: Date) -> bool:
        if not isinstance(other, Date):
            return NotImplemented
        return (self.year, self.month, self.day) <= (other.year, other.month, other.day)

    def __gt__(self, other: Date) -> bool:
        if not isinstance(other, Date):
            return NotImplemented
        return (self.year, self.month, self.day) > (other.year, other.month, other.day)

    def __ge__(self, other: Date) -> bool:
        if not isinstance(other, Date):
            return NotImplemented
        return (self.year, self.month, self.day) >= (other.year, other.month, other.day)

    def __str__(self) -> str:
        return self.isoformat()

    def __repr__(self) -> str:
        return f"Date({self.year}, {self.month}, {self.day})"


@dataclass
class Money:
    """금액을 표현하고 연체료 계산 및 차감을 처리하는 클래스."""
    amount: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.amount, (int, float)):
            raise InvalidMoneyError("금액은 숫자여야 합니다.")
        self.amount = int(self.amount)
        if self.amount < 0:
            raise InvalidMoneyError(f"금액은 0원 이상이어야 합니다: {self.amount}원")

    def add(self, amount: int | Money) -> Money:
        val = amount.amount if isinstance(amount, Money) else int(amount)
        if val < 0:
            raise InvalidMoneyError("추가할 금액은 0원 이상이어야 합니다.")
        self.amount += val
        return self

    def deduct(self, amount: int | Money) -> Money:
        val = amount.amount if isinstance(amount, Money) else int(amount)
        if val < 0:
            raise InvalidMoneyError("차감할 금액은 0원 이상이어야 합니다.")
        if self.amount < val:
            raise InsufficientFundsError(
                f"돈이 부족합니다! (현재 보유: {self.amount:,}원, 필요: {val:,}원, 부족: {val - self.amount:,}원)"
            )
        self.amount -= val
        return self

    def can_afford(self, amount: int | Money) -> bool:
        val = amount.amount if isinstance(amount, Money) else int(amount)
        return self.amount >= val

    def __add__(self, other: int | Money) -> Money:
        val = other.amount if isinstance(other, Money) else int(other)
        return Money(self.amount + val)

    def __radd__(self, other: int | Money) -> Money:
        return self.__add__(other)

    def __sub__(self, other: int | Money) -> Money:
        val = other.amount if isinstance(other, Money) else int(other)
        if self.amount < val:
            raise InsufficientFundsError(
                f"돈이 부족합니다! (현재 보유: {self.amount:,}원, 필요: {val:,}원, 부족: {val - self.amount:,}원)"
            )
        return Money(self.amount - val)

    def __mul__(self, other: int) -> Money:
        if not isinstance(other, int):
            return NotImplemented
        if other < 0:
            raise InvalidMoneyError("배수는 0 이상이어야 합니다.")
        return Money(self.amount * other)

    def __rmul__(self, other: int) -> Money:
        return self.__mul__(other)

    def __int__(self) -> int:
        return self.amount

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self.amount == other.amount
        if isinstance(other, int):
            return self.amount == other
        return False

    def __lt__(self, other: Money | int) -> bool:
        val = other.amount if isinstance(other, Money) else int(other)
        return self.amount < val

    def __le__(self, other: Money | int) -> bool:
        val = other.amount if isinstance(other, Money) else int(other)
        return self.amount <= val

    def __gt__(self, other: Money | int) -> bool:
        val = other.amount if isinstance(other, Money) else int(other)
        return self.amount > val

    def __ge__(self, other: Money | int) -> bool:
        val = other.amount if isinstance(other, Money) else int(other)
        return self.amount >= val

    def __str__(self) -> str:
        return f"{self.amount:,}원"

    def __repr__(self) -> str:
        return f"Money({self.amount})"


class BookStatus(str, Enum):
    AVAILABLE = "available"
    LOANED = "loaned"


@dataclass(slots=True)
class Book:
    isbn: str
    title: str
    author: str
    status: BookStatus = BookStatus.AVAILABLE

    def __post_init__(self) -> None:
        self.isbn = self.isbn.strip()
        self.title = self.title.strip()
        self.author = self.author.strip()
        if not self.isbn or not self.title or not self.author:
            raise InvalidBookError("ISBN, 제목, 저자는 비어 있을 수 없습니다.")

    def borrow(self) -> None:
        if self.status is BookStatus.LOANED:
            raise BookUnavailableError(f"이미 대출 중인 도서입니다: {self.isbn}")
        self.status = BookStatus.LOANED

    def return_copy(self) -> None:
        if self.status is BookStatus.AVAILABLE:
            raise AlreadyReturnedError(f"이미 반납된 도서입니다: {self.isbn}")
        self.status = BookStatus.AVAILABLE


@dataclass(slots=True)
class Loan:
    loan_id: str
    book_isbn: str
    borrower: str
    borrowed_at: datetime
    due_date: Date | None = None
    returned_at: datetime | None = None
    borrowed_date: Date | None = None
    returned_date: Date | None = None
    extended_days: int = 0
    is_overdue_fee_paid: bool = False
    paid_fee: int = 0

    def __post_init__(self) -> None:
        if self.borrowed_date is None:
            self.borrowed_date = Date(
                self.borrowed_at.year, self.borrowed_at.month, self.borrowed_at.day
            )
        if self.due_date is None:
            self.due_date = self.borrowed_date.add_days(DEFAULT_LOAN_DAYS)
        if self.returned_at is not None and self.returned_date is None:
            self.returned_date = Date(
                self.returned_at.year, self.returned_at.month, self.returned_at.day
            )

    @property
    def is_active(self) -> bool:
        return self.returned_at is None and self.returned_date is None

    def get_overdue_days(self, current_date: Date) -> int:
        target_date = self.returned_date if (not self.is_active and self.returned_date) else current_date
        if self.due_date and target_date > self.due_date:
            return target_date - self.due_date
        return 0

    def get_total_overdue_fee(self, current_date: Date) -> Money:
        days = self.get_overdue_days(current_date)
        return Money(days * DAILY_OVERDUE_FEE)

    def get_overdue_fee(self, current_date: Date) -> Money:
        if self.is_overdue_fee_paid:
            return Money(0)
        return self.get_total_overdue_fee(current_date)

    def is_overdue(self, current_date: Date) -> bool:
        return self.get_overdue_days(current_date) > 0

    def extend_period(self, days: int = 7, current_date: Date | None = None) -> None:
        if not self.is_active:
            raise LibraryError(f"이미 반납 처리된 대출은 연장할 수 없습니다: {self.loan_id}")
        if current_date and self.is_overdue(current_date):
            raise OverdueError("연체된 도서는 기간을 연장할 수 없습니다. 연체료를 납부하고 반납해야 합니다.")
        if self.extended_days + days > MAX_EXTENSION_DAYS:
            raise LoanExtensionLimitError(
                f"대여 기간 연장은 최대 일주일({MAX_EXTENSION_DAYS}일)까지만 가능합니다. "
                f"(현재 연장: {self.extended_days}일, 추가 요청: {days}일)"
            )
        if self.due_date is None:
            self.due_date = (self.borrowed_date or Date.today()).add_days(DEFAULT_LOAN_DAYS)
        self.due_date = self.due_date.add_days(days)
        self.extended_days += days

    def pay_overdue_fee(self, user_money: Money, current_date: Date) -> Money:
        fee = self.get_overdue_fee(current_date)
        if fee.amount == 0:
            return Money(0)
        user_money.deduct(fee)
        self.is_overdue_fee_paid = True
        self.paid_fee += fee.amount
        return fee

    def close(
        self,
        returned_at: datetime | None = None,
        returned_date: Date | None = None,
    ) -> None:
        if not self.is_active:
            raise AlreadyReturnedError(f"이미 반납 처리된 대출입니다: {self.loan_id}")
        self.returned_at = returned_at or datetime.now(UTC)
        if returned_date is not None:
            self.returned_date = returned_date
        else:
            self.returned_date = Date(
                self.returned_at.year, self.returned_at.month, self.returned_at.day
            )
