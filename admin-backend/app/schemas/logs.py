from typing import List, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    timestamp: str = Field(..., description="时间戳，格式 YYYY-MM-DD HH:mm:ss")
    level: str = Field(..., description="日志级别")
    logger: str = Field(..., description="logger 名称")
    message: str = Field(..., description="日志内容")


class LogQueryResponse(BaseModel):
    items: List[LogEntry] = Field(default_factory=list, description="日志列表")
    total: int = Field(0, description="符合条件的总条数")


class LogFileInfo(BaseModel):
    file_name: str = Field(..., description="文件名")
    date: str = Field(..., description="文件日期 YYYY-MM-DD")
    size: int = Field(..., description="文件大小 bytes")
    mtime: str = Field(..., description="最后修改时间 ISO")

