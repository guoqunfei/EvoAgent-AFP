# -*- coding: utf-8 -*-
"""
SQLite 数据库管理工具类。

封装 SQLite 数据库的初始化、连接管理、基本增删改查操作以及事务支持，
适合在 FastAPI 等后端项目中作为数据库访问层使用。
"""
from __future__ import annotations  # 允许在类型注解中使用类本身的名字而不必用字符串

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from typing import List, Dict, Tuple

class SQLiteManager:
    """
    SQLite 数据库管理器。

    主要负责：
    - 根据指定的数据库文件路径和建表脚本（schema）初始化数据库
    - 提供一个上下文管理器来获取数据库连接
    - 封装常用的 execute / executemany / fetch_one / fetch_all 方法
    - 支持手动事务
    """

    def __init__(self, db_path: Path, schema_path: Path, wal_mode: bool = True) -> None:
        """
        初始化管理器。

        Args:
            db_path: SQLite 数据库文件路径（.db 文件）。
            schema_path: 建表 SQL 脚本的路径（.sql 文件）。
            wal_mode: 是否启用 WAL（Write-Ahead Logging）日志模式，默认为 True。
                       WAL 模式可以提高并发读写性能，尤其适合 Web 应用。
        """
        self.db_path = db_path
        self.schema_path = schema_path
        self.wal_mode = wal_mode

    def initialize(self) -> None:
        """
        执行数据库初始化：

        1. 确保数据库文件所在的父目录存在（不存在则递归创建）。
        2. 打开数据库连接（此时若 db 文件不存在会自动创建）。
        3. 根据 wal_mode 设置 journal_mode 为 WAL（提高并发性能）。
        4. 开启外键约束支持（PRAGMA foreign_keys = ON）。
        5. 读取并执行 schema_path 指定的 SQL 脚本（通常是建表语句）。
        6. 提交所有更改。

        注意：
        - 每次调用都会重新执行 schema 脚本，因此脚本中的建表语句应使用
          `CREATE TABLE IF NOT EXISTS` 以保证幂等性，否则重复执行会报错。
        - 如果仅仅想确保数据库和目录存在而不重复执行 schema，可以修改逻辑，
          例如检查文件是否已存在、使用标志位或数据库迁移工具。
        """
        # 创建数据库文件所在目录（若不存在）
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用连接上下文执行初始化操作
        with self.connection() as conn:
            # 设置 WAL 日志模式
            if self.wal_mode:
                conn.execute("PRAGMA journal_mode = WAL;")
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON;")
            # 读取并执行 schema 文件中的所有 SQL 语句
            conn.executescript(self.schema_path.read_text(encoding="utf-8"))
            # 提交变更
            conn.commit()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """
        提供一个 SQLite 连接的上下文管理器。

        特点：
        - 设置 check_same_thread=False，允许多线程使用同一个连接（在 FastAPI
          等异步或线程池环境中很有用，但要注意 SQLite 本身不适合高并发写入）。
        - 设置 row_factory = sqlite3.Row，使得查询返回的行对象支持按列名访问，
          并且可以方便地转换为 dict。
        - 在退出上下文时自动关闭连接。

        Yields:
            sqlite3.Connection: 配置好的数据库连接对象。
        """
        # 建立连接，check_same_thread=False 允许在非创建线程中使用
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # 将行工厂设置为 sqlite3.Row，这样 fetch 的结果可以通过键名访问
        conn.row_factory = sqlite3.Row
        try:
            # 将连接提供给 with 语句的上下文
            yield conn
        finally:
            # 确保连接被关闭
            conn.close()

    def execute(
        self,
        sql: str,
        params: Dict[str, Any] | Tuple[Any, ...] | None = None,
        *,
        commit: bool = True,
    ) -> None:
        """
        执行单条 SQL 语句（INSERT、UPDATE、DELETE 等）。

        Args:
            sql: 要执行的 SQL 语句，可以包含占位符（? 或 :key）。
            params: SQL 参数，可以是字典或元组，默认为 None。
            commit: 是否在语句执行后自动提交，默认为 True。
                    如果在一个事务中批量执行，可以设为 False 并手动提交。
        """
        # 获取连接，执行语句
        with self.connection() as conn:
            # 如果没有提供参数，使用空字典避免 execute 报错
            conn.execute(sql, params or {})
            # 根据 commit 参数决定是否提交
            if commit:
                conn.commit()

    def execute_many(self, sql: str, params_seq: List[Dict[str, Any]]) -> None:
        """
        批量执行同一条 SQL 语句（如批量插入）。

        Args:
            sql: SQL 语句模板，包含占位符。
            params_seq: 参数序列，每个元素是一个参数字典（或元组）。
        """
        with self.connection() as conn:
            # 执行 executemany 批量操作
            conn.executemany(sql, params_seq)
            # 自动提交
            conn.commit()

    def fetch_one(
        self,
        sql: str,
        params: Dict[str, Any] | Tuple[Any, ...] | None = None,
    ) -> Dict[str, Any] | None:
        """
        执行查询并返回单条结果（转换为字典）。

        Args:
            sql: 查询 SQL 语句。
            params: 查询参数，默认为 None。

        Returns:
            如果查询到记录则返回一个 dict，键为列名；否则返回 None。
        """
        with self.connection() as conn:
            # 执行查询并获取第一条记录
            row = conn.execute(sql, params or {}).fetchone()
            # 将 Row 对象转换为普通字典，没有结果则返回 None
            return dict(row) if row else None

    def fetch_all(
        self,
        sql: str,
        params: Dict[str, Any] | Tuple[Any, ...] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        执行查询并返回所有结果（每行转换为字典）。

        Args:
            sql: 查询 SQL 语句。
            params: 查询参数，默认为 None。

        Returns:
            包含所有结果的列表，每个元素是一个字典。如果没有结果则返回空列表。
        """
        with self.connection() as conn:
            # 执行查询并获取所有记录
            rows = conn.execute(sql, params or {}).fetchall()
            # 将每一行 Row 对象转换为字典
            return [dict(row) for row in rows]

    def transaction(
        self,
        statements: List[Tuple[str, Dict[str, Any] | Tuple[Any, ...] | None]],
    ) -> None:
        """
        在手动事务中执行一组 SQL 语句。

        如果过程中任何语句执行失败，会自动回滚所有已执行的语句，并重新抛出异常。

        Args:
            statements: 一个列表，每个元素为 (sql, params) 元组，
                        params 可以为 None、字典或元组。
        """
        with self.connection() as conn:
            try:
                # 逐条执行语句
                for sql, params in statements:
                    conn.execute(sql, params or {})
                # 所有语句执行成功则提交事务
                conn.commit()
            except Exception:
                # 任何异常导致事务回滚
                conn.rollback()
                raise  # 重新抛出异常，让上层调用者感知错误