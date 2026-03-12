import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple


_LINE_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (?P<logger>.*?) - \[(?P<level>[A-Z]+)\] - (?P<msg>.*)$")
_FILE_RE = re.compile(r"^fire_detection_(\d{4}-\d{2}-\d{2})\.log$")


@dataclass
class _ParsedEntry:
    ts: datetime
    level: str
    logger: str
    message: str


class LogService:
    def __init__(self, log_dir: Path, retention_days: int = 7):
        self.log_dir = log_dir
        self.retention_days = retention_days

    def ensure_dir(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> int:
        self.ensure_dir()
        keep_days = int(self.retention_days) if self.retention_days else 7
        if keep_days <= 0:
            return 0

        cutoff_date = (datetime.now().date() - timedelta(days=keep_days))
        removed = 0

        for p in self.log_dir.iterdir():
            if not p.is_file():
                continue
            m = _FILE_RE.match(p.name)
            if not m:
                continue
            try:
                file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except Exception:
                continue
            if file_date < cutoff_date:
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    continue
        return removed

    def list_files(self, days: int = 7) -> List[Tuple[str, str, int, str]]:
        self.ensure_dir()
        day_count = max(1, min(int(days), 30))
        start_date = (datetime.now().date() - timedelta(days=day_count - 1))

        files: List[Tuple[str, str, int, str]] = []
        for p in self.log_dir.iterdir():
            if not p.is_file():
                continue
            m = _FILE_RE.match(p.name)
            if not m:
                continue
            date_str = m.group(1)
            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                continue
            if file_date < start_date:
                continue
            stat = p.stat()
            files.append((p.name, date_str, stat.st_size, datetime.fromtimestamp(stat.st_mtime).isoformat()))

        files.sort(key=lambda x: x[1], reverse=True)
        return files

    def resolve_file_by_date(self, date_str: str) -> Optional[Path]:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            return None
        p = self.log_dir / f"fire_detection_{date_str}.log"
        if not p.exists() or not p.is_file():
            return None
        return p

    def query(
        self,
        start: datetime,
        end: datetime,
        levels: Optional[Set[str]] = None,
        keyword: Optional[str] = None,
        offset: int = 0,
        limit: int = 200,
        order: str = "desc",
    ) -> Tuple[List[_ParsedEntry], int]:
        self.ensure_dir()

        if start > end:
            start, end = end, start

        offset = max(0, int(offset))
        limit = max(1, min(int(limit), 1000))
        order = (order or "desc").lower()
        level_set = {l.upper() for l in levels} if levels else None
        kw = (keyword or "").strip().lower()

        files = self._files_in_range(start, end)
        if order == "desc":
            return self._query_desc(files, start, end, level_set, kw, offset, limit)
        return self._query_asc(files, start, end, level_set, kw, offset, limit)

    def _files_in_range(self, start: datetime, end: datetime) -> List[Path]:
        start_date = start.date()
        end_date = end.date()
        files: List[Path] = []
        for p in self.log_dir.iterdir():
            if not p.is_file():
                continue
            m = _FILE_RE.match(p.name)
            if not m:
                continue
            try:
                file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except Exception:
                continue
            if start_date <= file_date <= end_date:
                files.append(p)
        files.sort(key=lambda x: x.name)
        return files

    def _iter_entries(self, file_path: Path) -> Iterable[_ParsedEntry]:
        current: Optional[_ParsedEntry] = None
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")
                m = _LINE_RE.match(line)
                if m:
                    if current is not None:
                        yield current
                    try:
                        ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        current = None
                        continue
                    current = _ParsedEntry(
                        ts=ts,
                        level=m.group("level"),
                        logger=m.group("logger"),
                        message=m.group("msg"),
                    )
                else:
                    if current is not None:
                        current.message += "\n" + line
        if current is not None:
            yield current

    def _match(
        self,
        entry: _ParsedEntry,
        start: datetime,
        end: datetime,
        levels: Optional[Set[str]],
        keyword: str,
    ) -> bool:
        if entry.ts < start or entry.ts > end:
            return False
        if levels is not None and entry.level.upper() not in levels:
            return False
        if keyword:
            if keyword not in entry.message.lower() and keyword not in entry.logger.lower():
                return False
        return True

    def _query_asc(
        self,
        files: List[Path],
        start: datetime,
        end: datetime,
        levels: Optional[Set[str]],
        keyword: str,
        offset: int,
        limit: int,
    ) -> Tuple[List[_ParsedEntry], int]:
        items: List[_ParsedEntry] = []
        total = 0
        for fp in files:
            for e in self._iter_entries(fp):
                if not self._match(e, start, end, levels, keyword):
                    continue
                total += 1
                if total <= offset:
                    continue
                if len(items) < limit:
                    items.append(e)
        return items, total

    def _query_desc(
        self,
        files: List[Path],
        start: datetime,
        end: datetime,
        levels: Optional[Set[str]],
        keyword: str,
        offset: int,
        limit: int,
    ) -> Tuple[List[_ParsedEntry], int]:
        from collections import deque

        need = offset + limit
        buf = deque(maxlen=max(need, 1))
        total = 0
        for fp in files:
            for e in self._iter_entries(fp):
                if not self._match(e, start, end, levels, keyword):
                    continue
                total += 1
                if need > 0:
                    buf.append(e)

        data = list(buf)
        data.reverse()
        if offset:
            data = data[offset:]
        return data[:limit], total
