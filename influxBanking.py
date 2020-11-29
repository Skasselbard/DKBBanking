#!/bin/python3

from pdfParser import Document
from influxdb import InfluxDBClient
from pdfParser import Document, Entry
from pprint import pprint
import re
from regx import statement_file_name
import os
import argparse

global host
global port
global user
global password
global db
global ssl
global path
host = "localhost"
port = 8086
user = "root"
password = "root"
db = "test"
ssl = False
path = "./"


def get_client():
    client = InfluxDBClient(host, port, database=db,
                            username=user, password=password, ssl=ssl)
    client.create_retention_policy(
        'Infinite', 'INF', 1, default=True)
    return client


def check_database():
    c = InfluxDBClient(host, port, database=None,
                       username=user, password=password, ssl=ssl)
    if not list(filter(
        lambda database: database['name'] == db, c.get_list_database()
    )):
        print("Creating missing Database")
        c.create_database(db)


def write_konto_entries(document):
    entries = []
    for entry in document.get_entrys():
        entries.append(entry.to_json(document.statement_number))
    get_client().write_points(entries)


def drop_dbs():
    client = InfluxDBClient(host, port, database=None,
                            username=user, password=password, ssl=ssl)
    db_list = client.get_list_database()
    for db in db_list:
        client.drop_database(db['name'])


def parse_and_write(folder, file_pattern=None):
    client = get_client()
    first_year = None
    first_statement_number = None
    first_from_date = None
    first_balance = "0,00"
    if file_pattern == None:
        file_pattern = statement_file_name()
    for file in os.listdir(folder):
        file = os.path.join(folder, file)
        if re.search(file_pattern, file):
            doc = Document(file)
            write_konto_entries(doc)
            # remember the chronologically first document for an initial balance
            if first_year == None or doc.year < first_year or (first_year == doc.year and doc.statement_number < first_statement_number):
                first_year = doc.year
                first_statement_number = doc.statement_number
                first_from_date = doc.from_date
                first_balance = doc.old_balance
            client.write_points([doc.to_json()])
            del doc
    initial_entry = Entry(first_from_date, first_from_date,
                          "Startkapital", "startkapital", first_balance, "")
    client.write_points([initial_entry.to_json(first_statement_number)])


if __name__ == "__main__":
    # TODO: following client parameters are missing:
    # verify_ssl=False, timeout=None, retries=3, use_udp=False, udp_port=4444, proxies=None, pool_size=10, path='', cert=None, gzip=False, session=None, headers=None
    parser = argparse.ArgumentParser(
        description="Parse a set of statement files of the DKB AG and export the entries to an influxdb server")
    parser.add_argument(
        '-rm', '--delete', action="store_true", help="Delete all entries before inserting the new ones")
    parser.add_argument(
        '-l', '--path', help="Path to the statement files that should be parsed. The file names of the statement files are expected to be DKB default names.")
    parser.add_argument(
        '--host', help="Hostname or hostaddress of the influxdb server")
    parser.add_argument(
        '-p', '--port', help="Port on which the influxdb server is listening")
    parser.add_argument(
        '-u', '--user', help="Username for the influxdb server")
    parser.add_argument(
        '-pw', '--password', help="Password for the influxdb server")
    parser.add_argument(
        '-d', '--db', help="Name of the influxdb database to use")
    parser.add_argument(
        '-s', '--ssl', action="store_true", help="Use an ssl connection")

    args = parser.parse_args()

    ssl = args.ssl
    if args.path:
        path = args.path
    if args.host:
        host = args.host
    if args.port:
        port = args.port
    if args.user:
        user = args.user
    if args.password:
        password = args.password
    if args.db:
        db = args.db

    if args.delete:
        drop_dbs()
    check_database()
    parse_and_write(path)
