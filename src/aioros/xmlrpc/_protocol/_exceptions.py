from typing import Dict, Type, Union

from lxml.builder import E
from lxml.etree import _Element

from ._common import py2xml

__all__ = (
    "XMLRPCError",
    "ApplicationError",
    "InvalidCharacterError",
    "ParseError",
    "ServerError",
    "XMLRPCSystemError",
    "TransportError",
    "UnsupportedEncodingError",
)


class XMLRPCError(Exception):
    code = -32500

    @property
    def message(self) -> str:
        return self.args[0]

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"<[{self.code}] {self.name}({self.message})>"


class ParseError(XMLRPCError):
    code = -32700


class UnsupportedEncodingError(ParseError):
    code = -32701


class InvalidCharacterError(ParseError):
    code = -32702


class ServerError(XMLRPCError):
    code = -32603


class InvalidData(ServerError):
    code = -32600


class MethodNotFound(ServerError):
    code = -32601


class InvalidArguments(ServerError):
    code = -32602


class ApplicationError(XMLRPCError):
    code = -32500


class XMLRPCSystemError(XMLRPCError):
    code = -32400


class TransportError(XMLRPCError):
    code = -32300


__EXCEPTION_CODES: Dict[int, Type[Exception]] = {
    -32000: Exception,
    XMLRPCError.code: XMLRPCError,
    ParseError.code: ParseError,
    UnsupportedEncodingError.code: UnsupportedEncodingError,
    InvalidCharacterError.code: InvalidCharacterError,
    ServerError.code: ServerError,
    InvalidData.code: InvalidData,
    MethodNotFound.code: MethodNotFound,
    InvalidArguments.code: InvalidArguments,
    ApplicationError.code: ApplicationError,
    XMLRPCSystemError.code: XMLRPCSystemError,
    TransportError.code: TransportError,
}

__EXCEPTION_TYPES: Dict[Type[Exception], int] = {
    value: key for key, value in __EXCEPTION_CODES.items()
}


def xml2py_exception(
    code: int, fault: str, default_exc_class: Type[Exception] = XMLRPCError
) -> Union[Exception, XMLRPCError]:
    if code not in __EXCEPTION_CODES:
        exc = default_exc_class(fault)
        setattr(exc, "code", code)
        return exc

    return __EXCEPTION_CODES[code](fault)


@py2xml.register(Exception)
def _(value: Exception) -> _Element:
    code, reason = __EXCEPTION_TYPES[Exception], repr(value)

    for klass in value.__class__.__mro__:
        if klass in __EXCEPTION_TYPES:
            code = __EXCEPTION_TYPES[klass]
            break

    return E(
        "struct",
        E("member", E("name", "faultCode"), E("value", py2xml(code))),
        E("member", E("name", "faultString"), E("value", py2xml(reason))),
    )
