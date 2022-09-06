#!/usr/bin/env python3
#coding: utf-8

'''Binance Exporter'''

import logging
import os
import sys
import time
from binance.spot import Spot
from binance.error import ClientError
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
        logging.error("%s environement variable must be set !", var)
        sys.exit(1)

BINANCE_KEY = os.environ.get('BINANCE_KEY')
BINANCE_SECRET = os.environ.get('BINANCE_SECRET')

# Check BINANCE_EXPORTER_PORT
try:
    BINANCE_EXPORTER_PORT = int(os.environ.get('BINANCE_EXPORTER_PORT', '8123'))
except ValueError:
    logging.error("BINANCE_EXPORTER_PORT must be int !")
    sys.exit(1)

METRICS = [
    {'name': 'free', 'description': 'Free Cryptocurrency Saving', 'type': 'gauge'},
    {'name': 'locked', 'description': 'Locked Cryptocurrency Saving', 'type': 'gauge'}
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

class BinanceCollector():
    '''Binance Collector Class'''
    def __init__(self):
        self.client = Spot(key=BINANCE_KEY, secret=BINANCE_SECRET)

    def get_balances(self):
        '''Get Binance Balances Account'''
        res = []
        try:
            balances = self.client.account()['balances']
            for balance in balances:
                for key in [i['name'] for i in METRICS]:
                    description = [i['description'] for i in METRICS if key == i['name']][0]
                    metric_type = [i['type'] for i in METRICS if key == i['name']][0]
                    res.append({'name': f'binance_balance_{key.lower()}',
                                'value': float(balance[key]),
                                'description': description,
                                'type': metric_type,
                                'labels': {'job': BINANCE_EXPORTER_NAME,
                                           'cryptocurrency': balance['asset']
                                          }
                                   })
            return res
        except ClientError as exception:
            logging.error("%s", exception.error_message)
            sys.exit(1)

    def collect(self):
        '''Collect Prometheus Metrics'''
        metrics = self.get_balances()
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
