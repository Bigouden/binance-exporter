#!/usr/bin/env python3
# coding: utf-8
# pyright: reportMissingImports=false, reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false, reportArgumentType=false

"""Binance Exporter"""

import hashlib
import hmac
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable
from urllib.parse import urlencode
from wsgiref.simple_server import make_server

import pytz
import requests
from prometheus_client import PLATFORM_COLLECTOR, PROCESS_COLLECTOR
from prometheus_client.core import REGISTRY, CollectorRegistry, Metric
from prometheus_client.exposition import _bake_output, _SilentHandler, parse_qs

BINANCE_EXPORTER_NAME = os.environ.get("BINANCE_EXPORTER_NAME", "binance-exporter")
BINANCE_EXPORTER_LOGLEVEL = os.environ.get("BINANCE_EXPORTER_LOGLEVEL", "INFO").upper()
BINANCE_EXPORTER_TZ = os.environ.get("TZ", "Europe/Paris")

MANDATORY_ENV_VARS = ["BINANCE_KEY", "BINANCE_SECRET"]


def make_wsgi_app(
    registry: CollectorRegistry = REGISTRY, disable_compression: bool = False
) -> Callable:
    """Create a WSGI app which serves the metrics from a registry."""

    def prometheus_app(environ, start_response):
        # Prepare parameters
        accept_header = environ.get("HTTP_ACCEPT")
        accept_encoding_header = environ.get("HTTP_ACCEPT_ENCODING")
        params = parse_qs(environ.get("QUERY_STRING", ""))
        headers = [
            ("Server", ""),
            ("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
            ("X-Content-Type-Options", "nosniff"),
            ("Cross-Origin-Resource-Policy", "same-origin"),
            ("Cross-Origin-Embedder-Policy", "require-corp"),
            ("Cross-Origin-Opener-Policy", "same-site"),
        ]
        if environ["PATH_INFO"] == "/":
            status = "301 Moved Permanently"
            headers.append(("Location", "/metrics"))
            output = b""
        elif environ["PATH_INFO"] == "/favicon.ico":
            status = "200 OK"
            output = b""
        elif environ["PATH_INFO"] == "/metrics":
            status, tmp_headers, output = _bake_output(
                registry,
                accept_header,
                accept_encoding_header,
                params,
                disable_compression,
            )
            headers += tmp_headers
        else:
            status = "404 Not Found"
            output = b""
        start_response(status, headers)
        return [output]

    return prometheus_app


def start_wsgi_server(
    port: int,
    addr: str = "0.0.0.0",  # nosec B104
    registry: CollectorRegistry = REGISTRY,
) -> None:
    """Starts a WSGI server for prometheus metrics as a daemon thread."""
    app = make_wsgi_app(registry)
    httpd = make_server(addr, port, app, handler_class=_SilentHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()


start_http_server = start_wsgi_server

# Logging Configuration
try:
    pytz.timezone(BINANCE_EXPORTER_TZ)
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone(BINANCE_EXPORTER_TZ)
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level=BINANCE_EXPORTER_LOGLEVEL,
    )
except pytz.exceptions.UnknownTimeZoneError:
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone("Europe/Paris")
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("TZ invalid : %s !", BINANCE_EXPORTER_TZ)
    os._exit(1)
except ValueError:
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("BINANCE_EXPORTER_LOGLEVEL invalid !")
    os._exit(1)

# Check Mandatory Environment Variable
for var in MANDATORY_ENV_VARS:
    if var not in os.environ:
        logging.critical("%s environment variable must be set !", var)
        os._exit(1)

BINANCE_KEY = os.environ.get("BINANCE_KEY")
BINANCE_SECRET = os.environ.get("BINANCE_SECRET")
BINANCE_API_ENDPOINT = "https://api.binance.com"

# Check BINANCE_EXPORTER_PORT
try:
    BINANCE_EXPORTER_PORT = int(os.environ.get("BINANCE_EXPORTER_PORT", "8123"))
except ValueError:
    logging.error("BINANCE_EXPORTER_PORT must be int !")
    os._exit(1)

METRICS = [
    {
        "name": "earn_wallet",
        "description": "Binance Earn Wallet",
        "type": "gauge",
        "key": "totalAmount",
        "method": "GET",
        "params": {},
        "labels": {"type": "flexible"},
        "uri": "/sapi/v1/simple-earn/flexible/position",
    },
    {
        "name": "earn_wallet",
        "description": "Binance Earn Wallet",
        "type": "gauge",
        "key": "amount",
        "method": "GET",
        "params": {},
        "labels": {"type": "locked"},
        "uri": "/sapi/v1/simple-earn/locked/position",
    },
    {
        "name": "funding_wallet",
        "description": "Binance Funding Wallet",
        "type": "gauge",
        "key": "free",
        "method": "POST",
        "params": {},
        "labels": {},
        "uri": "/sapi/v1/asset/get-funding-asset",
    },
    {
        "name": "spot_wallet",
        "description": "Binance Spot Wallet",
        "type": "gauge",
        "key": "free",
        "method": "POST",
        "params": {},
        "labels": {},
        "uri": "/sapi/v3/asset/getUserAsset",
    },
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors["python_gc_objects_collected_total"])


class BinanceCollector:
    """Binance Collector Class"""

    def __init__(self):
        pass

    @staticmethod
    def _timestamp():
        """Get Binance Timestamp"""
        return json.loads(
            requests.get(f"{BINANCE_API_ENDPOINT}/api/v3/time", timeout=2).text
        )["serverTime"]

    @staticmethod
    def _signature(data):
        """Generate Binance Signature"""
        return hmac.new(
            BINANCE_SECRET.encode("utf-8"),
            urlencode(data).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def api_call(self, method, uri, params):
        """Do Binance API Call"""
        headers = {"X-MBX-APIKEY": BINANCE_KEY}
        timestamp = self._timestamp()
        data = {"timestamp": timestamp}
        data |= params
        signature = self._signature(data)
        data["signature"] = signature
        res = None
        if method == "GET":
            res = requests.get(
                f"{BINANCE_API_ENDPOINT}{uri}", headers=headers, params=data, timeout=2
            )
        elif method == "POST":
            res = requests.post(
                f"{BINANCE_API_ENDPOINT}{uri}", headers=headers, params=data, timeout=2
            )
        else:
            logging.critical("Invalid HTTP Method !")
            os._exit(1)
        if res.status_code != 200:
            logging.critical("%s (uri: %s)", res.text, uri)
            os._exit(1)
        logging.debug(res.text)
        return res.text

    def get_wallets(self):
        """Get Binance Wallets"""
        res = []
        for metric in METRICS:
            wallet = json.loads(
                self.api_call(metric["method"], metric["uri"], metric["params"])
            )
            if "simple-earn" in metric["uri"]:
                wallet = wallet["rows"]
            for item in wallet:
                labels = {"job": BINANCE_EXPORTER_NAME, "asset": item["asset"]}
                labels |= metric["labels"]
                description = metric["description"]
                metric_type = metric["type"]
                res.append(
                    {
                        "name": f"binance_{metric['name'].lower()}",
                        "value": float(item[metric["key"]]),
                        "description": description,
                        "type": metric_type,
                        "labels": labels,
                    }
                )
        logging.info(res)
        return res

    def collect(self):
        """Collect Prometheus Metrics"""
        metrics = self.get_wallets()
        for metric in metrics:
            prometheus_metric = Metric(
                metric["name"], metric["description"], metric["type"]
            )
            prometheus_metric.add_sample(
                metric["name"], value=metric["value"], labels=metric["labels"]
            )
            yield prometheus_metric


def main():
    """Main Function"""
    logging.info("Starting Binance Exporter on port %s.", BINANCE_EXPORTER_PORT)
    logging.debug("BINANCE_EXPORTER_PORT: %s.", BINANCE_EXPORTER_PORT)
    logging.debug("BINANCE_EXPORTER_NAME: %s.", BINANCE_EXPORTER_NAME)
    # Start Prometheus HTTP Server
    start_http_server(BINANCE_EXPORTER_PORT)
    # Init BinanceCollector
    REGISTRY.register(BinanceCollector())
    # Infinite Loop
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
