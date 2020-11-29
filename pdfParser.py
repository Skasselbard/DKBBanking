#!/usr/bin/python3

import os
import re
from pprint import pprint
from dateutil.parser import parse as parse_date
from dateutil.parser import parserinfo
from regx import amount_rx, long_date_rx, whitespace_rx, digit_rx, short_date_rx, entry_start_rx, entry_end_rx
from math import isclose

date_format = "%Y-%m-%d"


class Entry:
    booking_date = ""
    value_date = ""
    type = ""
    reference = ""
    amount = ""
    purpose = ""

    def __repr__(self):
        return \
            "buchung: " + self.booking_date.strftime(date_format) + \
            "\nwertstellung: " + self.value_date.strftime(date_format) + \
            "\ntype: " + self.type + \
            "\nreferenz: " + self.reference + \
            "\nbetrag: " + self.amount + \
            "\nbetreff: " + self.purpose

    def __init__(self, booking_date, value_date, ty, reference, amount, purpose):
        self.type = ty
        self.booking_date = parse_date(
            booking_date, parserinfo=parserinfo(True))
        self.value_date = parse_date(value_date, parserinfo=parserinfo(True))
        self.amount = amount
        self.reference = reference
        self.purpose = purpose

    def to_json(self, statement_number):
        value_date = self.value_date.strftime(date_format)
        booking_date = self.booking_date.strftime(date_format)
        json_body = {
            "measurement": "transaction",
            "tags": {
                "reference": self.reference,
                "type": self.type,
                "statement_number": statement_number,
                "purpose": self.purpose,
                "booking_date": booking_date
            },
            "time": value_date,
            "fields": {
                "value": float(self.amount),
            }
        }
        return json_body


