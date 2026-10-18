from billing.export import Invoice, export_invoices_csv, HEADER


def test_header_first():
    out = export_invoices_csv([])
    assert out.splitlines()[0] == HEADER


def test_simple_row():
    out = export_invoices_csv([Invoice("A1", "Acme", 10)])
    assert out.splitlines()[1] == "A1,Acme,10.00"
