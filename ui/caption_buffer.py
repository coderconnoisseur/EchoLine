class CaptionBuffer:
    """Rolling caption text built from finalized and partial recognition results"""

    def __init__(self, max_words=30):
        self.max_words = max_words
        self._words = []         # Recent finalized words
        self._partial = []       # Words of the utterance still being recognized
        self._last_final = ""

    def add_partial(self, text):
        self._partial = text.split()

    def add_final(self, text):
        text = text.strip()
        if text == self._last_final:
            return
        self._last_final = text
        self._words = (self._words + text.split())[-self.max_words:]
        self._partial = []

    @property
    def text(self):
        return " ".join((self._words + self._partial)[-self.max_words:])
