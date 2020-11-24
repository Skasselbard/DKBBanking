#!/usr/bin/python3

import os
import re
from pprint import pprint
from dateutil.parser import parse as parse_date
from dateutil.parser import parserinfo
from regx import amount_rx, whitespace_rx, digit_rx, date_rx, entry_start_rx, entry_end_rx

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

    def to_influx_json(self, statement_number):
        value_date = self.value_date.strftime(date_format)
        booking_date = self.booking_date.strftime(date_format)
        json_body = {
            "measurement": "transaction",
            "tags": {
                "value": float(self.amount),
                "purpose": self.purpose,
                "statement_number": statement_number,
            },
            "time": value_date,
            "fields": {
                "reference": self.reference,
                "type": self.type,
                "booking_date": booking_date
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

    # the alignment of the amounts (at wich column do they end)
    negative_end = None
    positive_end = None

    def get_entrys(self):
        self.__statement_data()
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
                entries.append(self.__format_entry(entry))
        return entries

    def __init__(self, path):
        self.filepath = path
        os.system("pdftotext -layout " + self.filepath + " " + self.temp_file)
        self.old_balance = re.search(
            amount_rx(), self.__get_line("ALTER KONTOSTAND")).group()
        self.new_balance = re.search(
            amount_rx(), self.__get_line("NEUER KONTOSTAND")).group()
        self.statement_number = self.__statement_data()[0]
        self.year = self.__statement_data()[1]

    def __del__(self):
        os.remove(self.temp_file)

    def __get_line(self, regex):
        lines = open(self.temp_file, 'r').readlines()
        for line in lines:
            if re.search(regex, line):
                return line

    def __check_amount_sign(self, reference_line):
        # reference_line is:
        # Bu.Tag  Wert  Wir haben für Sie gebucht    Belastung in EUR   Gutschrift in EUR
        if re.search("Belastung in EUR" + whitespace_rx() + "Gutschrift in EUR", reference_line):
            self.negative_end = re.search(
                "Belastung in EUR", reference_line).end()
            self.positive_end = re.search(
                "Gutschrift in EUR", reference_line).end()

    def __format_entry(self, entry):
        # second column in the first line
        ty = entry[0].split()[2]
        # if its in the last column its positive
        # if its in the column before its positive
        amount = re.search(amount_rx(), entry[0])
        if amount.end() == self.negative_end:
            amount = "-" + amount.group()
        else:
            amount = amount.group()
        # format american styl number
        amount = amount.replace(".", "").replace(",", ".")
        # first date is booking date, the second is the value date
        dates = re.findall(date_rx(), entry[0])
        # third line and folowing are all purpose lines
        purpose = ""
        for i in range(2, len(entry)):
            purpose = purpose + " " + entry[i].strip()
        purpose.strip()
        # second line is the reference
        return Entry(dates[0] + self.year, dates[1] + self.year, ty, entry[1], amount, purpose)

    def __statement_data(self):
        # matches something like this: '001 / 2020'
        regex = digit_rx() + "{3,3}" + whitespace_rx() + \
            "/" + whitespace_rx() + digit_rx() + "{4,4}"
        data = re.search(regex, self.__get_line(
            "Kontoauszug Nummer")).group().split("/")
        return [data[0].strip(), data[1].strip()]


# doc = Document('data/Kontoauszug_1015639444_Nr_2020_003_per_2020_03_03.pdf')
# print(doc.get_entrys())
