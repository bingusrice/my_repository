"""도서 대출 관리 시스템 GUI 실행 진입점."""
from __future__ import annotations

import sys
from pathlib import Path

# src 디렉터리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from library_manager.gui import main

if __name__ == "__main__":
    main()
