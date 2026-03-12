from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse

from ..schemas.common import Response
from ..schemas.logs import LogEntry, LogQueryResponse, LogFileInfo
from ..services.log_service import LogService
from .auth import require_auth, require_csrf


router = APIRouter(prefix="/logs", tags=["日志查询"], dependencies=[Depends(require_auth), Depends(require_csrf)])

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOG_DIR = _PROJECT_ROOT / "log"
_SERVICE = LogService(_LOG_DIR, retention_days=7)


def _parse_dt(v: Optional[str], default: datetime) -> datetime:
    if not v:
        return default
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(v, fmt)
        except Exception:
            continue
    raise ValueError("时间格式错误，支持 YYYY-MM-DD HH:mm:ss 或 YYYY-MM-DDTHH:mm:ss")


@router.get("", response_model=Response[LogQueryResponse])
def query_logs(
    start: Optional[str] = Query(None, description="开始时间"),
    end: Optional[str] = Query(None, description="结束时间"),
    levels: Optional[List[str]] = Query(None, description="日志级别列表"),
    keyword: Optional[str] = Query(None, description="关键字"),
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    try:
        now = datetime.now()
        default_end = now
        default_start = now - timedelta(days=7)

        start_dt = _parse_dt(start, default_start)
        end_dt = _parse_dt(end, default_end)

        level_set: Optional[Set[str]] = set(levels) if levels else None
        _SERVICE.cleanup()
        items, total = _SERVICE.query(
            start=start_dt,
            end=end_dt,
            levels=level_set,
            keyword=keyword,
            offset=offset,
            limit=limit,
            order=order,
        )
        data = LogQueryResponse(
            items=[
                LogEntry(
                    timestamp=e.ts.strftime("%Y-%m-%d %H:%M:%S"),
                    level=e.level,
                    logger=e.logger,
                    message=e.message,
                )
                for e in items
            ],
            total=total,
        )
        return Response.success(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"日志查询失败: {e}")


@router.get("/files", response_model=Response[List[LogFileInfo]])
def list_log_files(days: int = Query(7, ge=1, le=30)):
    try:
        _SERVICE.cleanup()
        files = _SERVICE.list_files(days=days)
        return Response.success(
            data=[
                LogFileInfo(file_name=f[0], date=f[1], size=f[2], mtime=f[3])
                for f in files
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志文件列表失败: {e}")


@router.get("/download/{date}", response_class=FileResponse)
def download_log_file(date: str):
    p = _SERVICE.resolve_file_by_date(date)
    if not p:
        raise HTTPException(status_code=404, detail="日志文件不存在")
    return FileResponse(path=str(p), filename=p.name, media_type="text/plain")
