"""URL slugs for article titles."""
import re


def slugify(title):
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = s.replace(" ", "-")
    return s
