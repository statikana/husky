"""
Each wrapper method will not check for the validity of the data
passed to it. It is assumed that the data passed to it is valid
and has been checked before being passed to the wrapper. However,
the wrapper will provide a method to check the validity of the
data passed to it, to be used by the user of the wrapper.
"""

import enum
import inspect
from typing import Any, Callable, Optional
import asyncpg
from .data_types import Claim, Dimension


class HuskyPool(asyncpg.Pool):
    pass

    @classmethod
    def from_apg_pool(cls, pool: asyncpg.Pool):
        return cls(
            pool._dsn,
            pool._min_size,
            pool._max_size,
            pool._timeout,
            pool._max_queries,
            pool._max_inactive_connection_lifetime,
            pool._setup,
        )


class HuskyWrapper:
    def __init__(self, pool: HuskyPool):
        self.pool = pool

    async def make_table(self) -> None:
        """
        Creates the table for the wrapper if it doesn't exist.
        """
        raise NotImplementedError


class ClaimsWrapper(HuskyWrapper):
    CLAIMS_PER_USER_PER_DIMENSION = 1
    CLAIM_RADIUS = 200
    ALLOWED_DIMENSIONS = [Dimension.OVERWORLD, Dimension.NETHER, Dimension.THE_END]
    ALLOW_INTERSECTING_CLAIMS = False

    async def make_table(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    user_id INT,
                    claim_x INT,
                    claim_y INT,
                    dimension INT DEFAULT 0,
                    claim_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    async def make_claim(
        self, user_id: int, claim_x: int, claim_y: int, dimension: Dimension
    ) -> Claim:
        """
        Establishes a claim for a user at the given coordinates and dimension.
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO claims (user_id, claim_x, claim_y, dimension)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                user_id,
                claim_x,
                claim_y,
                dimension.value,
            )
            return Claim(**result)

    async def get_claims(
        self,
        user_id: Optional[int] = None,
        claim_x: Optional[int] = None,
        claim_y: Optional[int] = None,
        dimension: Optional[Dimension] = None,
    ) -> list[Claim]:
        """
        Returns a list of claims that match the given parameters.
        Any parameters that are not given will be ignored.
        """
        async with self.pool.acquire() as conn:
            params_values = [user_id, claim_x, claim_y, dimension]
            names = inspect.getfullargspec(self.get_claims).args[
                1:
            ]  # get all arg names except self
            params_names = [
                name for name, value in zip(names, params_values) if value is not None
            ]  # get all arg names that have a value
            query = "SELECT * FROM claims"
            query, params_values = self._add_where_params(
                query, params_names
            )  # add WHERE clause to query, format
            result = await conn.fetch(query, *params_values)
            return [Claim(**row) for row in result]

    async def remove_claim(
        self, claim_x: int, claim_y: int, dimension: Dimension
    ) -> Claim:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM claims
                WHERE claim_x = $1 AND claim_y = $2 AND dimension = $3
                """,
                claim_x,
                claim_y,
                dimension.value,
            )
    
    async def get_intersecting_claims(
        self, claim_x: int, claim_y: int, dimension: Dimension
    ) -> list[Claim]:
        """
        Returns a list of all claims which would be intersecting a new theoretical claim at (claim_x, claim_y) in dimension
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT * FROM claims WHERE
                SQRT(SQUARE(claim_x - $1) + SQUARE(claim_y - $2)) < $3
                AND dimension = $4
                """,
                claim_x,
                claim_y,
                self.CLAIM_RADIUS,
                dimension.value
            )
            # checks if the distance between the argument's claim point and 
            # any other point in the same dimension is less than CLAIM_RADIUS
            return [Claim(**row) for row in result]
    
    async def user_at_claim_limit(self, user_id: int, dimension: Dimension) -> bool:
        """
        Returns whether or not the user has reached CLAIMS_PER_USER_PER_DIMENSION in `dimension`
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT COUNT(*) FROM claims
                WHERE user_id = $1 AND dimension = $2
                """,
                user_id,
                dimension.value
            )
            return result[0] >= self.CLAIMS_PER_USER_PER_DIMENSION

    def _add_where_params(
        self, query: str, param_names: list[str],
    ) -> tuple[str, list[Any]]:
        """
        Formats the query to include a WHERE clause and param names to value requirements
        """
        if param_names:
            query += " WHERE " + " AND ".join(
                f"{param_name} = ${i+1}" for i, param_name in enumerate(param_names)
            )
            return query
        return query
