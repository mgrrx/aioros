from typing import List, Mapping, Tuple, Union, cast

from lxml.builder import E
from lxml.etree import XMLParser, _Element, fromstring, tostring

from ._common import XmlRpcTypes, py2xml, validate_schema, xml2py


def format_success(result: XmlRpcTypes) -> _Element:
    return E("methodResponse", E("params", E("param", E("value", py2xml(result)))))


def format_error(exception: Exception) -> _Element:
    return E("methodResponse", E("fault", E("value", py2xml(exception))))


def parse_xml(xml_string: bytes) -> _Element:
    parser = XMLParser(resolve_entities=False)
    root = fromstring(xml_string, parser)
    if not validate_schema(root):
        raise ValueError("Invalid body")
    return root


def build_xml(tree: _Element) -> Union[str, bytes]:
    return b'<?xml version="1.0"?>\n' + tostring(tree, encoding="ASCII")


def parse_request(
    body: bytes, headers: Mapping[bytes, bytes]
) -> Tuple[str, List[XmlRpcTypes]]:
    if b"xml" not in headers.get(b"content-type", b""):
        raise ValueError()

    xml_request = parse_xml(body)

    method_name = cast(List[str], xml_request.xpath("//methodName[1]/text()"))[0]

    params = cast(List[_Element], xml_request.xpath("//params/param/value"))
    args = [xml2py(param) for param in params]

    return method_name, args
