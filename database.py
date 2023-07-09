import asyncpg


class HuskyPool(asyncpg.Pool):
    pass

    @classmethod
    def from_apg_pool(cls, pool: asyncpg.Pool):
        return cls(pool._dsn, pool._min_size, pool._max_size, pool._timeout, pool._max_queries, pool._max_inactive_connection_lifetime, pool._setup)


