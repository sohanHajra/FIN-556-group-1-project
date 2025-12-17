#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "venue_arb.h"

#include "OrderParams.h"
#include "ExecutionTypes.h"

#include <sstream>

static std::string QuoteToString(const VenueQuote& q);

venue_arb::venue_arb(StrategyID strategyID,
                   const std::string& strategyName,
                   const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      arb_threshold_(0.01),
      aggressiveness_(0.0),
      position_size_(100),
      debug_(false)
{

}

venue_arb::~venue_arb() {}

void venue_arb::DefineStrategyParams()
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
        "position_size",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_INT,
        position_size_));

    params().CreateParam(CreateStrategyParamArgs(
        "debug",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_BOOL,
        debug_));
}

void venue_arb::DefineStrategyCommands()
{
    commands().AddCommand(StrategyCommand(1, "Cancel All Orders"));
}

void venue_arb::RegisterForStrategyEvents(StrategyEventRegister* eventRegister,
                                         DateType currDate)
{

}

void venue_arb::OnResetStrategyState()
{
    nasdaq_quotes_.clear();
    iex_quotes_.clear();
}

void venue_arb::OnQuote(const QuoteEventMsg& msg)
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

void venue_arb::EvaluateArb(const Instrument* inst)
{

    if (!nasdaq_quotes_.count(inst) || !iex_quotes_.count(inst)) {
        return;
    }
    

    const VenueQuote& n = nasdaq_quotes_[inst];
    const VenueQuote& i = iex_quotes_[inst];

    if (!n.valid() || !i.valid())
        return;

    std::cout
        << "[ARB] "
        << inst->symbol()
        << " NASDAQ(" << QuoteToString(n) << ") "
        << " IEX(" << QuoteToString(i) << ") "
        << " threshold=" << arb_threshold_
        << std::endl;

    int desired_position = 0;

    if (i.bid > n.ask + arb_threshold_) {
        desired_position = position_size_;
    }
    else if (n.bid > i.ask + arb_threshold_) {
        desired_position = -position_size_;
    }

    AdjustPortfolio(inst, desired_position);
}

void venue_arb::AdjustPortfolio(const Instrument* inst, int desired_position)
{

    int current_position = portfolio().position(inst);
    int trade_size = desired_position - current_position;
    std::cout
        << "[PORTFOLIO] "
        << inst->symbol()
        << " current=" << current_position
        << " desired=" << desired_position
        << " trade_size=" << trade_size
        << std::endl;

    if (trade_size == 0)
        return;

    if (orders().num_working_orders(inst) > 0) {
        return;
    }
    SendOrder(inst, trade_size, MARKET_CENTER_ID_NASDAQ);
}

void venue_arb::SendOrder(const Instrument* inst,
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


void venue_arb::OnStrategyCommand(const StrategyCommandEventMsg& msg)
{
    if (msg.command_id() == 1) {
        trade_actions()->SendCancelAll();
    }
}

void venue_arb::OnParamChanged(StrategyParam& param)
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
