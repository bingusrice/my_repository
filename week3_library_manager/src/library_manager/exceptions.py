class LibraryError(Exception):
    """Base class for expected domain errors."""


class InvalidBookError(LibraryError):
    pass


class DuplicateBookError(LibraryError):
    pass


class BookNotFoundError(LibraryError):
    pass


class BookUnavailableError(LibraryError):
    pass


class LoanNotFoundError(LibraryError):
    pass


class AlreadyReturnedError(LibraryError):
    pass


class InvalidDateError(LibraryError, ValueError):
    """날짜 범위(1~12월, 1~31일) 또는 형식이 유효하지 않을 때 발생하는 오류."""
    pass


class InvalidMoneyError(LibraryError, ValueError):
    """금액이 유효하지 않을 때(음수 등) 발생하는 오류."""
    pass


class InsufficientFundsError(LibraryError):
    """연체료 지불 시 보유 금액이 부족할 때 발생하는 오류."""
    pass


class LoanExtensionLimitError(LibraryError):
    """대여 기간 연장 한도(최대 일주일)를 초과했을 때 발생하는 오류."""
    pass


class OverdueError(LibraryError):
    """도서 연체 관련 처리 오류."""
    pass

