"""Invoice exports."""
from dataclasses import dataclass


@dataclass
class Invoice:
    id: str
    customer_name: str
    total: float


HEADER = "id,customer_name,total"


def export_invoices_csv(invoices):
    lines = [HEADER]
    for inv in invoices:
        lines.append(",".join([inv.id, inv.customer_name, f"{inv.total:.2f}"]))
    return "\n".join(lines) + "\n"


def round_currency(value):
    return round(value, 2)
