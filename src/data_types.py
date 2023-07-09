from dataclasses import dataclass
import enum


class Dimension(enum.Enum):
    OVERWORLD = 0
    NETHER = 1
    THE_END = 2


@dataclass
class Claim:
    user_id: int
    claim_x: int
    claim_y: int
    dimension: Dimension
