"""A wrapper around a YAML document that preserves line/column info.

We use `ruamel.yaml` because it keeps source positions. This module hides
the ruamel-specific details so the rest of the codebase deals only with
`Source`, `YamlNode`, and plain dicts/lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError

from warrant.parser.errors import SpecLoadError


@dataclass(frozen=True, slots=True)
class LineCol:
    line: int  # 1-based
    column: int  # 1-based


class Source:
    """A loaded YAML document plus its origin.

    Construct via `Source.from_file` or `Source.from_string`. Never
    instantiate directly.
    """

    __slots__ = ("_file", "_root", "_lines")

    def __init__(
        self,
        file: Path,
        root: Any,
        lines: tuple[str, ...],
    ) -> None:
        self._file = file
        self._root = root
        self._lines = lines

    @property
    def file(self) -> Path:
        return self._file

    @property
    def root(self) -> Any:
        return self._root

    @property
    def text(self) -> str:
        return "".join(self._lines)

    def line_at(self, line: int) -> str:
        """Return the source text of a 1-based line, without trailing newline."""
        if 1 <= line <= len(self._lines):
            return self._lines[line - 1].rstrip("\n")
        return ""

    # ---- Constructors ----

    @classmethod
    def from_string(cls, text: str, *, file: Path = Path("<string>")) -> Source | SpecLoadError:
        yaml = _make_yaml()
        try:
            root = yaml.load(text)
        except YAMLError as e:
            return _yaml_error_to_spec_error(e, file)
        if root is None:
            return SpecLoadError(
                message="spec file is empty",
                file=file,
                line=1,
                column=1,
            )
        if not isinstance(root, CommentedMap):
            return SpecLoadError(
                message="spec root must be a mapping (key: value pairs)",
                file=file,
                line=_node_line(root, default=1),
                column=_node_col(root, default=1),
            )
        return cls(file=file, root=root, lines=tuple(text.splitlines(keepends=True)))

    @classmethod
    def from_file(cls, path: Path) -> Source | SpecLoadError:
        if not path.exists():
            return SpecLoadError(message="file not found", file=path)
        if not path.is_file():
            return SpecLoadError(message="path is not a file", file=path)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            return SpecLoadError(
                message=f"file is not valid UTF-8: {e.reason}",
                file=path,
                line=e.start and 0 or None,
            )
        except OSError as e:
            return SpecLoadError(message=f"could not read file: {e.strerror}", file=path)
        return cls.from_string(text, file=path)


# ---------------------------------------------------------------------------
# Helpers for walking ruamel nodes
# ---------------------------------------------------------------------------


def node_line(node: Any, default: int = 1) -> int:
    """Best-effort 1-based line for a ruamel node or scalar."""
    return _node_line(node, default=default)


def node_col(node: Any, default: int = 1) -> int:
    """Best-effort 1-based column for a ruamel node or scalar."""
    return _node_col(node, default=default)


def lookup_path(root: Any, path: tuple[str, ...]) -> tuple[Any, int, int]:
    """Walk `path` through a YAML tree. Returns (node, line, column).

    If the path doesn't exist, returns the deepest reachable node and
    its position — useful for pointing at "the closest thing that exists."
    """
    node = root
    line = node_line(node)
    col = node_col(node)
    for key in path:
        if isinstance(node, dict) and key in node:
            node = node[key]
            line = node_line(node, default=line)
            col = node_col(node, default=col)
        elif isinstance(node, list) and key.isdigit():
            idx = int(key)
            if 0 <= idx < len(node):
                node = node[idx]
                line = node_line(node, default=line)
                col = node_col(node, default=col)
        else:
            # Path doesn't fully exist — stop here
            break
    return node, line, col


def _node_line(node: Any, default: int = 1) -> int:
    if isinstance(node, (CommentedMap, CommentedSeq)):
        try:
            lc: Any = node.lc
            line: int = int(lc.line) + 1  # ruamel is 0-based
            return line
        except (AttributeError, TypeError, ValueError):
            return default
    return default


def _node_col(node: Any, default: int = 1) -> int:
    if isinstance(node, (CommentedMap, CommentedSeq)):
        try:
            lc: Any = node.lc
            col: int = int(lc.col) + 1  # ruamel is 0-based
            return col
        except (AttributeError, TypeError, ValueError):
            return default
    return default


def _make_yaml() -> YAML:
    """A YAML parser configured for spec files.

    - `typ="rt"` (round-trip) gives us CommentedMap/CommentedSeq with `.lc`
      line/column info. This is the whole reason we chose ruamel over pyyaml.
    - `pure=True` uses the Python implementation (predictable across versions).
    - `version=(1, 2)` avoids the Norway problem (`no` stays a string).
    - `allow_duplicate_keys=False` catches accidental dupes in specs.
    """
    yaml = YAML(typ="rt", pure=True)
    yaml.preserve_quotes = True
    yaml.version = (1, 2)
    yaml.allow_duplicate_keys = False
    return yaml


def _yaml_error_to_spec_error(e: YAMLError, file: Path) -> SpecLoadError:
    """Translate a ruamel YAMLError into our structured error."""
    mark = getattr(e, "problem_mark", None)
    if mark is not None:
        return SpecLoadError(
            message=f"YAML syntax error: {getattr(e, 'problem', str(e))}",
            file=file,
            line=mark.line + 1,
            column=mark.column + 1,
        )
    return SpecLoadError(message=f"YAML error: {e}", file=file)
