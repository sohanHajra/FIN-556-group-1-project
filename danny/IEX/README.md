## IEX Parser

This IEX Parser offers several key benefits:

* **High-performance parsing**: Significantly faster than Python parsers
* **Multi-timestamp support**: Provides three timestamps for each event:
	+ **Event timestamp** (from the matching engine)
	+ **Packet send timestamp**
	+ **Packet capture timestamp**

### Usage

- **download_parse_load.sh**: Use this script to download, parse, and load data to OneTick. Edit the database name, start date, and end date within the script.

### Filtering Symbols

The script can filter for only interested symbols by changing `sym.txt` and adding the interested symbols per line (leave a blank line at the end).

To parse all symbols, change to `--symbols ALL` in [`download_parse_load.sh`](/server/parsers/IEX/download_parse_load.sh).

### Split Files

To split the parsed files by the symbol letter, change the `--split` flag in [`download_parse_load.sh`](/server/parsers/IEX/download_parse_load.sh) to `True`. This will produce 52 files, 26 for each alphabet for trades and 26 for price level updates.

### Parsed output format

We parse two types of messages:
Certainly! Here's the Markdown block aligned:


* #### Trade Report Messages

    Trades are saved into `<date>_trd.csv`. The output looks like this:

    ```
    Packet Capture Time,Packet Send Time,Message ID,IEX Timestamp,Tick Type,Symbol,Size,Price,Trade ID,Sale Condition
    1696248274476274944,1696248274476249406,60091,1696248274475865577,T,MSFT,10,316.350000,2275739,EXTENDED_HOURS|ODD_LOT
    1696248522899780096,1696248522899762796,70817,1696248522899669709,T,AAPL,20,171.410000,2683260,EXTENDED_HOURS|ODD_LOT
    ```

* #### Price Level Updates

    Price level updates are saved as `<date>_prl.csv`. The output looks like this:

    ```
    Packet Capture Time,Packet Send Time,Message ID,IEX Timestamp,Tick Type,Symbol,Price,Size,Record Type,Flag,ASK
    1696248000327041024,1696248000326948634,45631,1696248000184809932,PRL,MSFT,348.000000,20,R,1,1
    1696249295813316096,1696249295813302703,104927,1696249295813269151,PRL,AAPL,171.130000,243,R,1,1
    ```

### Source Directory

The `src` directory houses the Python and C++ files utilized by the bash scripts. For a brief overview, refer to [src_Readme](/server/parsers/IEX/src/README.md).

### Data Directory

The `data` directory contains two subdirectories: `iex_downloads` (default location for raw IEX data) and `one_tick_parsed` (default directory for parsed data).
