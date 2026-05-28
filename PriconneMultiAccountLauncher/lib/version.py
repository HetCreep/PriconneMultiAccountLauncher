import re
from typing import Tuple


class Version:
    _PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

    def __init__(self, version: str):
        m = self._PATTERN.match(version)
        if not m:
            raise ValueError(f"Invalid version format: {version}")
        self.major = int(m.group(1))
        self.minor = int(m.group(2))
        self.patch = int(m.group(3))

    def _tuple(self) -> Tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"Version('{self}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._tuple() == other._tuple()

    def __ne__(self, other: object) -> bool:
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    def __lt__(self, other: "Version") -> bool:
        return self._tuple() < other._tuple()

    def __le__(self, other: "Version") -> bool:
        return self._tuple() <= other._tuple()

    def __gt__(self, other: "Version") -> bool:
        return self._tuple() > other._tuple()

    def __ge__(self, other: "Version") -> bool:
        return self._tuple() >= other._tuple()

    def __hash__(self) -> int:
        return hash(self._tuple())
