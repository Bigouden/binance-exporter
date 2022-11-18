# Binance Exporter

## Quick Start

```bash
DOCKER_BUILDKIT=1 docker build -t binance-exporter .
docker run -dit --name binance-exporter --env BINANCE_KEY=xxx --env BINANCE_SECRET=xxx binance-exporter
```

## Metrics

```bash
# HELP binance_earn_wallet Binance Earn Wallet
# TYPE binance_earn_wallet gauge
binance_earn_wallet{asset="BNB",job="binance-exporter",type="flexible"} 1.0
# HELP binance_earn_wallet Binance Earn Wallet
# TYPE binance_earn_wallet gauge
binance_earn_wallet{asset="BUSD",job="binance-exporter",type="flexible"} 325.99909675
# HELP binance_earn_wallet Binance Earn Wallet
# TYPE binance_earn_wallet gauge
binance_earn_wallet{asset="TRU",job="binance-exporter",type="flexible"} 10.00267127
# HELP binance_earn_wallet Binance Earn Wallet
# TYPE binance_earn_wallet gauge
binance_earn_wallet{asset="DOGE",job="binance-exporter",type="locked"} 4.0
# HELP binance_funding_wallet Binance Funding Wallet
# TYPE binance_funding_wallet gauge
binance_funding_wallet{asset="EUR",job="binance-exporter"} 125.39311544
# HELP binance_spot_wallet Binance Spot Wallet
# TYPE binance_spot_wallet gauge
binance_spot_wallet{asset="BNB",job="binance-exporter"} 0.00171769
# HELP binance_spot_wallet Binance Spot Wallet
# TYPE binance_spot_wallet gauge
binance_spot_wallet{asset="LDO",job="binance-exporter"} 0.3
# HELP binance_spot_wallet Binance Spot Wallet
# TYPE binance_spot_wallet gauge
binance_spot_wallet{asset="HFT",job="binance-exporter"} 0.43433891
# HELP binance_spot_wallet Binance Spot Wallet
# TYPE binance_spot_wallet gauge
binance_spot_wallet{asset="BUSD",job="binance-exporter"} 0.05357892
# HELP binance_spot_wallet Binance Spot Wallet
# TYPE binance_spot_wallet gauge
binance_spot_wallet{asset="DOGE",job="binance-exporter"} 0.1095892
# HELP binance_spot_wallet Binance Spot Wallet
# TYPE binance_spot_wallet gauge
binance_spot_wallet{asset="TRU",job="binance-exporter"} 0.00089055
```
