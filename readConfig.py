#!/bin/python3

import configparser


def initConfig():
    config = configparser.ConfigParser()
    config.read('cridentials.ini')
    config.sections()
    return config

def dbhost():
    config = initConfig()
    return config['Database']['host']


def dbport():
    config = initConfig()
    return config['Database']['port']


def dbname():
    config = initConfig()
    return config['Database']['dbName']
