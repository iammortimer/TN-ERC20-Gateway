from web3 import Web3
import sqlite3 as sqlite
import requests

def createdb():
    createHeightTable = '''
        CREATE TABLE IF NOT EXISTS heights (
            id integer PRIMARY KEY,
            chain text NOT NULL,
            height integer
        );
    '''
    createTunnelTable = '''
        CREATE TABLE IF NOT EXISTS tunnel (
            id integer PRIMARY KEY,
            sourceAddress text NOT NULL,
            targetAddress text NOT NULL
        );
    '''
    createTableExecuted = '''
        CREATE TABLE IF NOT EXISTS executed (
            id integer PRIMARY KEY,
            sourceAddress text NOT NULL,
            targetAddress text NOT NULL,
            tnTxId text NOT NULL,
            ethTxId text NOT NULL,
            timestamp timestamp
            default current_timestamp,
            amount real,
            amountFee real
    );
    '''
    createTableErrors = '''
        CREATE TABLE IF NOT EXISTS errors (
            id integer PRIMARY KEY,
            sourceAddress text ,
            targetAddress text ,
            tnTxId text ,
            ethTxId text ,
            timestamp timestamp
            default current_timestamp,
            amount real,
            error text,
            exception text
    );
    '''

    con = sqlite.connect('gateway.db')
    cursor = con.cursor()
    cursor.execute(createHeightTable)
    cursor.execute(createTunnelTable)
    cursor.execute(createTableExecuted)
    cursor.execute(createTableErrors)
    con.commit()
    con.close()

def initialisedb(config):
    #get current TN block:
    tnlatestBlock = requests.get(config['tn']['node'] + '/blocks/height').json()['height'] - 1

    #get current ETH block:
    if config['erc20']['node'].startswith('http'):
        w3 = Web3(Web3.HTTPProvider(config['erc20']['node']))
    else:
        w3 = Web3()

    ethlatestBlock = w3.eth.blockNumber

    con = sqlite.connect('gateway.db')
    cursor = con.cursor()
    cursor.execute('INSERT INTO heights ("chain", "height") VALUES ("ETH", ' + str(ethlatestBlock) + ')')
    cursor.execute('INSERT INTO heights ("chain", "height") VALUES ("TN", ' + str(tnlatestBlock) + ')')
    con.commit()
    con.close()
