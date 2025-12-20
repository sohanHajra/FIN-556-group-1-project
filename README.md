# Venue Arbitrage and ETF Arbitrage Implementation for United States Oil Fund, LP (USO)

## Overview

This report outlines the process of building a robust arbitrage-trading strategy including data parsing and pipelining. The goal was to transform raw PCAP (Packet Capture) files from Databento and IEX into actionable data and trading behavior for ETF and Venue Arbitrage Trading Strategies on Strategy Studio, a platform used to develop and test trading strategies. The project involved multiple technical phases, including parsing raw data, interweaving market data between exchanges, and implementing various versions of these strategies.

Each phase presented unique challenges and learning opportunities, which are detailed below. This write-up is designed to be accessible to readers without prior HFT or Algorithmic Trading experience, offering clarity through structured explanations and real-world analogies.

## Biographies

**Danny Silverstein (dannys2)**: I am a senior studying Applied Mathematics with a minor in Computer Science. I am graduating in May 2026 and am passionate about applying mathematics to the trading industry, especially having to do with derivatives pricing and the management of ETFs with derivative underlyings. Created the initial Venue Arbitrage and ETF Arbitrage strategies in Strategy Studio, implemented the data merging, and small modifications to the IEX parser including scripts for automation.

LinkedIn: https://www.linkedin.com/in/dannysilverstein/ Email: dhsilver06@gmail.com

**Anton Charov (acharov2)**:

**Aditya Dalal (adala9)**: I am a senior studying Math and Computer Science, and plan to graduate in May 2026. I am passionate about applications of math and CS to the real world and am especially interested in the financial industry. I worked on making the ETF Arbitrage strategy and loading in the CME data and writing scripts to automate the PCAP extraction process.

LinkedIn: http://www.linkedin.com/in/aditya-dalal-bba2602b3 Email: dalaladi224@gmail.com

**Sohan Hajra (shajra2)**:

---

## Phase 1: Understanding PCAPs and Data Sources

### Defining the Objective

High-frequency trading relies on precise and timely market data. The primary goal of this project was to take raw market data captured in PCAP files, process it efficiently, and use it to build trading strategies. This required:

- Parsing PCAP files to extract meaningful data.
- Preparing the data for Strategy Studio to support trading decisions.

### What Are PCAPs?

Packet Capture (PCAP) files represent raw network data captured at the packet level. They are commonly used in networking and cybersecurity but are also crucial in finance for recording market data streams.

Each file contains a series of packets, each comprising a header and payload structured according to the network protocol in use. The PCAP header provides metadata describing each captured packet, such as its timestamp and size, while Ethernet headers define the link-layer frame structure. The remainder of the PCAP contains market data, which varies in structure from exchange to exchange.

In this project, the PCAP files contained:

- Ethernet headers.
- TCP/UDP packets.
- Market data messages from financial exchanges.

These files are large and complex, requiring specialized tools for decompression and parsing.

### Databento's Role

Databento provided the Nasdaq and CME market data in compressed PCAP formats. Their platform offered efficient tools for handling massive datasets:

- Compressed Files: PCAPs were stored in gzipped or zstd formats.
- Sequenced Batches: Data was organized sequentially to ensure integrity.

### Initial Challenges with PCAPs

- Understanding Packet Structure: The project began with a detailed study of the PCAP file structure, including Ethernet headers and payloads.
- Corrupted Packets: Some packets were incomplete or corrupt, necessitating careful handling.
- Tool Familiarization: Tools like Wireshark were used to visualize and dissect packets. This helped identify patterns and validate parsing logic.

Once we familiarized ourselves with PCAPs, we explored them on a per-exchange basis. Starting with Nasdaq.

Exchanges we used:

- CME - For CL contracts
- Nasdaq - For USO ETF
- IEX - For USO ETF

### Exploring Nasdaq PCAP Structure

The Nasdaq TotalView-ITCH (ITCH 5.0) protocol is a binary message format used by Nasdaq to disseminate real-time market data. ITCH messages are transmitted over UDP using the MoldUDP64 encapsulation protocol, which packages multiple ITCH messages into single UDP packets for efficient network transmission.

Each ITCH message begins with a single-byte message type identifier, followed by a fixed-length payload that varies by message type. The protocol supports dozens of message types, including order book updates (add, cancel, replace, execute), trades, system events, and administrative messages. Understanding these message structures is essential for parsing the raw binary data from PCAP files.

#### Example: Add Order No MPID Attribution Message (Type 'A')

