from ggs_accounting.utils import format_currency, format_date, export_to_csv
import os
import csv
import datetime as dt

def test_format_currency_and_date():
    assert format_currency(1234.5).replace(',', '').startswith('₹') or format_currency(1234.5).startswith('1')
    assert format_date(dt.date(2024, 1, 2)) == '02-01-2024'

def test_export_to_csv(tmp_path):
    data = [{'a':1, 'b':2}, {'a':3, 'b':4}]
    file = tmp_path/'out.csv'
    export_to_csv(str(file), data, headers=['a','b'])
    with open(file, newline='') as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ['a','b']
    assert rows[1] == ['1','2']
