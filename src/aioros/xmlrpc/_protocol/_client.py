from typing import Iterable, List, Union, cast

from lxml.builder import E
from lxml.etree import XMLParser, _Element, fromstring, tostring

from ._common import XmlRpcStructType, XmlRpcTypes, py2xml, validate_schema, xml2py
from ._exceptions import ParseError, ServerError, XMLRPCSystemError, xml2py_exception


def build_xml(method_name: str, *args: Iterable[XmlRpcTypes]) -> Union[str, bytes]:
    return b'<?xml version="1.0"?>\n' + tostring(
        E(
            "methodCall",
            E("methodName", method_name),
            E(
                "params",
                *(E("param", E("value", py2xml(arg))) for arg in args),
            ),
        ),
        encoding="ASCII",
    )


def parse_xml(body: bytes, method_name: str, *, huge_tree: bool = False) -> XmlRpcTypes:
    parser = XMLParser(huge_tree=huge_tree)
    response = fromstring(body, parser)
    if not validate_schema(response):
        raise ValueError("Invalid body")

    result = cast(List[_Element], response.xpath("//params/param/value"))
    if result:
        if len(result) < 2:
            return xml2py(result[0])

        return [xml2py(item) for item in result]

    fault = cast(List[_Element], response.xpath("//fault/value"))
    if fault:
        err = cast(XmlRpcStructType, xml2py(fault[0]))

        raise xml2py_exception(
            cast(int, err.get("faultCode", XMLRPCSystemError.code)),
            cast(str, err.get("faultString", "Unknown error")),
            default_exc_class=ServerError,
        )

    raise ParseError(
        f'Respond body for method "{method_name}" ' "not contains any response."
    )
