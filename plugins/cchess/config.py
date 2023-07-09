from pathlib import Path

from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    cchess_engine_path: Path = Path("data/cchess/fairy-stockfish")
