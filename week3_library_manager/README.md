# 3주차 프로젝트: 도서 대출 관리

## 학습 목표

`dataclass`, 합성, 저장소 추상화, 사용자 정의 예외, 타입 힌트와 `pytest`를 하나의 작은 프로그램으로 연결합니다. CLI는 입력만 해석하고, 업무 규칙은 `LibraryService`가 담당합니다.

## 구조

```text
CLI → LibraryService → Book·Loan
                   ↘ Repository → JSON 파일
```

```text
src/library_manager/
├── cli.py          # 명령행 입력과 출력
├── service.py      # 등록·검색·대출·반납 유스케이스
├── models.py       # Book, Loan, BookStatus
├── repository.py   # Protocol, 메모리·JSON 저장소
└── exceptions.py   # 도메인 오류
```

## 실행

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e . pytest
library-manager gui
## 핵심 규칙

- 같은 ISBN은 두 번 등록할 수 없습니다.
- 대출 중인 책은 다시 대출할 수 없습니다.
- 이미 반납된 대출을 다시 반납할 수 없습니다.
- 상태 변경은 `Book.borrow()`, `Book.return_copy()`, `Loan.close()`에서만 수행합니다.
- 서비스는 오류를 숨기지 않고 구체적인 도메인 예외로 알립니다.

## 연체 관리 및 GUI 시스템 (새로운 기능)

### 1. `Date` 및 `Money` 클래스
- **`Date` 클래스**:
  - `year`, `month`, `day`를 다루며, 월은 **1~12월**, 일은 **1~31일** 범위만 지정되도록 제한합니다 (`InvalidDateError`).
  - `next_day()`, `add_days()`, 두 날짜 간 일수 차이 계산(`Date - Date`)을 지원합니다.
- **`Money` 클래스**:
  - 금액을 관리하며 음수 입력을 차단합니다 (`InvalidMoneyError`).
  - 연체료 지불 시 보유 금액이 부족하면 **돈 부족 경고**와 함께 `InsufficientFundsError`가 발생합니다.
  - 덧셈, 뺄셈, 금액 비교 연산자 및 한국어 원화(`2,000원`) 포맷팅을 지원합니다.

### 2. 연체료 및 대여 기간 연장 규칙
- **대여 기간**: 기본 7일 (대출일로부터 7일 뒤 반납 예정).
- **연체 비용**: 연체 기간 **하루 당 2,000원** 부과 (`DAILY_OVERDUE_FEE = 2000`).
- **기간 연장**: 반납 예정일을 **최대 일주일(7일)** 연장 가능 (`LoanExtensionLimitError`, 연체된 도서는 연장 불가).
- **연체료 지불**: 보유 금액으로 연체료를 지불하며, 잔액 부족 시 경고 알림.

  ```
- **UI 주요 구성**:
  - **[⏭ 다음 날 (+1일)]**: 날짜를 하루 넘기며 실시간으로 도서들의 연체 일수와 연체료를 재계산합니다.
  - **[➕ 돈 추가 (+1,000원)]**: 클릭 당 1,000원의 보유 금액을 충전합니다.
  - **[📖 도서 대출]**: 도서를 대출하고 대여일/반납 예정일을 설정합니다.
  - **[📥 도서 반납]**: 연체 도서의 경우 연체료 납부 확인 후 반납 처리합니다 (잔액 부족 시 경고).
  - **[⏳ 기간 연장 (최대 일주일)]**: 대여 기간을 7일 연장합니다.
  - **[💳 연체 비용 지불]**: 연체료를 지불합니다 (보유 잔액이 부족하면 경고창 표시).

