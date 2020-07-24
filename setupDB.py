import sqlite3 as sqlite
from tnClass import tnCalls
from otherClass import otherCalls

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
            targetAddress text NOT NULL,
            timestamp timestamp
            default current_timestamp,
            status text
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

def createVerify():
    createVerifyTable = '''
        CREATE TABLE IF NOT EXISTS verified (
            id integer PRIMARY KEY,
            chain text NOT NULL,
            tx text NOT NULL,
            block integer
        );
    '''
    con = sqlite.connect('gateway.db')
    cursor = con.cursor()
    cursor.execute(createVerifyTable)
    con.commit()
    con.close()

def updateExisting():
    try:
        sql = 'ALTER TABLE tunnel ADD COLUMN timestamp timestamp;'

        con = sqlite.connect('gateway.db')
        cursor = con.cursor()
        cursor.execute(sql)
        con.commit()

        sql = 'ALTER TABLE tunnel ADD COLUMN status text;'

        cursor = con.cursor()
        cursor.execute(sql)
        con.commit()

        sql = 'UPDATE tunnel SET status = "created"'

        cursor = con.cursor()
        cursor.execute(sql)
        con.commit()
        con.close()
    except:
        con.close()
        return

def initialisedb(config):
    #get current TN block:
    tnlatestBlock = tnCalls(config).currentBlock()

    #get current ETH block:
    ethlatestBlock = otherCalls(config).currentBlock()

    con = sqlite.connect('gateway.db')
    cursor = con.cursor()
    cursor.execute('INSERT INTO heights ("chain", "height") VALUES ("ETH", ' + str(ethlatestBlock) + ')')
    cursor.execute('INSERT INTO heights ("chain", "height") VALUES ("TN", ' + str(tnlatestBlock) + ')')
    con.commit()
    con.close()
