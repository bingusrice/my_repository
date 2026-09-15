from __future__ import annotations

import argparse
from collections.abc import Sequence

from .exceptions import LibraryError
from .models import Book, Date, Loan, Money
from .repository import JsonLibraryRepository
from .service import LibraryService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="도서 대출 관리")
    parser.add_argument("--db", default="data/library.json", help="JSON 저장 파일")
    commands = parser.add_subparsers(dest="command", required=True)

    register = commands.add_parser("register", help="도서 등록")
    register.add_argument("isbn")
    register.add_argument("title")
    register.add_argument("author")

    search = commands.add_parser("search", help="도서 검색")
    search.add_argument("keyword")
    commands.add_parser("available", help="대출 가능 목록")

    borrow = commands.add_parser("borrow", help="도서 대출")
    borrow.add_argument("isbn")
    borrow.add_argument("borrower")

    return_command = commands.add_parser("return", help="도서 반납")
    return_command.add_argument("loan_id")

    extend_command = commands.add_parser("extend", help="도서 대여 기간 연장 (최대 7일)")
    extend_command.add_argument("loan_id")
    extend_command.add_argument("--days", type=int, default=7, help="연장할 일수 (기본 7일)")

    pay_command = commands.add_parser("pay-overdue", help="연체 비용 지불")
    pay_command.add_argument("loan_id")
    pay_command.add_argument("--amount", type=int, required=True, help="지불할 보유 금액(원)")

    loans = commands.add_parser("loans", help="대출 기록")
    loans.add_argument("--active", action="store_true")

    commands.add_parser("gui", help="GUI 그래픽 인터페이스 실행")
    return parser


def _book_line(book: Book) -> str:
    return f"{book.isbn} | {book.title} | {book.author} | {book.status.value}"


def _loan_line(loan: Loan, current_date: Date | None = None) -> str:
    returned = loan.returned_at.isoformat(timespec="seconds") if loan.returned_at else "대출 중"
    base = f"{loan.loan_id} | {loan.book_isbn} | {loan.borrower} | {returned}"
    extras: list[str] = []
    if loan.due_date:
        extras.append(f"반납예정: {loan.due_date}")
    if current_date and loan.is_active and loan.is_overdue(current_date):
        fee = loan.get_overdue_fee(current_date)
        extras.append(f"연체 {loan.get_overdue_days(current_date)}일 (연체료: {fee})")
    if loan.extended_days > 0:
        extras.append(f"연장됨: +{loan.extended_days}일")
    if extras:
        return f"{base} | {' | '.join(extras)}"
    return base


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "gui":
        from .gui import LibraryApp
        app = LibraryApp(args.db)
        app.mainloop()
        return 0

    service = LibraryService(JsonLibraryRepository(args.db))
    current_date = service.get_current_date()
    try:
        if args.command == "register":
            print(_book_line(service.register_book(args.isbn, args.title, args.author)))
        elif args.command == "search":
            for book in service.search_books(args.keyword):
                print(_book_line(book))
        elif args.command == "available":
            for book in service.available_books():
                print(_book_line(book))
        elif args.command == "borrow":
            print(_loan_line(service.borrow_book(args.isbn, args.borrower), current_date))
        elif args.command == "return":
            print(_loan_line(service.return_book(args.loan_id), current_date))
        elif args.command == "extend":
            loan = service.extend_loan(args.loan_id, days=args.days)
            print(f"기간 연장 완료: {loan.loan_id} | 새 반납예정일: {loan.due_date} (+{loan.extended_days}일 연장)")
        elif args.command == "pay-overdue":
            wallet = Money(args.amount)
            paid = service.pay_overdue_fee(args.loan_id, wallet)
            print(f"연체료 지불 완료: {paid} 지불됨. (남은 금액: {wallet})")
        elif args.command == "loans":
            for loan in service.list_loans(active_only=args.active):
                print(_loan_line(loan, current_date))
    except (LibraryError, ValueError) as exc:
        print(f"오류: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
