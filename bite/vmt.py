from __future__ import annotations
import re
from typing import Dict, List

from . import base


keyvalue_patterns = [
    re.compile(f"{a}(.+){a}\\s+{b}(.+){b}")
    for a in ("'", '"', "")
    for b in ("'", '"', "")]
# NOTE: unquoted last since we might accidental match it otherwise


name_patterns = [
    re.compile(f"{a}(.+){a}")
    for a in ("'", '"', "")]


def keyvalue_of(line: str) -> (str, str):
    for pattern in keyvalue_patterns:
        match = pattern.match(line)
        if match is not None:
            return match.groups()


def name_of(line: str) -> str:
    for pattern in name_patterns:
        match = pattern.match(line)
        if match is not None:
            return match.groups()[0]


def escape(word: str) -> str:
    # TODO: check if word cannot be escaped
    if "'" in word or " " in word:
        return f'"{word}"'
    elif '"' in word:
        return f"'{word}'"
    else:
        return word


class Node:
    name: str
    keyvalues: Dict[str, str]
    children: List[Node]
    _line_length: int  # for skipping child node lines

    def __init__(self):
        self.name = None
        self.keyvalues = dict()
        self.children = list()
        self._line_length = 0

    def __repr__(self) -> str:
        descriptor = " ".join([
            f"{self.name!r}" if self.name is not None else "None",
            f"{len(self.keyvalues)} keyvalues",
            f"{len(self.children)} children"])
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def __str__(self) -> str:
        indent = "  "
        lines = [escape(self.name), "{"]
        keyvalues = [
            f"{escape(key)} {escape(value)}"
            for key, value in self.keyvalues.items()]
        lines.extend(f"{indent}{line}" for line in keyvalues)
        for child in self.children:
            lines.extend(
                f"{indent}{line}"
                for line in str(child).split("\n"))
        lines.append("}")
        return "\n".join(lines)

    @classmethod
    def from_lines(cls, lines: List[str], prev_line=None) -> Node:
        out = cls()
        if prev_line is not None:
            out.name = prev_line
        i = 0
        while i <= len(lines):
            line = lines[i]
            line, sep, comment = line.partition("//")
            line = line.strip()  # no leading / trailing whitespace
            i += 1
            if line == "{":
                if out.name is None:  # top node
                    out.name = prev_line
                else:  # child node
                    child = Node.from_lines(lines[i:], prev_line)
                    out.children.append(child)
                    i += child._line_length
            elif line == "}":
                out._line_length = i
                return out  # node has been closed
            else:
                keyvalue = keyvalue_of(line)
                name = name_of(line)
                # NOTE: check for keyvalues first, names can match keyvalues
                if keyvalue is not None:
                    key, value = keyvalue
                    out.keyvalues[key] = value
                elif name is not None:
                    prev_line = name
                else:
                    prev_line = line
        raise RuntimeError("reached EOF before node closed")


class VMT(base.Material):
    is_text_based: bool = True
    extension: str = "vmt"
    shader: str
    is_transparent: bool
    textures: Dict[str, str]
    # keep the top level node as reference
    _raw: Node

    def __init__(self):
        super().__init__()
        self._raw = Node()

    @classmethod
    def from_lines(cls, lines: List[str]) -> VMT:
        out = cls()
        out._raw = Node.from_lines(lines)
        out.shader = out._raw.name
        # TODO: use a lookup dict to get textures from keyvalues
        # out.textures["base"] = out._raw.keyvalues["$basetexture"]
        # out.textures["secondary"] = out._raw.keyvalues["$texture2"]
        # TODO: set flags from keyvalues
        # out.is_transparent = bool(out._raw.keyvalues.get("$transparent", 0))
        return out
