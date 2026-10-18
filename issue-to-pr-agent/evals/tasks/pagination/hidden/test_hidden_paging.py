import pytest

from shop.paging import page_count, paginate


def test_partial_last_page_is_returned():
    assert paginate(list(range(7)), 2, 5) == [5, 6]


def test_page_count_rounds_up():
    assert page_count(7, 5) == 2
    assert page_count(10, 5) == 2
    assert page_count(0, 5) == 0


def test_past_end_is_empty():
    assert paginate(list(range(7)), 3, 5) == []


def test_bad_page_size():
    with pytest.raises(ValueError):
        page_count(3, 0)