The "Add Order No MPID Attribution" message is one of the most common message types in the ITCH feed. It represents a new order being added to the order book without Market Participator Identification (MPID) attribution. This message type is fundamental to reconstructing the Level 3 order book state.

**Message Structure:**

| Name | Offset | Length | Value | Notes |
|------|--------|--------|-------|-------|
| **Message Type** | 0 | 1 | "A" | Indicates "Add Order - No MPID Attribution Message" |
| **Stock Locate** | 1 | 2 | Integer | Locate code identifying the security |
| **Tracking Number** | 3 | 2 | Integer | Nasdaq internal tracking number |
| **Timestamp** | 5 | 6 | Integer | Nanoseconds since midnight |
| **Order Reference Number** | 11 | 8 | Integer | Unique reference number assigned to the new order at time of receipt |
| **Buy/Sell Indicator** | 19 | 1 | Alpha | "B" = Buy Order, "S" = Sell Order |
| **Shares** | 20 | 4 | Integer | Total number of shares associated with the order |
| **Stock** | 24 | 8 | Alpha | Stock symbol, right-padded with spaces |
| **Price** | 32 | 4 | Price (4) | Display price of the new order (scaled integer) |

#### Other Common ITCH Message Types

The ITCH protocol includes many other message types that are processed by the pipeline:

- **Type 'F'**: Add Order with MPID Attribution (similar to 'A' but includes market maker identification)
- **Type 'E'**: Order Executed Message (partial or full execution of an order)
- **Type 'C'**: Order Executed With Price Message (execution at price different from display price)
- **Type 'X'**: Order Cancel Message (partial cancellation)
- **Type 'D'**: Order Delete Message (full cancellation/removal)
- **Type 'U'**: Order Replace Message (modify existing order)
- **Type 'P'**: Non-Cross Trade Message (trade from hidden orders)
- **Type 'Q'**: Cross Trade Message (opening/closing crosses)

Each message type has its own fixed-length structure, allowing for efficient binary parsing.

## NASDAQ Data Processing Pipeline

Pipeline converts NASDAQ TotalView-ITCH data from compressed PCAP files to Strategy Studio tick and trade files. It handles L3 order book messages, maintains state, and outputs L2 depth-by-price and trade data.

Derivations for message format obtained from:

- Databento's Nasdaq TotalView-ITCH: https://databento.com/docs/venues-and-datasets/xnas-itch#timestamps?historical=python&live=python&reference=python
- Official Nasdaq Totalview-ITCH 5.0 Specification: https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf
- MoldUDP64 Protocol Specification: https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/moldudp64.pdf

The pipeline has 4 stages:

1. **Decompression**: `.zst` → `.pcap`
2. **PCAP Extraction**: `.pcap` → `.itch` (MoldUDP64 → ITCH messages)
3. **L3 to L2 Conversion**: `.itch` → Strategy Studio format (maintains order book)
4. **Data Management**: Batch processing, combining, and timestamp conversion

### Stage 1: Data Decompression

The pipeline first in `zst_to_pcap.py` takes a Databento `.pcap.zst` in zstandard-compressed PCAP format, and outputs a standard `.pcap` file. In order to do so, it uses `zstandard` for streaming decompression, processes it in 1MB chunks, and reports progress every 10MB or 5 seconds. Some considerations when running is that large files (multi-GB) may require sufficient disk space. The decompression ratio typically is 3-5x from compressed to uncompressed.

### Stage 2: PCAP to ITCH Conversion

In `pcap_to_itch_converter.py` input is taken as PCAP files containing MoldUDP64 packets, and output is given in the form of a Raw ITCH 5.0 binary stream. What is the process like? It uses `dpkt` and parses out the Ethernet/IP/UDP layers. Then it extracts the MOLDUDP64 payload: 10 bytes for Session ID (ASCII), 8 bytes for sequence number (big-endian), 2 bytes for message count (big-endian). For each it's message 2 bytes length + ITCH message body. As a final step, it frames the ITCH messages for the `itchfeed` parser: with the format `0x00` + `[1-byte length]` + `[ITCH bytes]`

Helpful details. The converter filters for UDP packets, handles IPv4 and IPv6, and skips messages that are >255 bytes (the ITCH 5.0 limit), and processes ~100k+ packets/second.

### Stage 3: L3 to L2 Conversion

Next, we convert Level 3 (order level) ITCH messages into Level 2 (price-level) depth data. We do this in `nasdaq_ss_tick_builder.py`, and manage our own order book state. This is done with a `PriceLevelBook` class which maintains: per-order tracking with `(order_id -> {side, price, size})`, and aggregated levels `(side -> price -> {size, num_orders})`.

