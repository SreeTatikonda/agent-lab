"""Pagination helpers for the product catalog."""
import math


def page_count(total_items, page_size):
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    return math.floor(total_items / page_size)


def paginate(items, page, page_size):
    """Return items for a 1-indexed page."""
    if page < 1:
        raise ValueError("page starts at 1")
    if page > page_count(len(items), page_size):
        return []
    start = (page - 1) * page_size
    return items[start:start + page_size]
