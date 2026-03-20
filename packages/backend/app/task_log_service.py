"""
任务日志服务 - 记录任务执行历史到数据库
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, and_

from .database import db, TaskLog


class TaskLogService:
    """任务日志服务"""

    def __init__(self):
        pass

    def log_task(
        self,
        platform: str,
        task_type: str,
        success: bool,
        email: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        proxy_used: Optional[str] = None,
        duration_ms: int = 0,
    ) -> int:
        """
        记录一条任务日志
        返回日志 ID
        """
        with db.get_session() as session:
            log = TaskLog(
                platform=platform,
                task_type=task_type,
                success=success,
                email=email,
                message=message,
                error=error,
                proxy_used=proxy_used,
                duration_ms=duration_ms,
            )
            session.add(log)
            session.flush()
            return log.id

    def get_logs(
        self,
        platform: str = "",
        task_type: str = "",
        success: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[list[dict], int]:
        """
        获取任务日志列表
        """
        with db.get_session() as session:
            query = session.query(TaskLog)

            if platform:
                query = query.filter(TaskLog.platform == platform)
            if task_type:
                query = query.filter(TaskLog.task_type == task_type)
            if success is not None:
                query = query.filter(TaskLog.success == success)
            if start_time:
                query = query.filter(TaskLog.created_at >= start_time)
            if end_time:
                query = query.filter(TaskLog.created_at <= end_time)

            total = query.count()

            logs = query.order_by(TaskLog.created_at.desc()) \
                       .offset((page - 1) * page_size) \
                       .limit(page_size) \
                       .all()

            return [l.to_dict() for l in logs], total

    def get_stats(
        self,
        platform: str = "",
        days: int = 7
    ) -> dict:
        """
        获取任务统计
        """
        with db.get_session() as session:
            query = session.query(TaskLog)

            if platform:
                query = query.filter(TaskLog.platform == platform)

            # 最近 N 天
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(TaskLog.created_at >= since)

            total = query.count()
            success_count = query.filter(TaskLog.success == True).count()
            fail_count = total - success_count

            # 平均耗时
            avg_duration = session.query(func.avg(TaskLog.duration_ms)).filter(
                and_(
                    TaskLog.platform == platform if platform else True,
                    TaskLog.created_at >= since,
                    TaskLog.success == True
                )
            ).scalar() or 0

            # 按天统计
            daily_stats = session.query(
                func.date(TaskLog.created_at).label('date'),
                func.count(TaskLog.id).label('total'),
                func.sum(func.cast(TaskLog.success == True, int)).label('success'),
            ).filter(
                and_(
                    TaskLog.platform == platform if platform else True,
                    TaskLog.created_at >= since
                )
            ).group_by(func.date(TaskLog.created_at)).all()

            return {
                "total": total,
                "success": success_count,
                "fail": fail_count,
                "success_rate": round(success_count / max(total, 1) * 100, 2),
                "avg_duration_ms": round(avg_duration, 2),
                "daily": [
                    {
                        "date": str(d.date),
                        "total": d.total,
                        "success": d.success or 0,
                    }
                    for d in daily_stats
                ]
            }

    def get_today_stats(self, platform: str = "") -> dict:
        """获取今日统计"""
        with db.get_session() as session:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            query = session.query(TaskLog).filter(TaskLog.created_at >= today_start)
            if platform:
                query = query.filter(TaskLog.platform == platform)

            total = query.count()
            success = query.filter(TaskLog.success == True).count()

            return {
                "total": total,
                "success": success,
                "fail": total - success,
                "success_rate": round(success / max(total, 1) * 100, 2),
            }


# 全局实例
task_log_service = TaskLogService()
