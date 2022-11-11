#!/usr/bin/env python3
#coding: utf-8

'''Binance Exporter'''

import logging
import os
import hmac
import hashlib
import json
import sys
import time
from urllib.parse import urlencode
import requests
from prometheus_client.core import REGISTRY, Metric
from prometheus_client import start_http_server, PROCESS_COLLECTOR, PLATFORM_COLLECTOR

BINANCE_EXPORTER_NAME = os.environ.get('BINANCE_EXPORTER_NAME',
                                       'binance-exporter')
BINANCE_EXPORTER_LOGLEVEL = os.environ.get('BINANCE_EXPORTER_LOGLEVEL',
                                           'INFO').upper()

MANDATORY_ENV_VARS = ["BINANCE_KEY", "BINANCE_SECRET"]

# Logging Configuration
try:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level=BINANCE_EXPORTER_LOGLEVEL)
except ValueError:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level='INFO')
    logging.error("BINANCE_EXPORTER_LOGLEVEL invalid !")
    sys.exit(1)

# Check Mandatory Environment Variable
for var in MANDATORY_ENV_VARS:
    if var not in os.environ:
        logging.critical("%s environement variable must be set !", var)
        sys.exit(1)

BINANCE_KEY = os.environ.get('BINANCE_KEY')
BINANCE_SECRET = os.environ.get('BINANCE_SECRET')
BINANCE_API_ENDPOINT = "https://api.binance.com"

# Check BINANCE_EXPORTER_PORT
try:
    BINANCE_EXPORTER_PORT = int(os.environ.get('BINANCE_EXPORTER_PORT', '8123'))
except ValueError:
    logging.error("BINANCE_EXPORTER_PORT must be int !")
    sys.exit(1)

METRICS = [
    {'name': 'earn_wallet',
     'description': 'Binance Earn Wallet',
     'type': 'gauge',
     'key': 'totalAmount',
     'method': 'GET',
     'params': {},
     'labels': {'type': 'flexible'},
     'uri': '/sapi/v1/lending/daily/token/position'},
    {'name': 'earn_wallet',
     'description': 'Binance Earn Wallet',
     'type': 'gauge',
     'key': 'amount',
     'method': 'GET',
     'params': {'product': 'STAKING'},
     'labels': {'type': 'locked'},
     'uri': '/sapi/v1/staking/position'},
    {'name': 'earn_wallet',
     'description': 'Binance Earn Wallet',
     'type': 'gauge',
     'key': 'totalAmount',
     'method': 'GET',
     'params': {},
     'labels': {},
     'uri': '/sapi/v1/lending/daily/token/position'},
    {'name': 'funding_wallet',
     'description': 'Binance Funding Wallet',
     'type': 'gauge',
     'key': 'free',
     'method': 'POST',
     'params': {},
     'labels': {},
     'uri': '/sapi/v1/asset/get-funding-asset'},
    {'name': 'spot_wallet',
     'description': 'Binance Spot Wallet',
     'type': 'gauge',
     'key': 'free',
     'method': 'POST',
     'params': {},
     'labels': {},
     'uri': '/sapi/v3/asset/getUserAsset'}
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

class BinanceCollector():
    '''Binance Collector Class'''
    def __init__(self):
        pass

    @staticmethod
    def _timestamp():
        '''Get Binance Timestamp'''
        return json.loads(requests.get(f"{BINANCE_API_ENDPOINT}/api/v3/time").text)['serverTime']

    @staticmethod
    def _signature(data):
        '''Generate Binance Signature'''
        return hmac.new(BINANCE_SECRET.encode('utf-8'),
                        urlencode(data).encode('utf-8'),
                        hashlib.sha256).hexdigest()

    def api_call(self, method, uri, params):
        '''Do Binance API Call'''
        headers = {"X-MBX-APIKEY": BINANCE_KEY}
        timestamp = self._timestamp()
        data = {'timestamp': timestamp}
        data |= params
        signature = self._signature(data)
        data['signature'] = signature
        if method == 'GET':
            res = requests.get(f"{BINANCE_API_ENDPOINT}{uri}", headers=headers, params=data)
        elif method == 'POST':
            res = requests.post(f"{BINANCE_API_ENDPOINT}{uri}", headers=headers, params=data)
        else:
            logging.critical("Invalid HTTP Method !")
            sys.exit(1)
        if res.status_code != 200:
            logging.critical(res.text)
            sys.exit(1)
        logging.debug(res.text)
        return res.text

    def get_wallets(self):
        '''Get Binance Wallets'''
        res = []
        for metric in METRICS:
            wallet = json.loads(self.api_call(metric['method'], metric['uri'], metric['params']))
            for item in wallet:
                labels = {'job': BINANCE_EXPORTER_NAME, 'asset': item['asset']}
                labels |= metric['labels']
                description = metric['description']
                metric_type = metric['type']
                res.append({'name': f"binance_{metric['name'].lower()}",
                            'value': float(item[metric['key']]),
                            'description': description,
                            'type': metric_type,
                            'labels': labels
                           })
        logging.info(res)
        return res

    def collect(self):
        '''Collect Prometheus Metrics'''
        metrics = self.get_wallets()
        for metric in metrics:
            prometheus_metric = Metric(metric['name'], metric['description'], metric['type'])
            prometheus_metric.add_sample(metric['name'],
                                         value=metric['value'],
                                         labels=metric['labels'])
            yield prometheus_metric

def main():
    '''Main Function'''
    logging.info("Starting Binance Exporter on port %s.", BINANCE_EXPORTER_PORT)
    logging.debug("BINANCE_EXPORTER_PORT: %s.", BINANCE_EXPORTER_PORT)
    logging.debug("BINANCE_EXPORTER_NAME: %s.", BINANCE_EXPORTER_NAME)
    # Start Prometheus HTTP Server
    start_http_server(BINANCE_EXPORTER_PORT)
    # Init BinanceCollector
    REGISTRY.register(BinanceCollector())
    # Loop Infinity
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
