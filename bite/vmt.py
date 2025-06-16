from __future__ import annotations
import re
from typing import Dict, List

from . import base


# NOTE: incomplete, based on VDC
# -- they don't have a simple category for texture parameters
# -- also don't have documentation for all possible parameters
# -- https://developer.valvesoftware.com/wiki/Category_talk:Shader_parameters
texture_parameters = {
    "$basetexture": "colour",
    "$basetexture2": "colour2",
    "$blendmodulatetexture": "blend_modulate",
    "$bumpmap": "normal",
    "$bumpmap2": "normal2",
    # NOTE: if `$ssbump` is true, bumpmap is a self-shadowing bumpmap
    "$envmap": "cubemap",
    # NOTE: not always a texture, can be "env_cubemap"
    # -- this gets "patched" by the map compiler
    "$envmapmask": "specular",  # Source
    "$detail": "detail",
    "$lightmap": "lightmap",
    "$lightwarptexture": "light_warp",
    "$phongexponenttexture": "phong_exponent",
    "$specmap_texture": "specular_pbr",  # Black Mesa
    "$texture2": "multiply",
    # NOTE: texture2 is multiplied with basetexture in UnlitTwoTexture
    "%tooltexture": "editor"}


name_patterns = [
    re.compile(f"{a}(.+){a}")
    for a in ("'", '"', "")]


def name_of(line: str) -> str:
    for pattern in name_patterns:
        match = pattern.match(line)
        if match is not None:
            return match.groups()[0]


parameter_patterns = [
    re.compile(f"{a}(.+){a}\\s+{b}(.+){b}")
    for a in ("'", '"', "")
    for b in ("'", '"', "")]
# NOTE: unquoted last since we might accidental match it otherwise


def parameter_of(line: str) -> (str, str):
    for pattern in parameter_patterns:
        match = pattern.match(line)
        if match is not None:
            return match.groups()


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
    parameters: Dict[str, str]
    children: List[Node]
    _line_length: int  # for skipping child node lines

    def __init__(self):
        self.name = None
        self.parameters = dict()
        self.children = list()
        self._line_length = 0

    def __repr__(self) -> str:
        descriptor = " ".join([
            f"{self.name!r}" if self.name is not None else "None",
            f"{len(self.parameters)} parameters",
            f"{len(self.children)} children"])
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def __str__(self) -> str:
        indent = "  "
        lines = [escape(self.name), "{"]
        parameters = [
            f"{escape(key)} {escape(value)}"
            for key, value in self.parameters.items()]
        lines.extend(f"{indent}{line}" for line in parameters)
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
                parameter = parameter_of(line)
                name = name_of(line)
                # NOTE: check for parameters first, names can match parameters
                if parameter is not None:
                    key, value = parameter
                    out.parameters[key] = value
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
        # parameters -> textures
        for parameter, role in texture_parameters.items():
            if parameter in out._raw.parameters:
                texture_path = out._raw.parameters[parameter]
                texture_path = texture_path.lower().replace("\\", "/")
                out.textures[role] = texture_path
        # set flags from parameters
        translucent = out._raw.parameters.get("$translucent", 0)
        alphatest = out._raw.parameters.get("$alphatest", 0)
        out.is_transparent == 1 in (translucent, alphatest)
        return out
