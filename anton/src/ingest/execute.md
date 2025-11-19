# Test Commands

```python
python pcap_to_itch.py ABSOLUTE_PATH_RAW_PCAP ABSOLUTE_PATH_TO_ITCH_FILE
```

```python
python nasdaq_loader.py ABSOLUTE_PATH_TO_ITCH_FILE  SPY -o spy_trades.csv
```

```
python pcap_to_itch.py C:\data\dev\fin556\group_01_project\anton\data\nasdaq_pcaps\ny4-xnas-tvitch-a-20250401T083000.pcap C:\data\dev\fin556\group_01_project\anton\data\nasdaq_pcaps\ny4-xnas-tvitch-a-20250401T083000.itch
```
```
python nasdaq_loader.py C:\data\dev\fin556\group_01_project\anton\data\nasdaq_pcaps\ny4-xnas-tvitch-a-20250401T083000.itch  SPY -o spy_trades_2.csv
```

```
python new_nasdaq_ss_builder.py C:\data\dev\fin556\group_01_project\anton\data\nasdaq_pcaps\ny4-xnas-tvitch-a-20250401T083000_2.itch USO 2025-01-10 -o tick_USO_20250110.txt
```


python nasdaq_ss_tick_builder.py C:\path\to\file.itch USO 2025-01-10 -o tick_USO_20250110.txt


# Expected output

```csv
ts_ns,symbol,price,shares
16202872317835,SPY,558.26,17
16203000242336,SPY,558.26,18
16260495809263,SPY,558.2,50
16371384214156,SPY,558.44,89
16690861254565,SPY,558.38,1
```