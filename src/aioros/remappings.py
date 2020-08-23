import re
import sys
from typing import Dict
from typing import Iterator
from typing import Optional


REMAP_PATTERN = re.compile(r'^(?P<src>(\~)?[a-zA-Z0-9][\w\/]+):=(?P<dst>.+)')


class Remappings:

    def __init__(self) -> None:
        self._mappings: Dict[str, str] = {}
        for arg in sys.argv:
            match = REMAP_PATTERN.match(arg)
            if match:
                dct: Dict[str, str] = match.groupdict()
                self._mappings[dct['src']] = dct['dst']

    def get(self, key: str, default: str = None) -> Optional[str]:
        return self._mappings.get(key, default)

    def __len__(self) -> int:
        return len(self._mappings)

    def __contains__(self, key: str) -> bool:
        return key in self._mappings

    def __getitem__(self, key: str) -> str:
        return self._mappings[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._mappings)
