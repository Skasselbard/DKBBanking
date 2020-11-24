#!/bin/python3

from pdfParser import Document
import readConfig
from dateutil.parser import parse
from influxdb import InfluxDBClient
from influxdb import SeriesHelper
from pdfParser import Document, Entry
from pprint import pprint
import re
from regx import statement_file_name
import os


def get_client():
    #TODO: username and password
    client = InfluxDBClient(readConfig.dbhost(),
                            readConfig.dbport(), database=readConfig.dbname())
    client.create_retention_policy(
        'Infinite', 'INF', 1, default=True)
    return client


def check_database():
    c = InfluxDBClient(readConfig.dbhost(), readConfig.dbport())
    if not list(filter(
        lambda database: database['name'] == readConfig.dbname(
        ), c.get_list_database()
    )):
        print("Creating missing Database")
        c.create_database(readConfig.dbname())


def write_konto_entries(document):
    check_database()
    entries = []
    for entry in document.get_entrys():
        entries.append(entry.to_influx_json(document.statement_number))
    get_client().write_points(entries)


def drop_dbs():
    client = InfluxDBClient(readConfig.dbhost(), readConfig.dbport())
    db_list = client.get_list_database()
    for db in db_list:
        client.drop_database(db['name'])


def parse_and_write(folder, file_pattern=None):
    if file_pattern == None:
        file_pattern = statement_file_name()
    for file in os.listdir(folder):
        file = os.path.join(folder, file)
        if re.search(file_pattern, file):
            doc = Document(file)
            write_konto_entries(doc)
            del doc


# drop_dbs()
parse_and_write("./data")


# query = getClient().query('SELECT * FROM "transaction"')
# pprint(query)
