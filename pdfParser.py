#!/usr/bin/python3

import os
import re
from typing import List
from pprint import pprint

filepath = 'data/Kontoauszug_1015639444_Nr_2020_003_per_2020_03_03.pdf'
tempFile = 'tmp.txt'

# the alignment of the amounts (at wich column do they end)
negative_end = None
positive_end = None


class Entry:
    buchung = ""
    wertstellung = ""
    type = ""
    referenz = ""
    betrag = ""

    def __repr__(self):
        return \
            "buchung: " + self.buchung + \
            "\nwertstellung: " + self.wertstellung + \
            "\ntype: " + self.type + \
            "\nreferenz: " + self.referenz + \
            "\nbetrag: " + self.betrag


def amount():
    return "(\d*\.)*\d*,\d*"


def dot():
    return "\."


def orr():
    return "|"


def whitespace():
    return "\s*"


def digit():
    return "\d"


def word():
    return "\S*"


def words():
    return word() + "( " + word() + ")*"


def date():
    return digit() + digit() + dot() + digit() + digit() + dot()


def entry_start():
    return date() + whitespace() + date() + whitespace() + word() + whitespace() + amount()


def entry_end():
    return entry_start() + orr() + "ALTER KONTOSTAND.*"


def get_line(regex):
    lines = open(tempFile, 'r').readlines()
    for line in lines:
        if re.search(regex, line):
            return line

# referenze_line is:
# Bu.Tag  Wert  Wir haben für Sie gebucht    Belastung in EUR   Gutschrift in EUR


def check_amount_sign(referenze_line):
    if re.search("Belastung in EUR" + whitespace() + "Gutschrift in EUR", referenze_line):
        global negative_end
        global positive_end
        negative_end = re.search("Belastung in EUR", referenze_line).end()
        positive_end = re.search("Gutschrift in EUR", referenze_line).end()


def get_entrys():
    entries = []
    lines = open(tempFile, 'r').readlines()
    for i, line in enumerate(lines):
        check_amount_sign(line)
        if re.search(entry_start(), line):
            entry = []
            # do not strip this line! (messes up the sign of amount)
            entry.append(line)
            j = i+1
            while (not re.search(entry_end(), lines[j])) and lines[j].strip() != "\n":
                entry.append(lines[j].strip())
                j += 1
            entries.append(format_entry(entry))
    return entries


def format_entry(entry):
    formated = Entry()
    betrag = re.search(amount(), entry[0])
    if betrag.end() == negative_end:
        betrag = "-" + betrag.group()
    else:
        betrag = betrag.group()
    formated.betrag = betrag
    formated.referenz = entry[1]
    return formated


def old_balance(lines):
    return re.search(amount(), get_line("ALTER KONTOSTAND")).group()


def new_balance(lines):
    return re.search(amount(), get_line("NEUER KONTOSTAND")).group()


os.system("pdftotext -layout " + filepath + " " + tempFile)
lines = open(tempFile, 'r').readlines()
print(old_balance(lines))
print(new_balance(lines))
entries = get_entrys()
pprint(entries)
print(len(entries))

# TODO: remove tmp
# os.remove(tempFile)
