def amount_rx():
    return "(\d*\.)*\d*,\d*"


def dot_rx():
    return "\."


def or_rx():
    return "|"


def whitespace_rx():
    return "\s*"


def digit_rx():
    return "\d"


def word_rx():
    return "\S*"


def words_rx():
    return word_rx() + "( " + word_rx() + ")*"


def date_rx():
    return digit_rx() + digit_rx() + dot_rx() + digit_rx() + digit_rx() + dot_rx()


def entry_start_rx():
    return date_rx() + whitespace_rx() + date_rx() + whitespace_rx() + word_rx() + whitespace_rx() + amount_rx()


def entry_end_rx():
    return entry_start_rx() + or_rx() + "ALTER KONTOSTAND.*"


def statement_file_name():
    # Kontoauszug_$KTNR$_Nr_2020_003_per_2020_03_03.pdf
    return "Kontoauszug_" + digit_rx() + "*_Nr_" + digit_rx() + "{4,4}_" + digit_rx(
    ) + "{3,3}_per_" + digit_rx() + "{4,4}_"+digit_rx()+"{2,2}_"+digit_rx()+"{2,2}.pdf"
