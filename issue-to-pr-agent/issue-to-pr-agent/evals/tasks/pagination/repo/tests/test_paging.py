from shop.paging import paginate


def test_first_page():
    assert paginate(list(range(10)), 1, 5) == [0, 1, 2, 3, 4]
