#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "venue_arb_persistent.h"

#include "OrderParams.h"
#include "ExecutionTypes.h"

#include <sstream>

static std::string QuoteToString(const VenueQuote& q);

venue_arb_persistent::venue_arb_persistent(StrategyID strategyID,
                   const std::string& strategyName,
                   const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      arb_threshold_(0.01),
      aggressiveness_(0.0),
      position_size_(100),
      persistence_count_(3),  // Require 3 consecutive quotes with opportunity
      debug_(false)
{

}

venue_arb_persistent::~venue_arb_persistent() {}

void venue_arb_persistent::DefineStrategyParams()
{
    // Minimum price difference between venues required to trigger an arbitrage trade.
    // The strategy only trades when the spread between NASDAQ and IEX exceeds this threshold.
    params().CreateParam(CreateStrategyParamArgs(
        "arb_threshold",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_DOUBLE,
        arb_threshold_));

    // Price adjustment for limit orders to improve fill probability.
    // Positive values make orders more aggressive (buy below ask, sell above bid).
    // Higher values increase fill probability but worsen execution price.
    params().CreateParam(CreateStrategyParamArgs(
        "aggressiveness",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_DOUBLE,
        aggressiveness_));

    // Target position size when an arbitrage opportunity is detected.
    // The strategy will trade to reach this position (+position_size for long, -position_size for short).
    params().CreateParam(CreateStrategyParamArgs(
        "position_size",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_INT,
        position_size_));

    // Number of consecutive quotes required before trading (confirmation filter).
    // Higher values reduce false signals but may miss fast opportunities.
    params().CreateParam(CreateStrategyParamArgs(
        "persistence_count",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_INT,
        persistence_count_));

    // Enable debug output for strategy diagnostics -- not implemented
    params().CreateParam(CreateStrategyParamArgs(
        "debug",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_BOOL,
        debug_));
}

void venue_arb_persistent::DefineStrategyCommands()
{
    commands().AddCommand(StrategyCommand(1, "Cancel All Orders"));
}

void venue_arb_persistent::RegisterForStrategyEvents(StrategyEventRegister* eventRegister,
                                         DateType currDate)
{

}

void venue_arb_persistent::OnResetStrategyState()
{
    nasdaq_quotes_.clear();
    iex_quotes_.clear();
    spread_states_.clear();
}

void venue_arb_persistent::OnQuote(const QuoteEventMsg& msg)
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

    if (msg.quote().bid_side().IsValid())
        vq->bid = msg.quote().bid();

    if (msg.quote().ask_side().IsValid())
        vq->ask = msg.quote().ask();

    EvaluateArb(inst);
}

void venue_arb_persistent::EvaluateArb(const Instrument* inst)
{

    if (!nasdaq_quotes_.count(inst) || !iex_quotes_.count(inst)) {
        return;
    }
    

    const VenueQuote& n = nasdaq_quotes_[inst];
    const VenueQuote& i = iex_quotes_[inst];

    if (!n.valid() || !i.valid())
        return;

    // Get or create spread state for this instrument
    SpreadState& state = spread_states_[inst];
    
    // Check current spread opportunity
    bool current_opportunity = false;
    int current_direction = 0;
    
    if (i.bid >= n.ask + arb_threshold_) {
        // Buy on NASDAQ (cheaper), sell on IEX (more expensive)
        current_opportunity = true;
        current_direction = 1;
    }
    else if (n.bid >= i.ask + arb_threshold_) {
        // Buy on IEX (cheaper), sell on NASDAQ (more expensive)
        current_opportunity = true;
        current_direction = -1;
    }

    // Update persistence tracking
    if (current_opportunity && current_direction == state.direction) {
        // Same opportunity persists
        state.opportunity_exists = true;
        state.direction = current_direction;
        state.consecutive_count++;
    }
    else if (current_opportunity) {
        // New opportunity in different direction - reset counter
        state.opportunity_exists = true;
        state.direction = current_direction;
        state.consecutive_count = 1;
    }
    else {
        // No opportunity - reset
        state.opportunity_exists = false;
        state.direction = 0;
        state.consecutive_count = 0;
    }

    // Only trade if opportunity has persisted for required number of quotes
    int desired_position = 0;
    MarketCenterID venue = MARKET_CENTER_ID_NASDAQ;

    if (state.opportunity_exists && state.consecutive_count >= persistence_count_) {
        if (state.direction == 1) {
            // Buy on NASDAQ
            desired_position = position_size_;
            venue = MARKET_CENTER_ID_NASDAQ;
        }
        else if (state.direction == -1) {
            // Buy on IEX
            desired_position = position_size_;
            venue = MARKET_CENTER_ID_IEX;
        }
    }

    if (desired_position != 0) {
        AdjustPortfolio(inst, desired_position, venue);
    }
}

void venue_arb_persistent::AdjustPortfolio(const Instrument* inst, int desired_position, MarketCenterID venue)
{

    int current_position = portfolio().position(inst);
    int trade_size = desired_position - current_position;

    if (trade_size == 0)
        return;

    if (orders().num_working_orders(inst) > 0) {
        return;
    }
    SendOrder(inst, trade_size, venue);
}

void venue_arb_persistent::SendOrder(const Instrument* inst,
                         int trade_size,
                         MarketCenterID venue)
{
    const VenueQuote& n = nasdaq_quotes_[inst];
    const VenueQuote& i = iex_quotes_[inst];

    const VenueQuote& vq =
        (venue == MARKET_CENTER_ID_NASDAQ)
            ? nasdaq_quotes_[inst]
            : iex_quotes_[inst];

    if (!vq.valid())
        return;

    double price =
        trade_size > 0
            ? vq.ask - aggressiveness_
            : vq.bid + aggressiveness_;

    const SpreadState& state = spread_states_[inst];
    
    std::cout
        << "[SEND ORDER] "
        << inst->symbol()
        << " venue=" << (venue == MARKET_CENTER_ID_NASDAQ ? "NASDAQ" : "IEX")
        << " side=" << (trade_size > 0 ? "BUY" : "SELL")
        << " size=" << abs(trade_size)
        << " price=" << price
        << "\n  NASDAQ(" << QuoteToString(n) << ")"
        << "\n  IEX(" << QuoteToString(i) << ")"
        << "\n  aggressiveness=" << aggressiveness_
        << "\n  persistence=" << state.consecutive_count << "/" << persistence_count_
        << std::endl;

    OrderParams params(
        *inst,
        abs(trade_size),
        price,
        venue,
        trade_size > 0 ? ORDER_SIDE_BUY : ORDER_SIDE_SELL,
        ORDER_TIF_DAY,
        ORDER_TYPE_LIMIT);

    trade_actions()->SendNewOrder(params);
}


void venue_arb_persistent::OnStrategyCommand(const StrategyCommandEventMsg& msg)
{
    if (msg.command_id() == 1) {
        trade_actions()->SendCancelAll();
    }
}

void venue_arb_persistent::OnParamChanged(StrategyParam& param)
{
    if (param.param_name() == "arb_threshold") {
        param.Get(&arb_threshold_);
    }
    else if (param.param_name() == "aggressiveness") {
        param.Get(&aggressiveness_);
    }
    else if (param.param_name() == "position_size") {
        param.Get(&position_size_);
    }
    else if (param.param_name() == "persistence_count") {
        param.Get(&persistence_count_);
    }
    else if (param.param_name() == "debug") {
        param.Get(&debug_);
    }
}

static std::string QuoteToString(const VenueQuote& q)
{
    std::ostringstream oss;
    oss << "bid=" << q.bid
        << " ask=" << q.ask;
    return oss.str();
}

