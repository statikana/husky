from typing import NamedTuple


class Indicies(NamedTuple):
    start: int
    end: int


class Color(NamedTuple):
    red: int
    green: int
    blue: int
    alpha: int = 255

    @classmethod
    def from_rgb(cls, red: int, green: int, blue: int) -> "Color":
        return cls(int(red), int(green), int(blue))

    def to_rgb(self) -> tuple[int, int, int]:
        return self.red, self.green, self.blue

    @classmethod
    def from_rgba(cls, red: int, green: int, blue: int, alpha: int) -> "Color":
        return cls(int(red), int(green), int(blue), int(alpha))

    def to_rgba(self) -> tuple[int, int, int, int]:
        return self.red, self.green, self.blue, self.alpha

    @classmethod
    def from_hex(cls, hex: str) -> "Color":
        hex = hex.strip("#")
        if len(hex) == 6:
            hex += "FF"
        return cls(*[int(hex[i : i + 2], 16) for i in range(0, 8, 2)])

    def to_hex(self) -> str:
        return "#" + "".join(hex(i)[2:].zfill(2) for i in self.to_rgba())

    def __repr__(self) -> str:
        return f"Color[{self.red} {self.green} {self.blue} {self.alpha}]"

    def __str__(self) -> str:
        return self.__repr__()


class LoadedFile(NamedTuple):
    path: str
    filename: str
