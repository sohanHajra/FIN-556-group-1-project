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

Nasdaq ITCH protocol specifications

Example Nasdaq message type: Add order no "market participator identification"

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
