#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "VenueArbStrategy.h"

#include "OrderParams.h"
#include "ExecutionTypes.h"

#include <sstream>


VenueArb::VenueArb(StrategyID strategyID,
                   const std::string& strategyName,
                   const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      arb_threshold_(0.01),
      aggressiveness_(0.0),
      position_size_(100),
      debug_(false)
{
}

VenueArb::~VenueArb() {}

void VenueArb::DefineStrategyParams()
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

void VenueArb::DefineStrategyCommands()
{
    commands().AddCommand(StrategyCommand(1, "Cancel All Orders"));
}

void VenueArb::RegisterForStrategyEvents(StrategyEventRegister* eventRegister,
                                         DateType currDate)
{

}

void VenueArb::OnResetStrategyState()
{
    nasdaq_quotes_.clear();
    iex_quotes_.clear();
}

void VenueArb::OnQuote(const QuoteEventMsg& msg)
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

void VenueArb::EvaluateArb(const Instrument* inst)
{
    if (!nasdaq_quotes_.count(inst) || !iex_quotes_.count(inst)) {
        return;
        std::cout<<"no data here (venuearbstrategy.cpp)"<<std::endl;
    }

    const VenueQuote& n = nasdaq_quotes_[inst];
    const VenueQuote& i = iex_quotes_[inst];

    if (!n.valid() || !i.valid())
        return;

    int desired_position = 0;

    if (i.bid > n.ask + arb_threshold_) {
        desired_position = position_size_;
    }
    else if (n.bid > i.ask + arb_threshold_) {
        desired_position = -position_size_;
    }

    AdjustPortfolio(inst, desired_position);
}

void VenueArb::AdjustPortfolio(const Instrument* inst, int desired_position)
{
    int current_position = portfolio().position(inst);
    int trade_size = desired_position - current_position;

    if (trade_size == 0)
        return;

    if (orders().num_working_orders(inst) > 0)
        return;

    SendOrder(inst, trade_size, MARKET_CENTER_ID_NASDAQ);
}

void VenueArb::SendOrder(const Instrument* inst,
                         int trade_size,
                         MarketCenterID venue)
{
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


void VenueArb::OnStrategyCommand(const StrategyCommandEventMsg& msg)
{
    if (msg.command_id() == 1) {
        trade_actions()->SendCancelAll();
    }
}

void VenueArb::OnParamChanged(StrategyParam& param)
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
