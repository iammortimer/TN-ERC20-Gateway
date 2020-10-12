# TN <-> ERC20 Platform Gateway Framework

Inspired by Hawky's Waves-ERC20 Gateway: https://github.com/PyWaves/Waves-ERC20-Gateway
But rewritten to be published under FOSS license.

This framework allows to easily establish a gateway between any ERC20 token and the
TN Platform.
## Installation
Clone this repository and edit the config.json file according to your needs. Install the dependencies in requirements.txt via:
```
pip3 install -r requirements.txt
```
via pip and run the gateway by
```
python3 start.py
```
## Configuration of the config file
The config.json file includes all necessary settings that need to be configured in order to run a proper gateway:
```
{
    "main": {
        "port": <port number to run the webinterface on>,
        "name": "Tokenname",
        "company": "Gateways Ltd",
        "contact-email": "info@contact.us",
        "contact-telegram": "https://t.me/TurtleNetwork",
        "recovery_amount": <minimum recovery amount>,
        "recovery_fee": <recovery fee in %>,
        "admin-username": "admin",
        "admin-password": "admin",
        "disclaimer": "link to disclaimer file online",
        "min": <minimum amount>,
        "max": <maximum amount>,
        "index-file": "name of the index.html to use, if left blank index.html will be used",
        "db-location": "directory name if the db file is not in the main directory"
        "use-pg": <true or false, depending on if you want to use a postGres DB instead of sqlite>
    },
    "postgres": {
        "pguser": "",
        "pgpswd": "",
        "pghost": "",
        "pgport": 5432
    },
    "other": {
        "node": "<the eth node you want to connect to>",
        "contract": {
            "address": "<the address of the contract for the token>",
            "decimals": <number of decimals of the token>
        },
        "gatewayAddress": "<ETH address of the gateway>",
        "privateKey": "<privatekey of the above devined address>",
        "coldwallet": "<ETH address of the gateway's cold wallet (if in use)>",
        "seedenvname" : "<the ENV name to store your private key instead of the field above>",
        "fee": <the total fee you want to collect on the gateway, calculated in the proxy token, e.g., 0.1>,
        "gas": <the amount of gas used for each transaction on the ETH network>,
        "gasprice" : <the gasprice in gwei or set to 0 for automatic gasprice determination>,
        "gateway_fee": <the gatewway part of the fee calculated in the proxy token, e.g., 0.1>,
        "network_fee": <the tx part of the fee calculated in the proxy token, e.g., 0.1>,
        "timeInBetweenChecks": <seconds in between a check for a new block>,
        "confirmations": <number of confirmations necessary in order to accept a transaction>,
        "etherscan-on": <true or false, depending on if you want to use etherscan instead of a normal eth node for most calls>,
        "etherscan-apikey": <etherscan apikey, required if you want to use etherscan alternative>,
        "network": "Ethereum"
    },
    "tn": {
        "gatewayAddress": "<TN address of the gateway>",
        "gatewaySeed": "<seed of the above devined address>",
        "coldwallet": "<TN address of the gateway's cold wallet (if in use)>",
        "seedenvname" : "<the ENV name to store your seed instead of the field above>",
        "fee": <the fee you want to collect on the gateway, calculated in the proxy token, e.g., 0.1>,
        "gateway_fee": <the gatewway part of the fee calculated in the proxy token, e.g., 0.1>,
        "network_fee": <the tx part of the fee calculated in the proxy token, e.g., 0.1>,
        "assetId": "<the asset id of the proxy token on the TN platform>",
        "decimals": <number of decimals of the token>,
        "network": "<Waves network you want to connect to (testnet|mainnet)>",
        "node": "<the TN node you want to connect to>",
        "timeInBetweenChecks": <seconds in between a check for a new block>,
        "confirmations": <number of confirmations necessary in order to accept a transaction>
    }
}
```

## Running the gateway
After starting the gateway, it will provide a webpage on the port set in config.json.

## Usage of the gateway
This is a simple gateway for TN tokens to the ERC20 Platform and vice versa. For sending tokens from the Etherium Platform to the TN blockchain, fill in your source ETH wallet address and the receiving Turtle Network wallet to create a tunnel. Then send the tokens to the Ethereum address of the gateway.

For sending tokens from the TN Platform to the Etherium blockchain, just add the Etherium address that should receive the tokens as the description of the transfer and send the tokens to the TN address of the gateway.

## Management interface
After starting the gateway, there are also a couple of management interfaces which are secured by the admin-username and admin-password fields in the config.json:
```
    /errors: This will show an overview of detected errors during processing of blocks or transferring funds
    /executed: This will show an overview of executed transactions through the gateway
    /docs: Swagger documentation for included API calls
```

# Disclaimer
USE THIS FRAMEWORK AT YOUR OWN RISK!!! FULL RESPONSIBILITY FOR THE SECURITY AND RELIABILITY OF THE FUNDS TRANSFERRED IS WITH THE OWNER OF THE GATEWAY!!!
