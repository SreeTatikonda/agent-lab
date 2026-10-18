from textkit.slug import slugify


def test_collapses_repeated_whitespace():
    assert slugify("Hello   World") == "hello-world"


def test_tabs_and_newlines():
    assert slugify("Hello\tBig\nWorld") == "hello-big-world"


def test_no_leading_or_trailing_dashes():
    assert slugify("  -Hello World!- ") == "hello-world"


def test_existing_dashes_collapse():
    assert slugify("a -- b") == "a-b"
