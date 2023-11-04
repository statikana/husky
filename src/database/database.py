"""
Each wrapper method will not check for the validity of the data
passed to it. It is assumed that the data passed to it is valid
and has been checked before being passed to the wrapper. However,
the wrapper will provide a method to check the validity of the
data passed to it, to be used by the user of the wrapper.
"""

import datetime
import enum
import inspect
from typing import Any, Callable, Optional
import asyncpg
from .database_types import Response, Task, autowrap
import time


class HuskyPool(asyncpg.Pool):
    pass

    @classmethod
    def from_apg_pool(cls, pool: asyncpg.Pool):
        return cls(
            min_size=pool._minsize,
            max_size=pool._maxsize,
            max_queries=pool._max_queries,
            max_inactive_connection_lifetime=pool._max_inactive_connection_lifetime,
            setup=pool._setup,
            init=pool._init,
            loop=pool._loop,
            connection_class=pool._connection_class,
            record_class=pool._record_class,
        )


class HuskyWrapper:
    def __init__(self, pool: HuskyPool):
        self.pool = pool

    async def make_table(self) -> None:
        """
        Creates the table for the wrapper if it doesn't exist.
        """
        raise NotImplementedError

    async def drop_table(self) -> None:
        """
        Drops the table for the wrapper if it exists.
        """
        raise NotImplementedError


class Users(HuskyWrapper):
    async def make_table(self) -> None:
        await self.pool.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY
            )"""
        )

    async def drop_table(self) -> None:
        await self.pool.execute(
            """
            DROP TABLE IF EXISTS users
            """
        )

    async def user_check(self, user_id: int) -> None:
        await self.pool.execute(
            """
            INSERT INTO users (user_id)
            VALUES ($1)
            ON CONFLICT DO NOTHING
            """,
            user_id,
        )


class TODO(HuskyWrapper):
    async def make_table(self) -> None:
        await self.pool.execute(
            """
            CREATE TABLE IF NOT EXISTS todo (
                task_id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                task TEXT NOT NULL UNIQUE,
                date DATE,
                time TIME,
                remind_type INT,
                datetime_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE (user_id, task)
            )
            """
        )

    async def drop_table(self) -> None:
        await self.pool.execute(
            """
            DROP TABLE IF EXISTS todo
            """
        )

    async def new_todo(
        self,
        user_id,
        task: str,
        date: datetime.date | None = None,
        time: datetime.time | None = None,
        remind_type: str | None = None,
    ) -> None:
        if remind_type is None:
            remind_type = 1
        elif remind_type == "Direct Message":
            remind_type = 2
        elif remind_type == "Not Set [None]":
            remind_type = 0
        else:
            raise ValueError("Invalid remind_type")

        try:
            await self.pool.execute(
                """
                INSERT INTO todo (user_id, task, date, time, remind_type)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                task,
                date,
                time,
                remind_type,
            )
        except asyncpg.UniqueViolationError:
            raise ValueError("Task already exists")

    async def get_todo_by_id(self, task_id: int) -> Task:
        task = autowrap(
            Task,
            await self.pool.fetchrow(
                """
            SELECT * FROM todo
            WHERE task_id = $1
            """,
                task_id,
            ),
        )
        return task

    async def get_user_tasks(self, user_id: int) -> list[Task]:
        tasks = [
            autowrap(Task, t)
            for t in await self.pool.fetch(
                """
            SELECT * FROM todo
            WHERE user_id = $1
            """,
                user_id,
            )
        ]
        return tasks

    async def get_overdue_tasks(self, threshold_sec: int = 0) -> list[Task]:
        tasks = [
            autowrap(Task, t)
            for t in await self.pool.fetch(
                """
                    SELECT * FROM todo
                    WHERE time < CURRENT_TIME - $1::INTERVAL AND date <= CURRENT_DATE
                """,
                datetime.timedelta(seconds=threshold_sec),
            )
        ]
        return tasks

    async def get_user_overdue_tasks(self, user_id: int) -> list[Task]:
        tasks = [
            autowrap(Task, t)
            for t in await self.pool.fetch(
                """
            SELECT * FROM todo
            WHERE user_id = $1 AND date < CURRENT_DATE
            """,
                user_id,
            )
        ]
        return tasks

    async def trim_overdue_tasks(self, min_overdue_seconds: int = 0) -> list[Task]:
        return await self.pool.fetch(
            """
            DELETE FROM todo
            WHERE date < CURRENT_DATE - $1::INTERVAL
            RETURNING *
            """,
            datetime.timedelta(seconds=min_overdue_seconds),
        )

    async def delete_task(self, task_id: int) -> None:
        await self.pool.execute(
            """
            DELETE FROM todo
            WHERE task_id = $1
            """,
            task_id,
        )

    async def delete_user_tasks(self, user_id: int) -> None:
        await self.pool.execute(
            """
            DELETE FROM todo
            WHERE user_id = $1
            """,
            user_id,
        )
