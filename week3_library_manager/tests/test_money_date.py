from __future__ import annotations

import pytest

from library_manager.exceptions import (
    InsufficientFundsError,
    InvalidDateError,
    InvalidMoneyError,
    LoanExtensionLimitError,
    OverdueError,
)
from library_manager.models import (
    DAILY_OVERDUE_FEE,
    MAX_EXTENSION_DAYS,
    BookStatus,
    Date,
    Money,
)
from library_manager.repository import InMemoryLibraryRepository
from library_manager.service import LibraryService


# ==========================================
# Date 클래스 테스트
# ==========================================

def test_date_valid_creation() -> None:
    d = Date(2026, 9, 15)
    assert d.year == 2026
    assert d.month == 9
    assert d.day == 15
    assert str(d) == "2026-09-15"


def test_date_month_range_restriction() -> None:
    # 1~12월 범위 밖인 경우 예외 발생
    with pytest.raises(InvalidDateError):
        Date(2026, 0, 15)
    with pytest.raises(InvalidDateError):
        Date(2026, 13, 1)
    with pytest.raises(InvalidDateError):
        Date(2026, -1, 10)


def test_date_day_range_restriction() -> None:
    # 1~31일 범위 밖인 경우 예외 발생
    with pytest.raises(InvalidDateError):
        Date(2026, 5, 0)
    with pytest.raises(InvalidDateError):
        Date(2026, 5, 32)
    with pytest.raises(InvalidDateError):
        Date(2026, 5, -5)


def test_date_invalid_calendar_day_rejected() -> None:
    # 윤년이 아닌 2026년 2월 29일은 불가
    with pytest.raises(InvalidDateError):
        Date(2026, 2, 29)
    # 4월 31일은 불가 (4월은 30일까지)
    with pytest.raises(InvalidDateError):
        Date(2026, 4, 31)
    # 윤년인 2024년 2월 29일은 유효
    d = Date(2024, 2, 29)
    assert d.day == 29


def test_date_next_day_and_add_days() -> None:
    d = Date(2026, 1, 31)
    next_d = d.next_day()
    assert next_d == Date(2026, 2, 1)

    year_end = Date(2026, 12, 31)
    assert year_end.next_day() == Date(2027, 1, 1)

    d2 = Date(2026, 9, 15)
    assert d2.add_days(7) == Date(2026, 9, 22)
    assert d2 + 7 == Date(2026, 9, 22)


def test_date_subtraction_and_comparison() -> None:
    d1 = Date(2026, 9, 15)
    d2 = Date(2026, 9, 22)
    assert d2 - d1 == 7
    assert d2 - 7 == d1

    assert d1 < d2
    assert d1 <= d2
    assert d2 > d1
    assert d2 >= d1
    assert d1 == Date(2026, 9, 15)


def test_date_isoformat_round_trip() -> None:
    s = "2026-09-15"
    d = Date.from_isoformat(s)
    assert d == Date(2026, 9, 15)
    assert d.isoformat() == s


# ==========================================
# Money 클래스 테스트
# ==========================================

def test_money_creation_and_formatting() -> None:
    m = Money(5000)
    assert m.amount == 5000
    assert str(m) == "5,000원"
    assert repr(m) == "Money(5000)"


def test_money_negative_rejected() -> None:
    with pytest.raises(InvalidMoneyError):
        Money(-1000)


def test_money_add_and_deduct() -> None:
    m = Money(1000)
    m.add(1000)
    assert m.amount == 2000
    m.deduct(500)
    assert m.amount == 1500


def test_money_insufficient_funds_warning_raises_exception() -> None:
    wallet = Money(1000)
    fee = Money(2000)
    with pytest.raises(InsufficientFundsError) as exc_info:
        wallet.deduct(fee)
    assert "돈이 부족합니다" in str(exc_info.value)
    assert "필요: 2,000원" in str(exc_info.value)


def test_money_operators() -> None:
    m1 = Money(1000)
    m2 = Money(2000)
    assert m1 + m2 == Money(3000)
    assert m1 + 1000 == Money(2000)
    assert 1000 + m1 == Money(2000)
    assert m2 - m1 == Money(1000)
    assert m1 * 3 == Money(3000)
    assert m1 < m2


