#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "etf_arb.h"

etf_arb::etf_arb(StrategyID strategyID,
                 const std::string& strategyName,
                 const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      uso_(nullptr),
      cl_(nullptr),
      arb_threshold_(0.05),
      hedge_ratio_(0.1),
      aggressiveness_(0.0),
      position_size_(100) {}

etf_arb::~etf_arb() {}

void etf_arb::DefineStrategyParams() {
    params().CreateParam(CreateStrategyParamArgs(
        "arb_threshold",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_DOUBLE,
        arb_threshold_));

    params().CreateParam(CreateStrategyParamArgs(
        "hedge_ratio",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_DOUBLE,
        hedge_ratio_));

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
}

void etf_arb::DefineStrategyCommands() {
    commands().AddCommand(StrategyCommand(1, "Cancel All Orders"));
}

void etf_arb::RegisterForStrategyEvents(
    StrategyEventRegister*, DateType) {

    uso_ = instrument_set().GetInstrument("USO");
    cl_  = instrument_set().GetInstrument("CL");
}

void etf_arb::OnResetStrategyState() {
    uso_quotes_.clear();
    cl_quote_ = VenueQuote();
}

void etf_arb::OnQuote(const QuoteEventMsg& msg) {
    const Instrument& inst = msg.instrument();
    MarketCenterID mc = msg.market_center_id();

    if (&inst == uso_) {
        VenueQuote& q = uso_quotes_[mc];
        if (msg.quote().bid_side().IsValid())
            q.bid = msg.quote().bid();
        if (msg.quote().ask_side().IsValid())
            q.ask = msg.quote().ask();
    }
    else if (&inst == cl_) {
        if (msg.quote().bid_side().IsValid())
            cl_quote_.bid = msg.quote().bid();
        if (msg.quote().ask_side().IsValid())
            cl_quote_.ask = msg.quote().ask();
    }
    else {
        return;
    }

    EvaluateArb();
}

void etf_arb::EvaluateArb() {
    if (!cl_quote_.valid())
        return;

    double cl_fair = cl_quote_.mid() * hedge_ratio_;
    int desired_position = 0;

    for (auto& it : uso_quotes_) {
        VenueQuote& uso_q = it.second;

        if (!uso_q.valid())
            continue;

        if (uso_q.bid > cl_fair + arb_threshold_) {
            desired_position = -position_size_;
        }
        else if (uso_q.ask < cl_fair - arb_threshold_) {
            desired_position = position_size_;
        }
    }

    AdjustPosition(desired_position);
}

void etf_arb::AdjustPosition(int desired_position) {
    int current = portfolio().position(uso_);
    int trade_size = desired_position - current;

    if (trade_size == 0)
        return;

    if (orders().num_working_orders(uso_) > 0)
        return;

    SendOrder(trade_size, MARKET_CENTER_ID_NASDAQ);
}

void etf_arb::SendOrder(int trade_size, MarketCenterID venue) {
    VenueQuote& q = uso_quotes_[venue];
    if (!q.valid())
        return;

    double price =
        trade_size > 0
            ? q.ask - aggressiveness_
            : q.bid + aggressiveness_;

    OrderParams params(
        *uso_,
        std::abs(trade_size),
        price,
        venue,
        trade_size > 0 ? ORDER_SIDE_BUY : ORDER_SIDE_SELL,
        ORDER_TIF_DAY,
        ORDER_TYPE_LIMIT);

    trade_actions()->SendNewOrder(params);
}

void etf_arb::OnStrategyCommand(const StrategyCommandEventMsg& msg) {
    if (msg.command_id() == 1) {
        trade_actions()->SendCancelAll();
    }
}

void etf_arb::OnParamChanged(StrategyParam& param) {
    if (param.param_name() == "arb_threshold")
        param.Get(&arb_threshold_);
    else if (param.param_name() == "hedge_ratio")
        param.Get(&hedge_ratio_);
    else if (param.param_name() == "aggressiveness")
        param.Get(&aggressiveness_);
    else if (param.param_name() == "position_size")
        param.Get(&position_size_);
}