class Document:
    filepath = None
    temp_file = 'tmp.txt'
    old_balance = None
    new_balance = None
    statement_number = None
    year = None
    table = 0
    is_first_entry = True
    from_date = None
    to_date = None

    # the alignment of the amounts (at wich column do they end)
    negative_end = None
    positive_end = None

    def get_entrys(self):
        entries = []
        lines = open(self.temp_file, 'r').readlines()
        for i, line in enumerate(lines):
            self.__check_amount_sign(line)
            if re.search(entry_start_rx(), line):
                entry = []
                # do not strip this line! (messes up the sign of amount)
                entry.append(line)
                j = i+1
                while (not re.search(entry_end_rx(), lines[j])) and lines[j] != "\n":
                    entry.append(lines[j].strip())
                    j += 1
                    # TODO: handle page breaks!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                formatted = self.__format_entry(entry)
                if not formatted == None:
                    entries.append(formatted)
                else:
                    # might be caused by edge case
                    if not self.is_first_entry:
                        raise ValueError("expected entry")
                self.is_first_entry = False  # next entry is not the first anymore
        self.__check_entries(entries)
        return entries

    def __check_entries(self, entries):
        # check if the entries add up to the new balance
        cumulation = sum([float(e.amount)
                          for e in entries]) + float(self.old_balance)
        if not isclose(cumulation, float(self.new_balance)):
            print(self.statement_number + "/" + self.year)
            print(self.old_balance)
            print([e.amount for e in entries])
            print(cumulation)
            print(self.new_balance)
            raise ValueError("entries do not sum up to new balance")

    def __init__(self, path):
        self.filepath = path
        os.system("pdftotext -layout " + self.filepath + " " + self.temp_file)
        self.old_balance = re.search(
            amount_rx(), self.__get_line("ALTER KONTOSTAND")).group()
        self.old_balance = self.old_balance.replace(".", "").replace(",", ".")
        self.new_balance = re.search(
            amount_rx(), self.__get_line("NEUER KONTOSTAND")).group()
        self.new_balance = self.new_balance.replace(".", "").replace(",", ".")
        stmt_data = self.__statement_data()
        self.statement_number = stmt_data["number"]
        self.year = stmt_data["year"]
        self.from_date = stmt_data["from_date"]
        self.to_date = stmt_data["to_date"]

    def __del__(self):
        os.remove(self.temp_file)

    def to_json(self):
        from_date = parse_date(
            self.from_date, parserinfo=parserinfo(True)).strftime(date_format)
        to_date = parse_date(self.to_date, parserinfo=parserinfo(
            True)).strftime(date_format)
        json_body = {
            "measurement": "statement",
            "tags": {
                "year": self.year,
                "statement_number": self.statement_number,
                "from_date": from_date
            },
            "time": to_date,
            "fields": {
                "old_balance": float(self.old_balance),
                "new_balance": float(self.new_balance),
            }
        }
        return json_body

    def __get_line(self, regex):
        lines = open(self.temp_file, 'r').readlines()
        for line in lines:
            if re.search(regex, line):
                return line

    def __check_amount_sign(self, reference_line):
        # reference_line is:
        # Bu.Tag  Wert  Wir haben für Sie gebucht    Belastung in EUR   Gutschrift in EUR
        if re.search("Belastung in EUR" + whitespace_rx() + "Gutschrift in EUR", reference_line):
            self.table += 1  # we have discovered a new table on a new page
            self.is_first_entry = True  # and the next entry is the first of the table
            self.negative_end = re.search(
                "Belastung in EUR", reference_line).end()
            self.positive_end = re.search(
                "Gutschrift in EUR", reference_line).end()

    def __format_entry(self, entry):
        # second column in the first line
        ty = entry[0].split()[2]
        # if amount is in the last column its positive
        # if amount is in the column before its positive
        amount = re.search(amount_rx(), entry[0])
        difference_to_negative = abs(amount.end() - self.negative_end)
        difference_to_positive = abs(amount.end() - self.positive_end)
        if min(difference_to_positive, difference_to_negative) >= 14:
            print(entry)
            raise ValueError("no amount found")
        if difference_to_negative < difference_to_positive:
            amount = "-" + amount.group()
        else:
            amount = amount.group()
        # format american styl number
        amount = amount.replace(".", "").replace(",", ".")
        # first date is booking date, the second is the value date
        dates = re.findall(short_date_rx(), entry[0])
        # third line and folowing are all purpose lines
        purpose = ""
        if len(entry) > 2:
            purpose = entry[2]
            for i in range(3, len(entry)):
                purpose = purpose + "\n" + entry[i].strip()
            purpose.strip()
        # second line is the reference
        e = Entry(dates[0] + self.year, dates[1] +
                  self.year, ty, entry[1], amount, purpose)
        self.__check_entry(e, difference_to_negative, difference_to_positive)
        return e

    def __check_entry(self, entry: Entry, difference_to_negative, difference_to_positive):
        if difference_to_positive >= 10 and difference_to_negative > 10:
            print(entry)
            raise ValueError("Column of amount has moved significantly")
        try:
            float(entry.amount)
        except Exception:
            print(open(self.temp_file, "r").read())
            raise ValueError(entry.__repr__)

    def __statement_data(self):
        # matches something like this: '001 / 2020'
        regex = digit_rx() + "{3,3}" + whitespace_rx() + \
            "/" + whitespace_rx() + digit_rx() + "{4,4}"
        data = re.search(regex, self.__get_line(
            "Kontoauszug Nummer")).group().split("/")
        dates = re.findall(long_date_rx(), self.__get_line(
            "Kontoauszug Nummer"))
        return {
            "number": data[0].strip(),
            "year": data[1].strip(),
            "from_date": dates[0],
            "to_date": dates[1]
        }


if __name__ == "__main__":
    doc = Document(
        '/home/tom/repos/banking/data/Kontoauszug_1015639444_Nr_2015_009_per_2015_09_04.pdf')
    entries = doc.get_entrys()
    # print(entries)
    print(len(entries))
