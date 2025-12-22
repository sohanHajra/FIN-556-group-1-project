#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "venue_arb_aggressive.h"

#include "OrderParams.h"
#include "ExecutionTypes.h"

#include <sstream>

static std::string QuoteToString(const VenueQuote& q);

venue_arb_aggressive::venue_arb_aggressive(StrategyID strategyID,
                   const std::string& strategyName,
                   const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      arb_threshold_(0.01),
      aggressiveness_(0.01),  // Higher default aggressiveness for better fills
      position_size_(100),
      debug_(false)
{

}

venue_arb_aggressive::~venue_arb_aggressive() {}

void venue_arb_aggressive::DefineStrategyParams()
{
    // Minimum price difference between venues required to trigger an arbitrage trade.
    // The strategy only trades when the spread between NASDAQ and IEX exceeds this threshold.
    params().CreateParam(CreateStrategyParamArgs(
        "arb_threshold",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_DOUBLE,
        arb_threshold_));

    // Price adjustment for limit orders to improve fill probability.
    // Higher default (0.01) for better fills on 1 cent spreads.
    // Positive values make orders more aggressive (buy below ask, sell above bid).
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

    // Enable debug output for strategy diagnostics -- not implemented
    params().CreateParam(CreateStrategyParamArgs(
        "debug",
        STRATEGY_PARAM_TYPE_RUNTIME,
        VALUE_TYPE_BOOL,
        debug_));
}

void venue_arb_aggressive::DefineStrategyCommands()
{
    commands().AddCommand(StrategyCommand(1, "Cancel All Orders"));
}

void venue_arb_aggressive::RegisterForStrategyEvents(StrategyEventRegister* eventRegister,
                                         DateType currDate)
{

}

void venue_arb_aggressive::OnResetStrategyState()
{
    nasdaq_quotes_.clear();
    iex_quotes_.clear();
    last_opportunities_.clear();  // Reset opportunity tracking
}

void venue_arb_aggressive::OnQuote(const QuoteEventMsg& msg)
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

void venue_arb_aggressive::EvaluateArb(const Instrument* inst)
{

    if (!nasdaq_quotes_.count(inst) || !iex_quotes_.count(inst)) {
        return;
    }
    

    const VenueQuote& n = nasdaq_quotes_[inst];
    const VenueQuote& i = iex_quotes_[inst];

    if (!n.valid() || !i.valid())
        return;

    // Calculate spreads
    double spread_nasdaq_arb = i.bid - n.ask;  // Buy NASDAQ opportunity
    double spread_iex_arb = n.bid - i.ask;      // Buy IEX opportunity
    
    // Get last opportunity state
    LastOpportunity& last_opp = last_opportunities_[inst];
    
    // Determine current opportunity
    int current_direction = 0;
    int trade_direction = 0;  // 1 = buy, -1 = sell
    MarketCenterID venue = MARKET_CENTER_ID_NASDAQ;

    if (i.bid >= n.ask + arb_threshold_) {
        // Buy on NASDAQ (cheaper), sell on IEX (more expensive)
        current_direction = 1;
        trade_direction = 1;  // Buy
        venue = MARKET_CENTER_ID_NASDAQ;
    }
    else if (n.bid >= i.ask + arb_threshold_) {
        // Buy on IEX (cheaper), sell on NASDAQ (more expensive)
        current_direction = -1;
        trade_direction = 1;  // Buy
        venue = MARKET_CENTER_ID_IEX;
    }

    // Track opportunity state for debugging
    bool opportunity_exists = (current_direction != 0);
    bool direction_changed = (current_direction != last_opp.direction);
    
    // Update tracking
    if (current_direction == 0) {
        // No opportunity exists - reset tracking
        if (last_opp.direction != 0) {
            // Opportunity just disappeared - reset
            last_opp.direction = 0;
        }
    }
    else {
        // Opportunity exists - update tracking
        last_opp.direction = current_direction;
    }

    // Debug output
    if (debug_ || opportunity_exists) {
        int current_pos = portfolio().position(inst);
        int working_orders = orders().num_working_orders(inst);
        std::cout
            << "[ARB CHECK] " << inst->symbol()
            << " NASDAQ(" << QuoteToString(n) << ")"
            << " IEX(" << QuoteToString(i) << ")"
            << " spread_nasdaq=" << spread_nasdaq_arb
            << " spread_iex=" << spread_iex_arb
            << " threshold=" << arb_threshold_
            << " current_pos=" << current_pos
            << " working_orders=" << working_orders
            << " trade_dir=" << trade_direction
            << " curr_dir=" << current_direction
            << " last_dir=" << last_opp.direction
            << " dir_changed=" << (direction_changed ? "YES" : "NO")
            << std::endl;
    }

    // AGGRESSIVE: Trade whenever opportunity exists
    // Keep trading as long as opportunity persists, building position continuously
    if (opportunity_exists && trade_direction != 0) {
        AdjustPortfolio(inst, trade_direction, venue);
    }
}

void venue_arb_aggressive::AdjustPortfolio(const Instrument* inst, int trade_direction, MarketCenterID venue)
{
    // AGGRESSIVE: Always trade position_size_ when opportunity exists
    // This allows continuous trading as long as opportunity persists
    int trade_size = trade_direction * position_size_;

    // AGGRESSIVE: Allow multiple working orders to improve fill probability
    // Only skip if we already have too many working orders (limit to prevent spam)
    int working_orders = orders().num_working_orders(inst);
    if (working_orders >= 3) {  // Allow up to 3 working orders per instrument
        if (debug_) {
            std::cout << "[SKIP] " << inst->symbol() 
                      << " has " << working_orders << " working orders (max 3)" << std::endl;
        }
        return;
    }

    // AGGRESSIVE: Send order even if we have some working orders
    // This allows building position faster by having multiple orders in the market
    SendOrder(inst, trade_size, venue);
}

void venue_arb_aggressive::SendOrder(const Instrument* inst,
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


void venue_arb_aggressive::OnStrategyCommand(const StrategyCommandEventMsg& msg)
{
    if (msg.command_id() == 1) {
        trade_actions()->SendCancelAll();
    }
}

void venue_arb_aggressive::OnParamChanged(StrategyParam& param)
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

