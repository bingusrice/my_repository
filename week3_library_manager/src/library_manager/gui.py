from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .exceptions import (
    InsufficientFundsError,
    InvalidDateError,
    InvalidMoneyError,
    LibraryError,
    LoanExtensionLimitError,
    OverdueError,
)
from .models import DAILY_OVERDUE_FEE, Date, Money
from .repository import JsonLibraryRepository
from .service import LibraryService


class LibraryApp(tk.Tk):
    """도서 대출 관리 시스템 GUI 애플리케이션."""

    def __init__(self, db_path: str = "data/library.json") -> None:
        super().__init__()
        self.title("도서 대출 관리 시스템 (Library Manager)")
        self.geometry("1040x720")
        self.minsize(880, 600)

        self.db_path = Path(db_path)
        self.repository = JsonLibraryRepository(self.db_path)
        self.service = LibraryService(self.repository)

        # 사용자 지갑 (Money 클래스)
        self.user_money = Money(0)

        self._setup_styles()
        self._build_ui()
        self._refresh_all()

        self._log(f"시스템 시작됨. 현재 날짜: {self.service.get_current_date()}, 보유 금액: {self.user_money}")

    def _setup_styles(self) -> None:
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # 색상 및 폰트 설정
        self.style.configure("Header.TFrame", background="#f0f4f8")
        self.style.configure("Card.TFrame", background="#ffffff", relief="ridge")
        self.style.configure("Action.TButton", font=("Malgun Gothic", 10, "bold"), padding=6)
        self.style.configure("Money.TButton", font=("Malgun Gothic", 10, "bold"), foreground="#0d6efd", padding=6)
        self.style.configure("Date.TButton", font=("Malgun Gothic", 10, "bold"), foreground="#198754", padding=6)
        self.style.configure("Danger.TButton", font=("Malgun Gothic", 10, "bold"), foreground="#dc3545", padding=6)

        self.style.configure("Treeview.Heading", font=("Malgun Gothic", 10, "bold"))
        self.style.configure("Treeview", font=("Malgun Gothic", 9), rowheight=26)

    def _build_ui(self) -> None:
        # 상단 대시보드 (날짜, 다음 날 버튼, 보유 금액, 돈 추가 버튼)
        top_frame = ttk.Frame(self, padding=12, style="Header.TFrame")
        top_frame.pack(fill="x", side="top")

        # 날짜 영역
        date_box = ttk.LabelFrame(top_frame, text=" 📅 현재 시스템 날짜 ", padding=10)
        date_box.pack(side="left", fill="both", expand=True, padx=6)

        self.lbl_current_date = ttk.Label(
            date_box,
            text="",
            font=("Malgun Gothic", 13, "bold"),
            foreground="#0f5132",
        )
        self.lbl_current_date.pack(side="left", padx=8)

        btn_next_day = ttk.Button(
            date_box,
            text="⏭ 다음 날 (+1일)",
            style="Date.TButton",
            command=self._on_next_day,
        )
        btn_next_day.pack(side="right", padx=6)

        btn_set_date = ttk.Button(
            date_box,
            text="⚙ 날짜 지정",
            command=self._on_set_date_dialog,
        )
        btn_set_date.pack(side="right", padx=4)

        # 보유 금액 영역
        money_box = ttk.LabelFrame(top_frame, text=" 💰 사용자 보유 금액 ", padding=10)
        money_box.pack(side="right", fill="both", expand=True, padx=6)

        self.lbl_money = ttk.Label(
            money_box,
            text="",
            font=("Malgun Gothic", 13, "bold"),
            foreground="#084298",
        )
        self.lbl_money.pack(side="left", padx=8)

        btn_add_money = ttk.Button(
            money_box,
            text="➕ 돈 추가 (+1,000원)",
            style="Money.TButton",
            command=self._on_add_money,
        )
        btn_add_money.pack(side="right", padx=6)

        # 액션 툴바 (대여, 반납, 연장, 연체료 지불)
        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(fill="x", side="top")

        btn_borrow = ttk.Button(
            toolbar,
            text="📖 도서 대출",
            style="Action.TButton",
            command=self._on_borrow_dialog,
        )
        btn_borrow.pack(side="left", padx=5)

        btn_return = ttk.Button(
            toolbar,
            text="📥 도서 반납",
            style="Action.TButton",
            command=self._on_return_loan,
        )
        btn_return.pack(side="left", padx=5)

        btn_extend = ttk.Button(
            toolbar,
            text="⏳ 기간 연장 (최대 일주일)",
            style="Action.TButton",
            command=self._on_extend_loan,
        )
        btn_extend.pack(side="left", padx=5)

        btn_pay_fee = ttk.Button(
            toolbar,
            text="💳 연체 비용 지불",
            style="Danger.TButton",
            command=self._on_pay_overdue_fee,
        )
        btn_pay_fee.pack(side="left", padx=5)

        btn_refresh = ttk.Button(
            toolbar,
            text="🔄 새로고침",
            command=self._refresh_all,
        )
        btn_refresh.pack(side="right", padx=5)

        # 탭 뷰 (대출 관리 & 도서 관리)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_loans = ttk.Frame(notebook, padding=8)
        self.tab_books = ttk.Frame(notebook, padding=8)

        notebook.add(self.tab_loans, text="  📋 대출 현황 및 연체 관리  ")
        notebook.add(self.tab_books, text="  📚 도서 목록 및 등록  ")

        self._build_loans_tab()
        self._build_books_tab()

        # 하단 로그/알림 패널
        bottom_frame = ttk.LabelFrame(self, text=" 📜 실시간 활동 로그 / 알림 ", padding=6)
        bottom_frame.pack(fill="x", side="bottom", padx=10, pady=6)

        self.txt_log = tk.Text(bottom_frame, height=4, font=("Consolas", 9), wrap="word", state="disabled")
        self.txt_log.pack(fill="x", expand=True)

    def _build_loans_tab(self) -> None:
        # 필터 프레임
        filter_bar = ttk.Frame(self.tab_loans)
        filter_bar.pack(fill="x", pady=(0, 6))

        self.loan_filter_var = tk.StringVar(value="active")
        ttk.Radiobutton(
            filter_bar,
            text="대출 중만 보기",
            variable=self.loan_filter_var,
            value="active",
            command=self._refresh_loans_table,
        ).pack(side="left", padx=6)

        ttk.Radiobutton(
            filter_bar,
            text="연체된 도서만 보기",
            variable=self.loan_filter_var,
            value="overdue",
            command=self._refresh_loans_table,
        ).pack(side="left", padx=6)

        ttk.Radiobutton(
            filter_bar,
            text="전체 기록 보기",
            variable=self.loan_filter_var,
            value="all",
            command=self._refresh_loans_table,
        ).pack(side="left", padx=6)

        info_lbl = ttk.Label(
            filter_bar,
            text=f"※ 연체료 기준: 1일당 {DAILY_OVERDUE_FEE:,}원 | 연장 한도: 최대 7일",
            foreground="#666666",
            font=("Malgun Gothic", 9),
        )
        info_lbl.pack(side="right", padx=6)

        # 대출 목록 테이블
        columns = (
            "loan_id",
            "book_title",
            "borrower",
            "borrowed_date",
            "due_date",
            "status",
            "overdue_fee",
            "extended",
            "returned_date",
        )
        self.tree_loans = ttk.Treeview(self.tab_loans, columns=columns, show="headings", selectmode="browse")

        self.tree_loans.heading("loan_id", text="대출 번호")
        self.tree_loans.heading("book_title", text="도서명 (ISBN)")
        self.tree_loans.heading("borrower", text="대출자")
        self.tree_loans.heading("borrowed_date", text="대출일")
        self.tree_loans.heading("due_date", text="반납 예정일")
        self.tree_loans.heading("status", text="대출 상태 / 연체 현황")
        self.tree_loans.heading("overdue_fee", text="미납 연체료")
        self.tree_loans.heading("extended", text="기간 연장")
        self.tree_loans.heading("returned_date", text="반납일")

        self.tree_loans.column("loan_id", width=100, anchor="center")
        self.tree_loans.column("book_title", width=220, anchor="w")
        self.tree_loans.column("borrower", width=90, anchor="center")
        self.tree_loans.column("borrowed_date", width=95, anchor="center")
        self.tree_loans.column("due_date", width=95, anchor="center")
        self.tree_loans.column("status", width=140, anchor="center")
        self.tree_loans.column("overdue_fee", width=95, anchor="e")
        self.tree_loans.column("extended", width=85, anchor="center")
        self.tree_loans.column("returned_date", width=95, anchor="center")

        loan_scroll = ttk.Scrollbar(self.tab_loans, orient="vertical", command=self.tree_loans.yview)
        self.tree_loans.configure(yscrollcommand=loan_scroll.set)

        self.tree_loans.pack(side="left", fill="both", expand=True)
        loan_scroll.pack(side="right", fill="y")

        # 테이블 태그 색상 설정
        self.tree_loans.tag_configure("overdue", foreground="#dc3545", background="#fff5f5")
        self.tree_loans.tag_configure("normal", foreground="#198754")
        self.tree_loans.tag_configure("returned", foreground="#6c757d")

    def _build_books_tab(self) -> None:
        # 좌측 도서 등록 패널
        left_panel = ttk.LabelFrame(self.tab_books, text=" ➕ 새 도서 등록 ", padding=10)
        left_panel.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(left_panel, text="ISBN:").pack(anchor="w", pady=(2, 0))
        self.ent_isbn = ttk.Entry(left_panel, width=24)
        self.ent_isbn.pack(fill="x", pady=(0, 8))

        ttk.Label(left_panel, text="도서 제목:").pack(anchor="w", pady=(2, 0))
        self.ent_title = ttk.Entry(left_panel, width=24)
        self.ent_title.pack(fill="x", pady=(0, 8))

        ttk.Label(left_panel, text="저자:").pack(anchor="w", pady=(2, 0))
        self.ent_author = ttk.Entry(left_panel, width=24)
        self.ent_author.pack(fill="x", pady=(0, 12))

        btn_register = ttk.Button(
            left_panel,
            text="도서 등록",
            style="Action.TButton",
            command=self._on_register_book,
        )
        btn_register.pack(fill="x", pady=4)

        # 우측 도서 목록 패널
        right_panel = ttk.Frame(self.tab_books)
        right_panel.pack(side="right", fill="both", expand=True)

        # 검색 바
        search_bar = ttk.Frame(right_panel)
        search_bar.pack(fill="x", pady=(0, 6))

        ttk.Label(search_bar, text="검색어:").pack(side="left", padx=(0, 6))
        self.ent_search = ttk.Entry(search_bar, width=30)
        self.ent_search.pack(side="left", padx=(0, 6))
        self.ent_search.bind("<KeyRelease>", lambda e: self._refresh_books_table())

        btn_search = ttk.Button(search_bar, text="검색", command=self._refresh_books_table)
        btn_search.pack(side="left", padx=4)

        btn_borrow_selected = ttk.Button(
            search_bar,
            text="선택 도서 대출",
            style="Action.TButton",
            command=self._on_borrow_selected_book,
        )
        btn_borrow_selected.pack(side="right", padx=4)

        # 도서 테이블
        columns = ("isbn", "title", "author", "status")
        self.tree_books = ttk.Treeview(right_panel, columns=columns, show="headings", selectmode="browse")

        self.tree_books.heading("isbn", text="ISBN")
        self.tree_books.heading("title", text="제목")
        self.tree_books.heading("author", text="저자")
        self.tree_books.heading("status", text="대출 상태")

        self.tree_books.column("isbn", width=140, anchor="center")
        self.tree_books.column("title", width=260, anchor="w")
        self.tree_books.column("author", width=140, anchor="w")
        self.tree_books.column("status", width=100, anchor="center")

        book_scroll = ttk.Scrollbar(right_panel, orient="vertical", command=self.tree_books.yview)
        self.tree_books.configure(yscrollcommand=book_scroll.set)

        self.tree_books.pack(side="left", fill="both", expand=True)
        book_scroll.pack(side="right", fill="y")

    # =========================================================================
    # UI 갱신 및 로깅 메서드
    # =========================================================================

    def _log(self, message: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"[{self.service.get_current_date()}] {message}\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _refresh_all(self) -> None:
        # 상단 날짜 및 금액 표시 갱신
        self.lbl_current_date.configure(text=f"{self.service.get_current_date()}")
        self.lbl_money.configure(text=f"{self.user_money}")

        self._refresh_loans_table()
        self._refresh_books_table()

    def _refresh_loans_table(self) -> None:
        self.tree_loans.delete(*self.tree_loans.get_children())
        current_date = self.service.get_current_date()
        filter_mode = self.loan_filter_var.get()

        loans = self.service.list_loans(active_only=False)

        for loan in loans:
            if filter_mode == "active" and not loan.is_active:
                continue
            if filter_mode == "overdue" and (not loan.is_active or not loan.is_overdue(current_date)):
                continue

            book = self.repository.find_book(loan.book_isbn)
            title_display = f"{book.title} ({loan.book_isbn})" if book else loan.book_isbn

            borrowed_str = str(loan.borrowed_date) if loan.borrowed_date else "-"
            due_str = str(loan.due_date) if loan.due_date else "-"
            returned_str = str(loan.returned_date) if loan.returned_date else ("대출 중" if loan.is_active else "-")

            tag = "normal"
            if not loan.is_active:
                tag = "returned"
                status_text = "반납 완료"
                overdue_fee_text = f"{loan.paid_fee:,}원 납부됨" if loan.paid_fee > 0 else "-"
            else:
                overdue_days = loan.get_overdue_days(current_date)
                if overdue_days > 0:
                    tag = "overdue"
                    status_text = f"🔴 {overdue_days}일 연체!"
                    fee = loan.get_overdue_fee(current_date)
                    if loan.is_overdue_fee_paid:
                        overdue_fee_text = "✅ 지불 완료"
                    else:
                        overdue_fee_text = f"{fee}"
                else:
                    days_left = (loan.due_date - current_date) if loan.due_date else 0
                    status_text = f"🟢 정상 (D-{days_left})"
                    overdue_fee_text = "0원"

            extended_text = f"+{loan.extended_days}일 연장" if loan.extended_days > 0 else "미연장"

            self.tree_loans.insert(
                "",
                "end",
                iid=loan.loan_id,
                values=(
                    loan.loan_id,
                    title_display,
                    loan.borrower,
                    borrowed_str,
                    due_str,
                    status_text,
                    overdue_fee_text,
                    extended_text,
                    returned_str,
                ),
                tags=(tag,),
            )

    def _refresh_books_table(self) -> None:
        self.tree_books.delete(*self.tree_books.get_children())
        query = self.ent_search.get().strip()
        books = self.service.search_books(query) if query else self.repository.list_books()

        for book in books:
            status_text = "대출 가능" if book.status.value == "available" else "대출 중"
            self.tree_books.insert(
                "",
                "end",
                iid=book.isbn,
                values=(
                    book.isbn,
                    book.title,
                    book.author,
                    status_text,
                ),
            )

    # =========================================================================
    # 이벤트 핸들러 (요구사항 구현)
    # =========================================================================

    def _on_next_day(self) -> None:
        """날짜를 하루 넘기는 다음 날 버튼 (+1일)."""
        old_date = self.service.get_current_date()
        new_date = self.service.advance_day(1)
        self._refresh_all()

        # 새로 연체된 도서가 있는지 검사
        overdue_count = sum(
            1 for loan in self.service.list_loans(active_only=True)
            if loan.is_overdue(new_date) and not loan.is_overdue_fee_paid
        )
        msg = f"날짜가 하루 경과되었습니다: {old_date} -> {new_date}"
        if overdue_count > 0:
            msg += f" (현재 미납 연체 도서: {overdue_count}건)"
        self._log(msg)

    def _on_set_date_dialog(self) -> None:
        """date 클래스의 범위 제한(1~12월, 1~31일)을 시험하고 날짜를 지정하는 다이얼로그."""
        curr = self.service.get_current_date()
        date_str = simpledialog.askstring(
            "날짜 직접 지정",
            f"새로운 날짜를 입력하세요 (YYYY-MM-DD)\n* 월은 1~12월, 일은 1~31일 범위 내여야 합니다.\n현재: {curr}",
            parent=self,
        )
        if not date_str:
            return

        try:
            new_date = Date.from_isoformat(date_str.strip())
            self.service.set_current_date(new_date)
            self._refresh_all()
            self._log(f"시스템 날짜가 {new_date}로 변경되었습니다.")
            messagebox.showinfo("날짜 변경 완료", f"현재 시스템 날짜가 {new_date}로 설정되었습니다.")
        except InvalidDateError as exc:
            messagebox.showerror("날짜 오류", f"유효하지 않은 날짜입니다!\n{exc}")
        except Exception as exc:
            messagebox.showerror("입력 오류", f"날짜 형식이 올바르지 않습니다: {exc}")

    def _on_add_money(self) -> None:
        """돈 추가 (클릭 당 1000원)."""
        self.user_money.add(1000)
        self.lbl_money.configure(text=f"{self.user_money}")
        self._log(f"돈 1,000원이 충전되었습니다. (현재 보유: {self.user_money})")

    def _on_register_book(self) -> None:
        isbn = self.ent_isbn.get().strip()
        title = self.ent_title.get().strip()
        author = self.ent_author.get().strip()

        if not isbn or not title or not author:
            messagebox.showwarning("입력 필요", "ISBN, 도서 제목, 저자를 모두 입력해주세요.")
            return

        try:
            book = self.service.register_book(isbn, title, author)
            self._refresh_books_table()
            self.ent_isbn.delete(0, "end")
            self.ent_title.delete(0, "end")
            self.ent_author.delete(0, "end")
            self._log(f"새 도서 등록 완료: {book.title} ({book.isbn})")
            messagebox.showinfo("등록 성공", f"'{book.title}' 도서가 성공적으로 등록되었습니다.")
        except LibraryError as exc:
            messagebox.showerror("도서 등록 실패", str(exc))

    def _on_borrow_selected_book(self) -> None:
        selected = self.tree_books.selection()
        if not selected:
            messagebox.showinfo("안내", "대출할 도서를 목록에서 먼저 선택해주세요.")
            return
        isbn = selected[0]
        self._borrow_flow(isbn)

    def _on_borrow_dialog(self) -> None:
        # 사용 가능한 도서 목록 팝업 또는 ISBN 입력
        selected = self.tree_books.selection()
        isbn_preset = selected[0] if selected else ""

        isbn = simpledialog.askstring("도서 대출", "대출할 도서의 ISBN을 입력하세요:", initialvalue=isbn_preset, parent=self)
        if not isbn:
            return
        self._borrow_flow(isbn.strip())

    def _borrow_flow(self, isbn: str) -> None:
        borrower = simpledialog.askstring("도서 대출", "대출자 이름을 입력하세요:", initialvalue="student01", parent=self)
        if not borrower:
            return

        try:
            loan = self.service.borrow_book(isbn, borrower.strip())
            self._refresh_all()
            book = self.repository.find_book(isbn)
            title = book.title if book else isbn
            self._log(f"도서 대출: '{title}' -> {borrower} (반납 예정일: {loan.due_date})")
            messagebox.showinfo(
                "대출 완료",
                f"대출이 완료되었습니다!\n\n도서: {title}\n대출자: {borrower}\n대출일: {loan.borrowed_date}\n반납 예정일: {loan.due_date} (대여 기간 7일)",
            )
        except LibraryError as exc:
            messagebox.showerror("대출 실패", str(exc))
        except ValueError as exc:
            messagebox.showwarning("입력 오류", str(exc))

    def _on_extend_loan(self) -> None:
        """대여 기간 연장 (최대 일주일)."""
        selected = self.tree_loans.selection()
        if not selected:
            messagebox.showinfo("안내", "대여 기간을 연장할 대출 항목을 선택해주세요.")
            return

        loan_id = selected[0]
        loan = self.repository.find_loan(loan_id)
        if not loan:
            messagebox.showerror("오류", "대출 정보를 찾을 수 없습니다.")
            return

        if not loan.is_active:
            messagebox.showwarning("연장 불가", "이미 반납 완료된 도서는 기간을 연장할 수 없습니다.")
            return

        current_date = self.service.get_current_date()
        if loan.is_overdue(current_date):
            messagebox.showwarning(
                "연장 불가 (연체 상태)",
                "⚠️ 연체된 도서는 기간을 연장할 수 없습니다!\n연체료를 지불하고 도서를 반납해주세요.",
            )
            return

        if loan.extended_days >= 7:
            messagebox.showwarning(
                "연장 한도 초과",
                f"⚠️ 대여 기간 연장은 최대 일주일(7일)까지만 가능합니다.\n(이미 {loan.extended_days}일 연장되었습니다)",
            )
            return

        # 연장 실행 (7일)
        try:
            self.service.extend_loan(loan_id, days=7)
            self._refresh_all()
            self._log(f"기간 연장 완료: 대출번호 {loan_id} (새 반납 예정일: {loan.due_date})")
            messagebox.showinfo(
                "기간 연장 완료",
                f"✅ 대여 기간이 일주일(7일) 연장되었습니다!\n새로운 반납 예정일: {loan.due_date}",
            )
        except (LoanExtensionLimitError, OverdueError, LibraryError) as exc:
            messagebox.showerror("연장 실패", str(exc))

    def _on_pay_overdue_fee(self) -> None:
        """연체 비용 지불 버튼 및 돈 부족 경고 시스템."""
        selected = self.tree_loans.selection()
        if not selected:
            messagebox.showinfo("안내", "연체료를 지불할 대출 항목을 선택해주세요.")
            return

        loan_id = selected[0]
        loan = self.repository.find_loan(loan_id)
        if not loan:
            messagebox.showerror("오류", "대출 정보를 찾을 수 없습니다.")
            return

        current_date = self.service.get_current_date()
        overdue_fee = loan.get_overdue_fee(current_date)

        if not loan.is_overdue(current_date):
            messagebox.showinfo("연체 없음", "해당 도서는 연체되지 않았습니다. 연체료가 0원입니다.")
            return

        if loan.is_overdue_fee_paid or overdue_fee.amount == 0:
            messagebox.showinfo("지불 완료", "해당 대출의 연체료는 이미 지불 완료되었습니다.")
            return

        overdue_days = loan.get_overdue_days(current_date)

        # 돈이 부족한지 사전 확인 및 경고 시스템
        if not self.user_money.can_afford(overdue_fee):
            shortage = overdue_fee.amount - self.user_money.amount
            self._log(
                f"⚠️ [돈 부족 경고] 연체료 {overdue_fee} 결제 실패 (보유: {self.user_money}, 부족: {shortage:,}원)"
            )
            messagebox.showwarning(
                "⚠️ 돈 부족 경고",
                f"연체 비용을 지불하기에 보유 금액이 부족합니다!\n\n"
                f"• 연체 일수: {overdue_days}일 (하루당 {DAILY_OVERDUE_FEE:,}원)\n"
                f"• 지불할 연체료: {overdue_fee}\n"
                f"• 현재 보유 금액: {self.user_money}\n"
                f"• 부족한 금액: {shortage:,}원\n\n"
                f"상단의 '➕ 돈 추가 (+1,000원)' 버튼을 눌러 금액을 충전한 후 다시 시도해주세요.",
            )
            return

        # 결제 확인 질문
        confirm = messagebox.askyesno(
            "연체료 지불 확인",
            f"연체료를 지불하시겠습니까?\n\n"
            f"• 연체 일수: {overdue_days}일\n"
            f"• 총 연체료: {overdue_fee}\n"
            f"• 현재 보유 금액: {self.user_money}\n"
            f"• 결제 후 남은 잔액: {self.user_money.amount - overdue_fee.amount:,}원",
        )
        if not confirm:
            return

        try:
            paid = self.service.pay_overdue_fee(loan_id, self.user_money)
            self._refresh_all()
            self._log(f"✅ 연체료 결제 완료: {paid} 지불됨 (남은 잔액: {self.user_money})")
            messagebox.showinfo(
                "결제 완료",
                f"✅ 연체료 {paid}가 성공적으로 결제되었습니다!\n\n남은 보유 금액: {self.user_money}",
            )
        except InsufficientFundsError as exc:
            messagebox.showwarning("⚠️ 돈 부족 경고", str(exc))
        except LibraryError as exc:
            messagebox.showerror("결제 실패", str(exc))

    def _on_return_loan(self) -> None:
        """도서 반납 처리 (연체 시 연체료 지불 여부 검증 및 돈 부족 경고)."""
        selected = self.tree_loans.selection()
        if not selected:
            messagebox.showinfo("안내", "반납할 대출 항목을 선택해주세요.")
            return

        loan_id = selected[0]
        loan = self.repository.find_loan(loan_id)
        if not loan:
            messagebox.showerror("오류", "대출 정보를 찾을 수 없습니다.")
            return

        if not loan.is_active:
            messagebox.showinfo("안내", "이미 반납 처리된 대출입니다.")
            return

        current_date = self.service.get_current_date()
        overdue_fee = loan.get_overdue_fee(current_date)
        overdue_days = loan.get_overdue_days(current_date)

        # 연체된 상태이고 아직 연체료를 안 낸 경우
        if overdue_fee.amount > 0 and not loan.is_overdue_fee_paid:
            # 돈이 부족한지 검증
            if not self.user_money.can_afford(overdue_fee):
                shortage = overdue_fee.amount - self.user_money.amount
                self._log(f"⚠️ [반납 불가] 연체료 미납 & 돈 부족: {shortage:,}원 부족")
                messagebox.showwarning(
                    "⚠️ 돈 부족 경고 (반납 불가)",
                    f"이 도서는 {overdue_days}일 연체되었습니다!\n"
                    f"반납하기 위해 연체료({overdue_fee})를 정산해야 하지만 보유 금액이 부족합니다.\n\n"
                    f"• 필요 연체료: {overdue_fee}\n"
                    f"• 현재 보유 금액: {self.user_money}\n"
                    f"• 부족한 금액: {shortage:,}원\n\n"
                    f"상단의 '➕ 돈 추가 (+1,000원)' 버튼을 눌러 충전 후 반납해주세요.",
                )
                return

            pay_now = messagebox.askyesno(
                "연체료 결제 및 반납",
                f"이 도서는 {overdue_days}일 연체되었습니다.\n"
                f"반납 시 연체료 {overdue_fee}가 보유 금액에서 차감됩니다.\n\n"
                f"현재 보유 금액: {self.user_money}\n"
                f"결제 후 잔액: {self.user_money.amount - overdue_fee.amount:,}원\n\n"
                f"연체료를 결제하고 도서를 반납하시겠습니까?",
            )
            if not pay_now:
                return

            # 연체료 결제와 함께 반납
            try:
                self.service.return_book(loan_id, return_date=current_date, auto_pay_with=self.user_money)
                self._refresh_all()
                self._log(f"도서 반납 완료 (연체료 {overdue_fee} 정산됨, 잔액: {self.user_money})")
                messagebox.showinfo(
                    "반납 완료",
                    f"✅ 연체료 {overdue_fee}가 정산되고 도서가 정상 반납되었습니다.\n남은 보유 금액: {self.user_money}",
                )
            except InsufficientFundsError as exc:
                messagebox.showwarning("⚠️ 돈 부족 경고", str(exc))
            except LibraryError as exc:
                messagebox.showerror("반납 실패", str(exc))
            return

        # 연체되지 않았거나 이미 연체료가 납부된 경우
        confirm = messagebox.askyesno("반납 확인", "선택한 도서를 반납하시겠습니까?")
        if not confirm:
            return

        try:
            self.service.return_book(loan_id, return_date=current_date)
            self._refresh_all()
            self._log(f"도서 반납 완료: 대출번호 {loan_id}")
            messagebox.showinfo("반납 완료", "✅ 도서가 성공적으로 반납되었습니다.")
        except LibraryError as exc:
            messagebox.showerror("반납 실패", str(exc))


def main() -> None:
    app = LibraryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