# ==========================================
# 연체료 계산 및 지불 테스트
# ==========================================

def test_overdue_fee_calculation_2000_won_per_day() -> None:
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 1),
    )
    book = service.register_book("9788966260959", "파이썬", "저자")
    loan = service.borrow_book(book.isbn, "홍길동")

    # 대출일: 2026-09-01, 반납 예정일: 2026-09-08
    assert loan.due_date == Date(2026, 9, 8)

    # 9월 8일 (정상 기한 내) -> 연체 0일, 연체료 0원
    service.set_current_date(Date(2026, 9, 8))
    assert loan.get_overdue_days(service.get_current_date()) == 0
    assert loan.get_overdue_fee(service.get_current_date()) == Money(0)

    # 9월 9일 (1일 연체) -> 2000원
    service.set_current_date(Date(2026, 9, 9))
    assert loan.get_overdue_days(service.get_current_date()) == 1
    assert loan.get_overdue_fee(service.get_current_date()) == Money(2000)

    # 9월 12일 (4일 연체) -> 8000원
    service.set_current_date(Date(2026, 9, 12))
    assert loan.get_overdue_days(service.get_current_date()) == 4
    assert loan.get_overdue_fee(service.get_current_date()) == Money(8000)


def test_pay_overdue_fee_insufficient_funds() -> None:
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 1),
    )
    book = service.register_book("1", "도서", "저자")
    loan = service.borrow_book(book.isbn, "학생")

    # 3일 연체 (9월 11일, 반납예정일 9월 8일) -> 6000원 필요
    service.set_current_date(Date(2026, 9, 11))
    wallet = Money(4000)  # 4000원만 보유

    with pytest.raises(InsufficientFundsError):
        service.pay_overdue_fee(loan.loan_id, wallet)

    # 잔액 부족으로 결제되지 않음
    assert wallet.amount == 4000
    assert not loan.is_overdue_fee_paid


def test_pay_overdue_fee_success() -> None:
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 1),
    )
    book = service.register_book("1", "도서", "저자")
    loan = service.borrow_book(book.isbn, "학생")

    # 2일 연체 (9월 10일) -> 4000원 필요
    service.set_current_date(Date(2026, 9, 10))
    wallet = Money(5000)

    paid = service.pay_overdue_fee(loan.loan_id, wallet)
    assert paid == Money(4000)
    assert wallet.amount == 1000
    assert loan.is_overdue_fee_paid
    # 지불 후 미납 연체료는 0원이어야 함
    assert loan.get_overdue_fee(service.get_current_date()) == Money(0)


# ==========================================
# 기간 연장 (최대 일주일) 테스트
# ==========================================

def test_loan_extension_success() -> None:
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 1),
    )
    book = service.register_book("1", "도서", "저자")
    loan = service.borrow_book(book.isbn, "학생")
    initial_due = loan.due_date  # 2026-09-08

    # 7일 연장
    service.extend_loan(loan.loan_id, days=7)
    assert loan.due_date == initial_due.add_days(7)  # 2026-09-15
    assert loan.extended_days == 7


def test_loan_extension_limit_exceeded() -> None:
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 1),
    )
    book = service.register_book("1", "도서", "저자")
    loan = service.borrow_book(book.isbn, "학생")

    # 7일 연장 완료
    service.extend_loan(loan.loan_id, days=7)

    # 추가 연장 시도 시 예외 발생 (최대 일주일 제한)
    with pytest.raises(LoanExtensionLimitError):
        service.extend_loan(loan.loan_id, days=1)


def test_overdue_loan_cannot_be_extended() -> None:
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 1),
    )
    book = service.register_book("1", "도서", "저자")
    loan = service.borrow_book(book.isbn, "학생")

    # 이미 연체된 상태로 이동 (9월 10일)
    service.set_current_date(Date(2026, 9, 10))

    # 연체된 도서는 연장 불가
    with pytest.raises(OverdueError):
        service.extend_loan(loan.loan_id, days=7)


def test_advance_day() -> None:
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 15),
    )
    next_day = service.advance_day()
    assert next_day == Date(2026, 9, 16)
    assert service.get_current_date() == Date(2026, 9, 16)
