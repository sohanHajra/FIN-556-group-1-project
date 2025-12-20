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