**Trade Message Types**:

| ITCH Message | Type | Description | Price Source |
|-------------|------|-------------|--------------|
| `P` | NonCrossTrade | Hidden order trades | In message |
| `Q` | CrossTrade | Opening/closing crosses | In message (cross_price) |
| `C` | OrderExecutedWithPrice | Visible order executed at different price | In message (execution_price) |
| `E` | OrderExecuted | Visible order executed | **Order book lookup** (requires tracking) |

**Order Book Tracking for E Messages**:

When processing `E` messages, the system maintains a simplified order book:

- Tracks `A`/`F` messages: `order_ref → {symbol, price, side}`
- Updates on `X`, `D`, `U` messages
- Uses order book to:
  1. Filter by symbol (only trades for tracked symbol)
  2. Look up execution price (E messages don't contain price)
  3. Determine trade side (1=BUY if order was bid, -1=SELL if order was ask)

**Strategy Studio Format (T Ticks)**:

Columns:

- `COLLECTION_TIME`: UTC timestamp
- `SOURCE_TIME`: Same as COLLECTION_TIME
- `SEQ_NUM`: Synthetic sequence number
- `TICK_TYPE`: "T" (trade)
- `MARKET_CENTER`: "NASDAQ"
- `PRICE`: Trade price (4 decimal precision)
- `SIZE`: Trade size (shares)
- `FEED_TYPE`: 1=consolidated (optional, empty if default)
- `SIDE`: 1=BUY, -1=SELL, ""=UNKNOWN (optional)
- `TRADE_COND_TYPE`: "" (optional)
- `TRADE_COND`: "OPEN"/"CLOSE"/"HALT" for cross trades (optional)

**Trade Type Selection**:

Default: `{'P', 'E'}` captures:

- `P`: All hidden order trades
- `E`: All visible order trades

This captures all trades. `C` messages are less common (only when execution price ≠ display price).

### Stage 4: Data Management

#### Batch Processing

We take multiple `.zst` files across data ranges and process them using the tools mentioned above. The output is the following and organized by date:

- `output/pcap_decompressed/YYYYMMDD/`
- `output/itch_converted_pcaps/YYYYMMDD/`
- `output/tick_messages/YYYYMMDD/`
- `output/trade_messages/YYYYMMDD/`

Note that we have automatic cleanup of intermediate files (`.pcap`,`.itch`) after processing, and have optional skip flags for re-runs (`--skip-decompress`,`--skip-pcap`).

#### File Combining

In `combine_csv.py` we combine per-file outputs into daily files:

- `output/tick_messages/YYYYMMDD/*.csv` → `output/combined/combined_tick_YYYYMMDD.csv`
- `output/trade_messages/YYYYMMDD/*.csv` → `output/combined/combined_trade_YYYYMMDD.csv`

It's useful to see that these files also follow timestamp sorting to ensure chronological order and header validation for consistent format.

#### Timestamp Conversion

Our `utc_nasdaq_timestamp_converter.py` converts timestamps from EDT/EST to UTC. We add a 4 hour offset to do so. The columns `COLLECTION_TIME` and `SOURCE_TIME` receive this processing, and we output this into `output/converted_combined/`.

### Dataflow Summary

```
Raw Data (Databento)
    ↓
[Stage 1] .zst → .pcap (decompression)
    ↓
[Stage 2] .pcap → .itch (MoldUDP64 extraction)
    ↓
[Stage 3A] .itch → tick_*.txt (L3→L2 depth conversion)
    ↓
[Stage 3B] .itch → trade_*.txt (trade extraction)
    ↓
[Stage 4A] Batch: Multiple files per day
    ↓
[Stage 4B] Combine: Daily aggregated files
    ↓
[Stage 4C] UTC Conversion: Timezone correction
    ↓
Final Output: Strategy Studio compatible tick/trade files
```

#### Technical Notes for those that are inclined

**Timestamp Handling**:

ITCH provides nanoseconds after midnight. We convert to full UTC datetime: `YYYY-MM-DD HH:MM:SS.ffffff`. Strategy Studio requires both `COLLECTION_TIME` and `SOURCE_TIME`.

**Order Book State**:

Must track all orders to aggregate correctly. Handles partial fills, cancels, and replaces. Emits P ticks only when price levels change.

**Symbol Filtering**:

Filters at parser level (optimized mode). Only processes messages for the target symbol. Reduces processing time by 10-20x.

**Sequence Numbers**:

We have synthetic sequence numbers (incremental). There are separate sequences for tick and trade files. We ensure chronological ordering.

**Price Precision**:

ITCH prices stored as integers (scaled). We convert to float with 4 decimal precision.

**Side Encoding**:

For ITCH: "B"=buy, "S"=sell. And, for Strategy Studio Ticks: 1=bid, 2=ask. But for Strategy Studio Trades: 1=BUY, -1=SELL, ""=UNKNOWN.

### Performance Characteristics

The pipeline processes approximately 1 million ITCH messages per second when running in optimized mode, making it suitable for handling large NASDAQ data files efficiently. Memory usage scales linearly with the number of active orders being tracked in the order book state, as the system maintains per-order tracking dictionaries and aggregated price level maps. This design ensures that memory consumption remains predictable and manageable even for highly liquid symbols with thousands of simultaneous orders.

All processing is performed using streaming I/O operations, meaning that files are never fully loaded into memory. Instead, the system reads and processes data in chunks, allowing it to handle files of arbitrary size without memory constraints. This streaming approach is particularly important when processing multi-gigabyte PCAP files that contain millions of messages.

Several key optimizations contribute to the high processing throughput. Parser-level message filtering ensures that only relevant ITCH message types (A, F, E, C, X, D, U) are parsed, avoiding the overhead of decoding thousands of other message types that are not needed for order book reconstruction. Early symbol filtering skips the expensive decode operation for messages that don't match the target symbol, which is particularly effective since most messages in a NASDAQ feed are for other symbols. Order book existence checks are performed before decoding execution and cancel messages, allowing the system to quickly skip messages for orders that aren't being tracked. Finally, timestamp string computation is performed lazily, only converting nanoseconds to formatted datetime strings when actually needed for output, rather than pre-computing timestamps for every message.

Note for Strategy Studio look at the Text Tick Reader to match the format exactly. Even the file name is important.

### ITCH Message Parsing Library

The pipeline uses the `itchfeed` Python library (version 1.0.6) to parse NASDAQ ITCH 5.0 binary messages. This library provides a comprehensive `MessageParser` class that can decode all ITCH message types defined in the NASDAQ TotalView-ITCH specification, including order book updates, trades, system events, and administrative messages. The parser handles the binary message format automatically, converting raw bytes into structured Python objects with typed fields.

The `MessageParser` supports selective message type filtering at the parser level, allowing the pipeline to specify which message types to parse (e.g., `MessageParser(message_type=b"AFECXDU")` for order book messages). This optimization avoids the overhead of parsing thousands of irrelevant message types, significantly improving processing speed. When no filter is specified, the parser processes all message types in the feed, making it suitable for comprehensive market data analysis.

---

# Phase 3: The Strategies

## What Is USO?

![USO Overview](images/uso_overview.png)

![USO Holdings](images/uso_holdings.png)

USO is an ETF designed to provide exposure to short-term movements in crude oil prices, but it does **not** hold physical oil. Instead, it holds **WTI crude oil futures contracts**, primarily at the **front of the futures curve**.

The fund is managed by **United States Oil Fund, LP**, and its mandate is to track **daily changes in oil prices** as closely as possible using exchange-traded futures.

---

## How USO Gets Oil Exposure

USO maintains exposure by:

- Holding near-dated WTI futures  
- Periodically rolling contracts as they approach expiration  
- Holding collateral (e.g., cash or T-bills) to support futures positions  

Because futures expire, USO must continuously sell expiring contracts and buy later ones. This rolling process introduces **roll yield**, which can either help or hurt performance depending on the shape of the oil futures curve.

---

## Why USO ≠ Spot Oil

Although USO is often treated as “the price of oil,” its returns are driven by:

- Changes in futures prices  
- Roll costs (or gains)  
- Futures curve structure (contango vs. backwardation)  

As a result:

- USO tracks **oil futures**, not spot oil  
- Over longer horizons, its performance can diverge significantly from spot price changes  
- Over short horizons, it often tracks closely enough to serve as a liquid oil proxy  

This distinction is critical when valuing USO or constructing arbitrage trades.

---

## Why USO Is Tradeable for Arbitrage

USO is attractive from a trading perspective because:

- It is highly liquid  
- Its underlying instruments (WTI futures) are transparent and liquid  
- Its implied value can be estimated directly from futures prices  
- Temporary ETF–futures mispricings occur intraday  

These properties make USO a natural candidate for **ETF–futures relative-value strategies**, where price discrepancies can be traded with the expectation of convergence.

---

# The Venue Arbitrage Strategy

![Venue Arbitrage Example](images/qt_venuearb.png)

## Venue Arbitrage Between IEX and Nasdaq for USO

Venue arbitrage exploits short-lived price differences for the same security trading simultaneously on multiple exchanges. For USO, this means trading discrepancies between **IEX** and **NASDAQ**, both of which list and trade the ETF.

Although USO represents the same underlying asset everywhere, its quoted prices can momentarily diverge due to differences in **market structure**, **latency**, and **liquidity**.

---

## Protected Quotes and Why They Matter

In U.S. equity markets, the best displayed bid and offer across all exchanges are designated **Protected Quotes** under **SEC Regulation NMS**. These quotes represent the best immediately executable prices available in the market, and other venues are prohibited from executing trades at worse prices—a restriction enforced by the **Order Protection Rule (Rule 611)**.

As a result:

- If Nasdaq is showing the best offer for USO, other venues must either route to Nasdaq or match that price  
- Trades executed at inferior prices constitute a **trade-through** and violate the rule  
- Protected Quotes act as a hard constraint on how far prices can diverge across venues  

This mechanism ensures investors receive the best available price, but it does **not** eliminate very short-lived discrepancies at the quote level.

---

## Why Discrepancies Still Occur

Despite quote protection, prices can still differ briefly because:

- Order books update asynchronously across venues  
- Quotes can change faster than routing decisions  
- Some venues, such as IEX, introduce a small intentional delay to incoming orders  
- Liquidity depth differs even at the same displayed price  

These effects are most visible during periods of fast order flow, when quote updates propagate unevenly through the market.

---

## The Arbitrage Logic

The strategy targets moments when:

- A Protected Quote is present on one venue  
- Another venue temporarily lags in reflecting that price  

In these cases, a trader can:

- Buy on the venue displaying the protected best offer  
- Sell on the venue displaying the protected best bid  
- Capture the transient cross-venue spread before quotes realign  

As market makers rebalance inventory and smart order routers enforce quote protection, prices quickly reconverge.

---

## Practical Constraints

This is microstructure-driven arbitrage, not risk-free:

- Latency determines whether a protected quote is still accessible  
- Partial fills can create short-term exposure  
- Fees, rebates, and routing costs materially affect outcomes  

The strategy succeeds only when execution speed and venue-level data are sufficient to act before the market synchronizes.

---

# ETF Arbitrage: Core Mechanism and Trading Intuition

![ETF Arbitrage Visual](images/etf_arb_visual.png)

Most ETFs are kept aligned with their underlying assets through a **creation–redemption mechanism** operated by **Authorized Participants (APs)**. When an ETF’s market price deviates from the value of its underlying holdings (its implied NAV), APs can create or redeem ETF shares in exchange for the underlying basket, locking in the price difference and pushing the ETF back toward fair value.

If an ETF trades above its implied value, APs can:

- Buy the underlying assets  
- Deliver them to the ETF sponsor  
- Receive newly created ETF shares  
- Sell those shares at the elevated market price  

If it trades below implied value, the process runs in reverse via redemptions.

This structure creates a strong economic force that prevents persistent mispricing.

---

## Why Short-Horizon ETF Arbitrage Exists

Creation and redemption are not instantaneous. They are:

- Capital-intensive  
- Executed in large blocks  
- Typically triggered only when mispricing is large or persistent  

As a result, ETFs can exhibit short-lived intraday deviations from their implied value before AP activity restores equilibrium. These temporary dislocations are the basis of ETF arbitrage strategies that operate at smaller size and shorter horizons than APs themselves.

The goal is **not** to perform creation/redemption directly, but to anticipate convergence by trading the ETF against its underlying assets when pricing becomes temporarily inconsistent.

---

## USO-Specific Arbitrage Logic

USO is particularly suitable for this approach because it derives its value from **WTI crude oil futures**, not spot oil. This allows the ETF’s fair value to be implied directly from observable futures prices, while the ETF itself trades continuously on equity exchanges.

The strategy exploits moments when:

- USO trades rich or cheap relative to its futures-implied value  
- Liquidity or order-flow imbalances temporarily distort prices  
- Market makers and APs have not yet corrected the discrepancy  

Positions are constructed by going **long the undervalued leg** and **short the overvalued leg**, with the expectation that ETF price and implied value will reconverge as arbitrage forces act.

This is best viewed as **microstructure-driven arbitrage anchored to ETF mechanics**, rather than risk-free arbitrage.
