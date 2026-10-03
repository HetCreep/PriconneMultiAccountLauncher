import contextlib
import json
import os
from pathlib import Path
from tkinter import Variable


class VariableBase:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_dict(self) -> dict[str, str]:
        return {k: v.get() if isinstance(v, Variable) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, obj: dict[str, str]):
        default = cls().__dict__
        item = [(k, v(value=obj.get(k, default[k].get()))) for k, v in cls.__annotations__.items()]
        return cls(**dict(item))

    @classmethod
    def from_path(cls, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def write_path(self, path: Path):
        """Atomic write — tmp + os.replace so a crash mid-write never produces a half JSON."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            # Best-effort cleanup of the partial tmp file; ignore if it's already gone.
            with contextlib.suppress(OSError):
                tmp.unlink()
            raise
