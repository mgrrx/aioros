import base64
import os
from datetime import datetime
from functools import singledispatch
from types import GeneratorType
from typing import Any, Dict, List, Optional, Union, cast

from lxml.builder import E
from lxml.etree import RelaxNG, _Element

NoneType = type(None)

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

TIME_FORMAT = "%Y%m%dT%H:%M:%S"
TIME_FORMATS = [TIME_FORMAT, "%Y%m%dT%H%M%S"]

SCHEMA = RelaxNG(file=os.path.join(CURRENT_DIR, "xmlrpc.rng"))


class Binary(bytes):
    @classmethod
    def fromstring(cls, data: Optional[str]) -> "Binary":
        if data is None:
            return cls(b"")

        return cls(base64.b64decode(data))


XmlRpcTypes = Union[
    str,
    bytes,
    bool,
    datetime,
    int,
    Binary,
    NoneType,
    "XmlRpcArrayType",
    "XmlRpcStructType",
]
XmlRpcArrayType = List[XmlRpcTypes]
XmlRpcStructType = Dict[str, XmlRpcTypes]


@singledispatch
def py2xml(_: Any) -> _Element:
    raise TypeError()


@py2xml.register(bytes)
def _(value: bytes) -> _Element:
    return E("string", value.decode())


@py2xml.register(str)
def _(value: str) -> _Element:
    return E("string", value)


@py2xml.register(float)
def _(value: float) -> _Element:
    return E("double", str(value))


@py2xml.register(datetime)
def _(value: datetime) -> _Element:
    return E("dateTime.iso8601", value.strftime(TIME_FORMAT))


@py2xml.register(int)
def _(value: int) -> _Element:
    if -2147483648 < value < 2147483647:
        return E("i4", str(value))
    return E("double", str(value))


@py2xml.register(Binary)
def _(value: Binary) -> _Element:
    return E("base64", str(base64.b64encode(value).decode()))


@py2xml.register(bool)
def _(value: bool) -> _Element:
    return E("boolean", "1" if value else "0")


@py2xml.register(NoneType)
def _(_: NoneType) -> _Element:
    return E("nil")


@py2xml.register(list)
@py2xml.register(tuple)
@py2xml.register(set)
@py2xml.register(frozenset)
@py2xml.register(GeneratorType)
def _(value: Union[list, tuple, set, frozenset, GeneratorType]) -> _Element:
    return E("array", E("data", *(E("value", py2xml(i)) for i in value)))


@py2xml.register(dict)
def _(value: dict) -> _Element:
    return E(
        "struct",
        *(
            E("member", E("name", str(key)), E("value", py2xml(val)))
            for key, val in value.items()
        ),
    )


def xml2datetime(value: _Element) -> datetime:
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(str(value.text or ""), fmt)
        except ValueError:
            pass

    raise ValueError(f"It's impossible to parse dataetime with formats {TIME_FORMATS}")


def xml2struct(element: _Element) -> XmlRpcStructType:
    values = cast(List[_Element], element.xpath("./member/value"))
    names = cast(List[str], element.xpath("./member/name/text()"))
    return {str(name): xml2py(value) for name, value in zip(names, values)}


def xml2array(element: _Element) -> XmlRpcArrayType:
    values = cast(List[_Element], element.xpath("./data/value"))
    return [xml2py(i) for i in values]


def xml2string(element: _Element) -> str:
    return str(element.text or "").strip()


def xml2int(element: _Element) -> int:
    return int(element.text or 0)


def xml2none(element: _Element) -> None:
    # pylint: disable=unused-argument
    return None


def xml2float(element: _Element) -> float:
    return float(element.text or 0.0)


def xml2bool(element: _Element) -> bool:
    return bool(int(element.text or 0))


def xml2binary(element: _Element) -> Binary:
    return Binary.fromstring(element.text or "")


def unwrap_value(element: _Element) -> XmlRpcTypes:
    try:
        return xml2py(next(iter(element.iterchildren())))
    except StopIteration:
        return xml2py(element.text or "")


XML2PY_TYPES = {
    "string": xml2string,
    "struct": xml2struct,
    "array": xml2array,
    "base64": xml2binary,
    "boolean": xml2bool,
    "dateTime.iso8601": xml2datetime,
    "double": xml2float,
    "integer": xml2int,
    "int": xml2int,
    "i4": xml2int,
    "nil": xml2none,
    "value": unwrap_value,
}


def xml2py(value: Union[str, _Element]) -> XmlRpcTypes:
    if isinstance(value, str):
        return cast(str, value).strip()
    return XML2PY_TYPES[value.tag](value)


def validate_schema(element: _Element) -> bool:
    return SCHEMA.validate(element)
