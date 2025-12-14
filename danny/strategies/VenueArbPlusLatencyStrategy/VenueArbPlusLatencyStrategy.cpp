#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "VenueArbPlusLatencyStrategy.h"

#include "OrderParams.h"
#include "ExecutionTypes.h"

VenueLatencyArb::VenueLatencyArb(StrategyID strategyID,
                   const std::string& strategyName,
                   const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      latency_ns_(0),
      arb_threshold_(0.01),
      aggressiveness_(0.0),
      position_size_(100),
      debug_(false)
{
}

VenueLatencyArb::~VenueLatencyArb() {}

void VenueLatencyArb::DefineStrategyParams()
{
    params().CreateParam(CreateStrategyParamArgs(
        "latency_ns",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_INT64,
        latency_ns_));

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

void VenueLatencyArb::DefineStrategyCommands()
{
    commands().AddCommand(StrategyCommand(1, "Cancel All Orders"));
}

void VenueLatencyArb::RegisterForStrategyEvents(StrategyEventRegister*,
                                         DateType)
{
}

void VenueLatencyArb::OnResetStrategyState()
{
    nasdaq_quotes_.clear();
    iex_quotes_.clear();
    delayed_quotes_.clear();
}

void VenueLatencyArb::OnQuote(const QuoteEventMsg& msg)
{
    const Instrument* inst = &msg.instrument();
    MarketCenterID mc = msg.market_center_id();

    if (mc != MARKET_CENTER_ID_NASDAQ &&
        mc != MARKET_CENTER_ID_IEX)
        return;

    DelayedQuote dq;
    dq.instrument = inst;
    dq.venue = mc;
    dq.bid = msg.quote().bid_side().IsValid()
                ? msg.quote().bid()
                : NAN;
    dq.ask = msg.quote().ask_side().IsValid()
                ? msg.quote().ask()
                : NAN;

    dq.apply_time =
        msg.event_time() + TimeDelta::FromNanoseconds(latency_ns_);

    delayed_quotes_.push_back(dq);

    ProcessDelayedQuotes(msg.event_time());
}

void VenueLatencyArb::ProcessDelayedQuotes(const DateTime& now)
{
    while (!delayed_quotes_.empty() &&
           delayed_quotes_.front().apply_time <= now) {

        ApplyQuote(delayed_quotes_.front());
        delayed_quotes_.pop_front();
    }
}

void VenueLatencyArb::ApplyQuote(const DelayedQuote& dq)
{
    VenueQuote& vq =
        (dq.venue == MARKET_CENTER_ID_NASDAQ)
            ? nasdaq_quotes_[dq.instrument]
            : iex_quotes_[dq.instrument];

    if (std::isfinite(dq.bid))
        vq.bid = dq.bid;

    if (std::isfinite(dq.ask))
        vq.ask = dq.ask;

    EvaluateArb(dq.instrument);
}

void VenueLatencyArb::EvaluateArb(const Instrument* inst)
{
    if (!nasdaq_quotes_.count(inst) ||
        !iex_quotes_.count(inst))
        return;

    const VenueQuote& n = nasdaq_quotes_[inst];
    const VenueQuote& i = iex_quotes_[inst];

    if (!n.valid() || !i.valid())
        return;

    int desired_position = 0;

    if (i.bid > n.ask + arb_threshold_)
        desired_position = position_size_;
    else if (n.bid > i.ask + arb_threshold_)
        desired_position = -position_size_;

    AdjustPortfolio(inst, desired_position);
}

void VenueLatencyArb::AdjustPortfolio(const Instrument* inst,
                              int desired_position)
{
    int trade_size =
        desired_position - portfolio().position(inst);

    if (trade_size == 0)
        return;

    if (orders().num_working_orders(inst) > 0)
        return;

    SendOrder(inst, trade_size, MARKET_CENTER_ID_NASDAQ);
}

void VenueLatencyArb::SendOrder(const Instrument* inst,
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

void VenueLatencyArb::OnStrategyCommand(const StrategyCommandEventMsg& msg)
{
    if (msg.command_id() == 1)
        trade_actions()->SendCancelAll();
}

void VenueLatencyArb::OnParamChanged(StrategyParam& param)
{
    if (param.param_name() == "latency_ns")
        param.Get(&latency_ns_);
    else if (param.param_name() == "arb_threshold")
        param.Get(&arb_threshold_);
    else if (param.param_name() == "aggressiveness")
        param.Get(&aggressiveness_);
    else if (param.param_name() == "position_size")
        param.Get(&position_size_);
    else if (param.param_name() == "debug")
        param.Get(&debug_);
}
