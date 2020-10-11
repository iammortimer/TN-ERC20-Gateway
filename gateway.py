import re
import json
import datetime
import os
from typing import List, Optional
from pydantic import BaseModel

from verification import verifier
from dbClass import dbCalls
from dbPGClass import dbPGCalls
from otherClass import otherCalls
from tnClass import tnCalls
from etherscanClass import etherscanCalls

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
import uvicorn
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

class cHeights(BaseModel):
    TN: int
    Other: int

class cAdresses(BaseModel):
    sourceAddress: str
    targetAddress: str

class cExecResult(BaseModel):
    successful: bool

class cDustkey(BaseModel):
    successful: bool
    dustKey: int = None

class cFullInfo(BaseModel):
    chainName: str
    assetID: str
    tn_gateway_fee: float
    tn_network_fee: float
    tn_total_fee: float
    other_gateway_fee: float
    other_network_fee: float
    other_total_fee: float
    fee: float
    company: str
    email: str
    telegram: str
    recovery_amount: float
    recovery_fee: float
    otherHeight: int
    tnHeight: int
    tnAddress: str
    tnColdAddress: str
    otherAddress: str
    otherNetwork: str
    disclaimer: str
    tn_balance: int
    other_balance: int
    minAmount: float
    maxAmount: float
    type: str
    usageinfo: str

class cDepositWD(BaseModel):
    status: str
    tx: str
    block: str
    error: str

class cTx(BaseModel):
    sourceAddress: str
    targetAddress: str
    tnTxId: str
    OtherTxId: str
    TNVerBlock: int = 0
    OtherVerBlock: int = 0
    amount: float
    TypeTX: str
    Status: str

class cTxs(BaseModel):
    transactions: List[cTx] = []
    error: str = ""

class cFees(BaseModel):
    totalFees: float

class cHealth(BaseModel):
    status: str
    connectionTN: bool
    connectionOther: bool
    blocksbehindTN: int
    blockbehindOther: int
    balanceTN: float
    balanceOther: float
    numberErrors: int

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

with open('config_run.json') as json_file:
    config = json.load(json_file)

if config['main']['use-pg']:
    dbc = dbPGCalls(config)
else:
    dbc = dbCalls(config)

tnc = tnCalls(config, dbc)

if config['other']['etherscan-on']:
    otc = etherscanCalls(config, dbc)
else:
    otc = otherCalls(config, dbc)

checkit = verifier(config, dbc)

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, config["main"]["admin-username"])
    correct_password = secrets.compare_digest(credentials.password, config["main"]["admin-password"])
    if not (correct_username and correct_password):
        print("ERROR: invalid logon details")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def get_tnBalance():
    return tnc.currentBalance()

def get_otherBalance():
    return otc.currentBalance()


@app.get("/")
async def index(request: Request):
    heights = await getHeights()
    index = config['main']['index-file']
    if index == "": index = "index.html"
    return templates.TemplateResponse(index, {"request": request, 
                                                     "chainName": config['main']['name'],
                                                     "assetID": config['tn']['assetId'],
                                                     "tn_gateway_fee":config['tn']['gateway_fee'],
                                                     "tn_network_fee":config['tn']['network_fee'],
                                                     "tn_total_fee":config['tn']['network_fee']+config['tn']['gateway_fee'],
                                                     "eth_gateway_fee":config['other']['gateway_fee'],
                                                     "eth_network_fee":config['other']['network_fee'],
                                                     "eth_total_fee":config['other']['network_fee'] + config['other']['gateway_fee'],
                                                     "fee": config['tn']['fee'],
                                                     "company": config['main']['company'],
                                                     "email": config['main']['contact-email'],
                                                     "telegram": config['main']['contact-telegram'],
                                                     "recovery_amount":config['main']['recovery_amount'],
                                                     "recovery_fee":config['main']['recovery_fee'],
                                                     "ethHeight": heights['Other'],
                                                     "tnHeight": heights['TN'],
                                                     "tnAddress": config['tn']['gatewayAddress'],
                                                     "ethAddress": config['other']['gatewayAddress'],
                                                     "disclaimer": config['main']['disclaimer']})

@app.get('/heights', response_model=cHeights)
async def getHeights():
    result = dbc.getHeights()
    
    return {'TN': result[1][1], 'Other': result[0][1]}

@app.get('/errors')
async def getErrors(request: Request, username: str = Depends(get_current_username)):
    if (config["main"]["admin-username"] == "admin" and config["main"]["admin-password"] == "admin"):
        return {"message": "change the default username and password please!"}
    
    if username == config["main"]["admin-username"]:
        print("INFO: displaying errors page")
        result = dbc.getErrors()
        return templates.TemplateResponse("errors.html", {"request": request, "errors": result})

@app.get('/executed')
async def getExecuted(request: Request, username: str = Depends(get_current_username)):
    if (config["main"]["admin-username"] == "admin" and config["main"]["admin-password"] == "admin"):
        return {"message": "change the default username and password please!"}
    
    if username == config["main"]["admin-username"]:
        print("INFO: displaying executed page")
        result = dbc.getExecutedAll()
        result2 = dbc.getVerifiedAll()
        return templates.TemplateResponse("tx.html", {"request": request, "txs": result, "vtxs": result2})

