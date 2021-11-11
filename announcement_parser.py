import re

class AnnoucementParser:
    def find_coin(self, title):
        coin = None
        if ("Will List" in title) | ("Lists" in title):
            m = re.search('\(([^)]+)', title)
            if m is not None and m.group(1).isupper():
                coin = m.group(1)
        return coin
