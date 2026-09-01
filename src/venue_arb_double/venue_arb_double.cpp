#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "venue_arb_double.h"

#include "OrderParams.h"
#include "ExecutionTypes.h"

#include <sstream>
#include <algorithm>
#include <iostream>

static std::string QuoteToString(const VenueQuote& q);

venue_arb_double::venue_arb_double(
    StrategyID strategyID,
    const std::string& strategyName,
    const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      arb_threshold_(0.01),
      aggressiveness_(0.0),
      debug_(false)
{
}

venue_arb_double::~venue_arb_double() {}

void venue_arb_double::DefineStrategyParams()
{
    params().CreateParam(CreateStrategyParamArgs(
        "arb_threshold",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_DOUBLE,
        arb_threshold_));

    params().CreateParam(CreateStrategyParamArgs(
        "aggressiveness",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_DOUBLE,
        aggressiveness_));

    params().CreateParam(CreateStrategyParamArgs(
        "debug",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_BOOL,
        debug_));
}

void venue_arb_double::DefineStrategyCommands()
{
    commands().AddCommand(StrategyCommand(1, "Cancel All Orders"));
}

void venue_arb_double::RegisterForStrategyEvents(
    StrategyEventRegister* eventRegister,
    DateType currDate)
{
}

void venue_arb_double::OnResetStrategyState()
{
    nasdaq_quotes_.clear();
    iex_quotes_.clear();
}

void venue_arb_double::OnQuote(const QuoteEventMsg& msg)
{
    const Instrument* inst = &msg.instrument();
    MarketCenterID mc = msg.market_center_id();

    VenueQuote* vq = nullptr;

    if (mc == MARKET_CENTER_ID_NASDAQ)
        vq = &nasdaq_quotes_[inst];
    else if (mc == MARKET_CENTER_ID_IEX)
        vq = &iex_quotes_[inst];
    else
        return;

    if (msg.quote().bid_side().IsValid()) {
        vq->bid = msg.quote().bid();
        vq->bid_size = msg.quote().bid_side().size();
    }

    if (msg.quote().ask_side().IsValid()) {
        vq->ask = msg.quote().ask();
        vq->ask_size = msg.quote().ask_side().size();
    }

    EvaluateArb(inst);
}

void venue_arb_double::EvaluateArb(const Instrument* inst)
{
    if (!nasdaq_quotes_.count(inst) || !iex_quotes_.count(inst))
        return;

    const VenueQuote& n = nasdaq_quotes_[inst];
    const VenueQuote& i = iex_quotes_[inst];

    if (!n.valid() || !i.valid())
        return;

    double spread_nasdaq_arb = i.bid - n.ask;
    double spread_iex_arb    = n.bid - i.ask;

    MarketCenterID buy_venue;
    MarketCenterID sell_venue;
    int direction = 0;

    if (i.bid >= n.ask + arb_threshold_) {
        buy_venue  = MARKET_CENTER_ID_NASDAQ;
        sell_venue = MARKET_CENTER_ID_IEX;
        direction = 1;
    }
    else if (n.bid >= i.ask + arb_threshold_) {
        buy_venue  = MARKET_CENTER_ID_IEX;
        sell_venue = MARKET_CENTER_ID_NASDAQ;
        direction = -1;
    }

    if (debug_ || direction != 0) {
        std::cout
            << "[ARB CHECK] " << inst->symbol()
            << " NASDAQ(" << QuoteToString(n) << ")"
            << " IEX(" << QuoteToString(i) << ")"
            << " spread_nasdaq=" << spread_nasdaq_arb
            << " spread_iex=" << spread_iex_arb
            << " threshold=" << arb_threshold_
            << " direction=" << direction
            << std::endl;
    }

    if (direction != 0) {
        AdjustPortfolio(inst, buy_venue, sell_venue);
    }
}

void venue_arb_double::AdjustPortfolio(
    const Instrument* inst,
    MarketCenterID buy_venue,
    MarketCenterID sell_venue)
{
    const VenueQuote& buy_q =
        (buy_venue == MARKET_CENTER_ID_NASDAQ)
            ? nasdaq_quotes_[inst]
            : iex_quotes_[inst];

    const VenueQuote& sell_q =
        (sell_venue == MARKET_CENTER_ID_NASDAQ)
            ? nasdaq_quotes_[inst]
            : iex_quotes_[inst];

    if (!buy_q.valid() || !sell_q.valid())
        return;

    int buy_liq  = buy_q.ask_size;
    int sell_liq = sell_q.bid_size;

    int paired_qty = std::min({ buy_liq, sell_liq });

    if (paired_qty <= 0)
        return;

    SendOrder(inst, buy_venue,  true,  paired_qty);
    SendOrder(inst, sell_venue, false, paired_qty);
}

void venue_arb_double::SendOrder(
    const Instrument* inst,
    MarketCenterID venue,
    bool is_buy,
    int trade_size)
{
    const VenueQuote& vq =
        (venue == MARKET_CENTER_ID_NASDAQ)
            ? nasdaq_quotes_[inst]
            : iex_quotes_[inst];

    if (!vq.valid())
        return;

    int available_qty =
        is_buy ? vq.ask_size : vq.bid_size;

    int send_qty = available_qty;

    if (send_qty <= 0)
        return;

    double price =
        is_buy
            ? vq.ask - aggressiveness_
            : vq.bid + aggressiveness_;

    std::cout
        << "[SEND ORDER] "
        << inst->symbol()
        << " venue=" << (venue == MARKET_CENTER_ID_NASDAQ ? "NASDAQ" : "IEX")
        << " side=" << (is_buy ? "BUY" : "SELL")
        << " size=" << send_qty
        << " price=" << price
        << std::endl;

    OrderParams params(
        *inst,
        send_qty,
        price,
        venue,
        is_buy ? ORDER_SIDE_BUY : ORDER_SIDE_SELL,
        ORDER_TIF_DAY,
        ORDER_TYPE_LIMIT);

    trade_actions()->SendNewOrder(params);
}

void venue_arb_double::OnStrategyCommand(const StrategyCommandEventMsg& msg)
{
    if (msg.command_id() == 1) {
        trade_actions()->SendCancelAll();
    }
}

void venue_arb_double::OnParamChanged(StrategyParam& param)
{
    if (param.param_name() == "arb_threshold")
        param.Get(&arb_threshold_);
    else if (param.param_name() == "aggressiveness")
        param.Get(&aggressiveness_);
    else if (param.param_name() == "debug")
        param.Get(&debug_);
}

static std::string QuoteToString(const VenueQuote& q)
{
    std::ostringstream oss;
    oss << "bid=" << q.bid
        << " ask=" << q.ask;
    return oss.str();
}
