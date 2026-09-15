from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from .exceptions import (
    BookNotFoundError,
    DuplicateBookError,
    LoanNotFoundError,
)
from .models import Book, BookStatus, Date, Loan, Money
from .repository import LibraryRepository


class LibraryService:
    def __init__(
        self,
        repository: LibraryRepository,
        current_date: Date | None = None,
    ) -> None:
        self.repository = repository
        self._current_date = current_date or Date.today()

    def get_current_date(self) -> Date:
        return self._current_date

    def set_current_date(self, date: Date) -> None:
        self._current_date = date

    def advance_day(self, days: int = 1) -> Date:
        self._current_date = self._current_date.add_days(days)
        return self._current_date

    def register_book(self, isbn: str, title: str, author: str) -> Book:
        if self.repository.find_book(isbn.strip()) is not None:
            raise DuplicateBookError(f"이미 등록된 ISBN입니다: {isbn}")
        book = Book(isbn=isbn, title=title, author=author)
        self.repository.add_book(book)
        return book

    def search_books(self, keyword: str) -> list[Book]:
        normalized = keyword.strip().casefold()
        if not normalized:
            return self.repository.list_books()
        return [
            book
            for book in self.repository.list_books()
            if normalized in book.isbn.casefold()
            or normalized in book.title.casefold()
            or normalized in book.author.casefold()
        ]

    def available_books(self) -> list[Book]:
        return [
            book
            for book in self.repository.list_books()
            if book.status is BookStatus.AVAILABLE
        ]

    def borrow_book(
        self,
        isbn: str,
        borrower: str,
        borrowed_date: Date | None = None,
    ) -> Loan:
        book = self._require_book(isbn)
        borrower = borrower.strip()
        if not borrower:
            raise ValueError("대출자 이름은 비어 있을 수 없습니다.")
        book.borrow()
        b_date = borrowed_date or self._current_date
        loan = Loan(
            loan_id=uuid4().hex[:12],
            book_isbn=book.isbn,
            borrower=borrower,
            borrowed_at=datetime.now(UTC),
            borrowed_date=b_date,
            due_date=b_date.add_days(7),
        )
        self.repository.save_book(book)
        self.repository.add_loan(loan)
        return loan

    def extend_loan(self, loan_id: str, days: int = 7) -> Loan:
        loan = self._require_loan(loan_id)
        loan.extend_period(days=days, current_date=self._current_date)
        self.repository.save_loan(loan)
        return loan

    def pay_overdue_fee(self, loan_id: str, user_money: Money) -> Money:
        loan = self._require_loan(loan_id)
        fee = loan.pay_overdue_fee(user_money, current_date=self._current_date)
        self.repository.save_loan(loan)
        return fee

    def return_book(
        self,
        loan_id: str,
        return_date: Date | None = None,
        auto_pay_with: Money | None = None,
    ) -> Loan:
        loan = self._require_loan(loan_id)
        current = return_date or self._current_date

        # 반납 시 미납 연체료가 있고 자동 결제용 잔액이 전달된 경우 결제 시도
        if auto_pay_with is not None and not loan.is_overdue_fee_paid and loan.is_overdue(current):
            loan.pay_overdue_fee(auto_pay_with, current_date=current)

        book = self._require_book(loan.book_isbn)
        loan.close(returned_at=datetime.now(UTC), returned_date=current)
        book.return_copy()
        self.repository.save_loan(loan)
        self.repository.save_book(book)
        return loan

    def list_loans(self, active_only: bool = False) -> list[Loan]:
        loans = self.repository.list_loans()
        return [loan for loan in loans if loan.is_active] if active_only else loans

    def _require_book(self, isbn: str) -> Book:
        book = self.repository.find_book(isbn.strip())
        if book is None:
            raise BookNotFoundError(f"도서를 찾을 수 없습니다: {isbn}")
        return book

    def _require_loan(self, loan_id: str) -> Loan:
        loan = self.repository.find_loan(loan_id.strip())
        if loan is None:
            raise LoanNotFoundError(f"대출 기록을 찾을 수 없습니다: {loan_id}")
        return loan
