from clara.llm.base import MockProvider
from clara.simplify import chunk_text, simplify
from clara.verify import verify


def test_chunk_groups_paragraphs_under_limit():
    text = "\n\n".join(f"Paragraph {i} " + "word " * 40 for i in range(6))
    chunks = chunk_text(text, max_chars=300)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
    joined = " ".join(chunks)
    assert all(f"Paragraph {i}" in joined for i in range(6))  # nothing lost


def test_oversized_paragraph_split_by_sentences():
    para = " ".join(f"Sentence number {i}." for i in range(50))
    assert len(chunk_text(para, max_chars=200)) > 1


class CountingProvider(MockProvider):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def complete(self, system, prompt, **kw):
        self.calls += 1
        return super().complete(system, prompt, **kw)


def test_long_text_makes_multiple_calls():
    text = "\n\n".join("Pay 100 dollars." + " filler" * 60 for _ in range(4))
    provider = CountingProvider()
    out = simplify(text, provider=provider, max_chars=400)
    assert provider.calls > 1          # not one truncatable call
    assert "100 dollars" in out        # content from the chunks survives


def test_short_text_single_call():
    provider = CountingProvider()
    simplify("Short text.", provider=provider)
    assert provider.calls == 1


def test_faithful_across_chunks():
    text = "\n\n".join(f"Item {i}: pay {i * 100} by 2024-0{i}-01." for i in range(1, 4))
    out = simplify(text, provider=MockProvider(), max_chars=40)
    assert verify(text, out).ok        # numbers and dates preserved across chunks
