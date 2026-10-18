import csv
import io

from billing.export import Invoice, export_invoices_csv


def test_comma_in_name_round_trips():
    out = export_invoices_csv([Invoice("A1", "Acme, Inc.", 10)])
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[1] == ["A1", "Acme, Inc.", "10.00"]


def test_quote_in_name_round_trips():
    out = export_invoices_csv([Invoice("A2", 'Bob "The Builder"', 5)])
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[1] == ["A2", 'Bob "The Builder"', "5.00"]


def test_plain_rows_unchanged():
    out = export_invoices_csv([Invoice("A1", "Acme", 10)])
    assert out == "id,customer_name,total\nA1,Acme,10.00\n"