@app.get('/ethAddress/{address}', response_model=cAdresses)
async def checkTunnel(address: str):
    address = re.sub('[\W_]+', '', address)

    result = dbc.getTargetAddress(address)
    if len(result) == 0:
        targetAddress = ""
    else:
        targetAddress = result

    return cAdresses(sourceAddress=address, targetAddress=targetAddress)

#TODO: rewrite to post
@app.get('/tunnel/{sourceAddress}/{targetAddress}', response_model=cExecResult)
async def createTunnel(sourceAddress: str, targetAddress: str):
    sourceAddress = re.sub('[\W_]+', '', sourceAddress)
    targetAddress = re.sub('[\W_]+', '', targetAddress)

    if not tnc.validateAddress(targetAddress):
        return {'successful': False}

    if not otc.validateAddress(sourceAddress):
        return { 'successful': False }

    sourceAddress = otc.normalizeAddress(sourceAddress)

    result = dbc.getTargetAddress(sourceAddress)
    if len(result) == 0:
        dbc.insTunnel("created", sourceAddress, targetAddress)
        print("INFO: tunnel created")
        return { 'successful': True }
    else:
        if result != targetAddress:
            return { 'successful': False }
        else: 
            return { 'successful': True }

#TODO: rewrite to post
@app.get('/dustkey/{targetAddress}', response_model=cDustkey)
async def createTunnelDK(targetAddress: str):
    if not tnc.validateAddress(targetAddress):
        return {'successful': False}

    sourceAddress = str(round(datetime.datetime.now().timestamp()))
    sourceAddress = sourceAddress[-6:]

    result = dbc.getTargetAddress(sourceAddress)
    if len(result) == 0:
        result = dbc.getSourceAddress(targetAddress)

        if len(result) == 0:
            dbc.insTunnel("created", sourceAddress, targetAddress)
            print("INFO: tunnel created - dustkey")

            return { 'successful': True, 'dustkey': sourceAddress}
        else:
            return { 'successful': True, 'dustkey': result }
    else:
        result = dbc.getSourceAddress(targetAddress)
        if len(result) == 0:
            return { 'successful': False }
        else: 
            return { 'successful': True, 'dustkey': result }

@app.get("/api/fullinfo", response_model=cFullInfo)
async def api_fullinfo():
    heights = await getHeights()
    tnBalance = get_tnBalance()
    otherBalance = get_otherBalance()
    return {"chainName": config['main']['name'],
            "assetID": config['tn']['assetId'],
            "tn_gateway_fee":config['tn']['gateway_fee'],
            "tn_network_fee":config['tn']['network_fee'],
            "tn_total_fee":config['tn']['network_fee']+config['tn']['gateway_fee'],
            "other_gateway_fee":config['other']['gateway_fee'],
            "other_network_fee":config['other']['network_fee'],
            "other_total_fee":config['other']['network_fee'] + config['other']['gateway_fee'],
            "fee": config['tn']['fee'],
            "company": config['main']['company'],
            "email": config['main']['contact-email'],
            "telegram": config['main']['contact-telegram'],
            "recovery_amount":config['main']['recovery_amount'],
            "recovery_fee":config['main']['recovery_fee'],
            "otherHeight": heights['Other'],
            "tnHeight": heights['TN'],
            "tnAddress": config['tn']['gatewayAddress'],
            "tnColdAddress": config['tn']['coldwallet'],
            "otherAddress": config['other']['gatewayAddress'],
            "otherNetwork": config['other']['network'],
            "disclaimer": config['main']['disclaimer'],
            "tn_balance": tnBalance,
            "other_balance": otherBalance,
            "minAmount": config['main']['min'],
            "maxAmount": config['main']['max'],
            "type": "tunnel",
            "usageinfo": ""}

@app.get("/api/deposit/{tnAddress}", response_model=cDepositWD)
async def api_depositCheck(tnAddress:str):
    result = checkit.checkTX(targetAddress=tnAddress)

    return result

@app.get("/api/wd/{tnAddress}", response_model=cDepositWD)
async def api_wdCheck(tnAddress: str):
    result = checkit.checkTX(sourceAddress=tnAddress)

    return result

@app.get("/api/checktxs/{tnAddress}", response_model=cTxs)
async def api_checktxs(tnAddress: str):
    if not tnc.validateAddress(tnAddress):
        temp = cTxs(error='invalid address')
    else:
        result = dbc.checkTXs(address=tnAddress)

        if 'error' in result:
            temp = cTxs(error=result['error'])
        else:
            temp = cTxs(transactions=result)
            
    return temp

@app.get("/api/checktxs", response_model=cTxs)
async def api_checktxs():
    result = dbc.checkTXs(address='')

    if 'error' in result:
        temp = cTxs(error=result['error'])
    else:
        temp = cTxs(transactions=result)

    return temp

@app.get('/api/fees/{fromdate}/{todate}', response_model=cFees)
async def api_getFees(fromdate: str, todate: str):
    return dbc.getFees(fromdate, todate)

@app.get('/api/fees/{fromdate}', response_model=cFees)
async def api_getFees(fromdate: str):
    return dbc.getFees(fromdate, '')

@app.get('/api/fees', response_model=cFees)
async def api_getFees():
    return dbc.getFees('','')

@app.get('/api/health', response_model=cHealth)
async def api_getHealth():
    return checkit.checkHealth()
