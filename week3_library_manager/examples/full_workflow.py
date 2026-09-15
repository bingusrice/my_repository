from __future__ import annotations

import sys

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from library_manager.exceptions import (
    BookUnavailableError,
    InsufficientFundsError,
    LoanExtensionLimitError,
    OverdueError,
)
from library_manager.models import Date, Money
from library_manager.repository import InMemoryLibraryRepository
from library_manager.service import LibraryService


def main() -> None:
    # 1. 서비스 초기화 (시작일: 2026-09-01)
    service = LibraryService(
        InMemoryLibraryRepository(),
        current_date=Date(2026, 9, 1),
    )
    print("=== [1] 서비스 시작 ===")
    print(f"현재 시스템 날짜: {service.get_current_date()}")

    # 2. 도서 등록
    first = service.register_book(
        "9788966260959",
        "파이썬 코딩의 기술",
        "브렛 슬라킨",
    )
    second = service.register_book(
        "9781492056355",
        "Fluent Python",
        "Luciano Ramalho",
    )
    print(f"도서 등록: {first.title} ({first.status.value})")
    print(f"도서 등록: {second.title} ({second.status.value})")

    # 3. 도서 대출 (대여 기간 기본 7일: 2026-09-01 ~ 2026-09-08)
    loan = service.borrow_book(first.isbn, "student01")
    print(f"\n=== [2] 도서 대출 ===")
    print(f"대출 번호: {loan.loan_id}")
    print(f"대출일: {loan.borrowed_date}, 반납 예정일: {loan.due_date}")

    # 4. 기간 연장 시연 (최대 일주일)
    print(f"\n=== [3] 대여 기간 연장 ===")
    service.extend_loan(loan.loan_id, days=7)
    print(f"7일 연장 완료 -> 새 반납 예정일: {loan.due_date}")

    try:
        service.extend_loan(loan.loan_id, days=1)
    except LoanExtensionLimitError as exc:
        print(f"예상된 한도 초과 오류: {exc}")

    # 5. 날짜 경과 시뮬레이션 (연체 발생)
    print(f"\n=== [4] 날짜 경과 및 연체 발생 ===")
    service.set_current_date(Date(2026, 9, 18))  # 반납 예정일(9월 15일)로부터 3일 경과
    current_date = service.get_current_date()
    overdue_days = loan.get_overdue_days(current_date)
    overdue_fee = loan.get_overdue_fee(current_date)
    print(f"현재 날짜: {current_date}")
    print(f"연체 일수: {overdue_days}일 (하루당 2,000원)")
    print(f"계산된 연체료: {overdue_fee}")

    # 6. 연체된 상태에서 기간 연장 시도 -> 거부됨
    try:
        service.extend_loan(loan.loan_id, days=1)
    except OverdueError as exc:
        print(f"예상된 연체 도서 연장 거부: {exc}")

    # 7. Money 클래스를 통한 연체 비용 지불 및 잔액 부족 경고
    print(f"\n=== [5] 연체 비용 지불 및 잔액 부족 시스템 ===")
    wallet = Money(0)
    print(f"사용자 초기 잔액: {wallet}")

    # 클릭 당 1000원 추가 (3회 클릭 = 3000원)
    wallet.add(1000).add(1000).add(1000)
    print(f"돈 추가 3회 (+3,000원) -> 현재 잔액: {wallet}")

    # 잔액 부족 상태에서 결제 시도
    try:
        service.pay_overdue_fee(loan.loan_id, wallet)
    except InsufficientFundsError as exc:
        print(f"⚠️ 경고 (잔액 부족): {exc}")

    # 추가 충전 (+4,000원 -> 총 7,000원 보유)
    wallet.add(1000).add(1000).add(1000).add(1000)
    print(f"\n추가 충전 4회 (+4,000원) -> 현재 잔액: {wallet}")

    # 정상 결제
    paid = service.pay_overdue_fee(loan.loan_id, wallet)
    print(f"✅ 연체료 결제 성공: {paid} 차감됨, 남은 잔액: {wallet}")

    # 8. 반납 완료
    print(f"\n=== [6] 도서 반납 ===")
    service.return_book(loan.loan_id)
    print(f"도서 반납 후 상태: {first.status.value}")
    print(f"활성 대출 수: {len(service.list_loans(active_only=True))}")


if __name__ == "__main__":
    main()
