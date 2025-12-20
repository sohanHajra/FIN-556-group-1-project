#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "EtfArb1Strategy.h"
#include <sstream> 
#include <iostream>
#include <limits> 

using namespace RCM::StrategyStudio;
using namespace RCM::StrategyStudio::MarketModels;
using namespace RCM::StrategyStudio::Utilities;

EtfArb1Strategy::EtfArb1Strategy(StrategyID strategyID, const std::string& strategyName, const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      etf_instrument_(nullptr),
      etf_symbol_param_("USO"),                
      basket_symbols_param_("CL"),             
      entry_threshold_(0.05),                  
      position_size_(100),
      aggressiveness_(0.01) {
}

EtfArb1Strategy::~EtfArb1Strategy() {}

void EtfArb1Strategy::DefineStrategyParams() {
    params().CreateParam(CreateStrategyParamArgs("etf", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_STRING, etf_symbol_param_));
    params().CreateParam(CreateStrategyParamArgs("basket", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_STRING, basket_symbols_param_));
    params().CreateParam(CreateStrategyParamArgs("threshold", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_DOUBLE, entry_threshold_));
    params().CreateParam(CreateStrategyParamArgs("size", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_DOUBLE, position_size_));
    params().CreateParam(CreateStrategyParamArgs("aggressiveness", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_DOUBLE, aggressiveness_));
}

void EtfArb1Strategy::OnParamChanged(StrategyParam& param) {
    if (param.param_name() == "threshold") {
        if (!param.Get(&entry_threshold_)) return;
    } else if (param.param_name() == "size") {
        if (!param.Get(&position_size_)) return;
    } else if (param.param_name() == "aggressiveness") {
        if (!param.Get(&aggressiveness_)) return;
    }
}

void EtfArb1Strategy::OnResetStrategyState() {
    last_mid_prices_.clear();
    etf_venue_quotes_.clear();
}

void EtfArb1Strategy::RegisterForStrategyEvents(StrategyEventRegister* eventRegister, DateType currDate) {
    // Parse the basket symbols first
    std::stringstream ss(basket_symbols_param_);
    std::string segment;
    std::vector<std::string> symbol_list;
    while (std::getline(ss, segment, ',')) {
        symbol_list.push_back(segment);
    }

    // Iterate through instruments the system knows about and find the ones that match our parameters.
    for (auto it = instrument_begin(); it != instrument_end(); ++it) {
        const Instrument* inst = it->second;
        
        // Check if this is our ETF
        if (inst->symbol() == etf_symbol_param_) {
            etf_instrument_ = inst;
            // No need to manually register if passed via command line, 
            // but if your API version requires it, you can uncomment:
            // eventRegister->RegisterForInstrument(inst);
        }
        
        // Check if this is in our Basket/Proxy list
        for (const auto& sym : symbol_list) {
            if (inst->symbol() == sym) {
                 basket_weights_[inst] = 1.0 / symbol_list.size(); 
                 last_mid_prices_[inst] = 0.0;
                //  eventRegister->RegisterForInstrument(inst);
            }
        }
    }

    // Error checking
    if (!etf_instrument_) {
        std::cout << "CRITICAL ERROR: ETF Instrument " << etf_symbol_param_ << " not found! (Did you pass it in --symbols?)" << std::endl;
    }
}

void EtfArb1Strategy::OnQuote(const QuoteEventMsg& msg) {
    const Instrument* instrument = &msg.instrument();
    const Quote& quote = msg.quote();
    
    double bid = quote.bid();
    double ask = quote.ask();
    double mid = (bid + ask) / 2.0;

    if (instrument == etf_instrument_) {
        MarketCenterID venue = msg.market_center_id();
        VenuePrice& vp = etf_venue_quotes_[venue];
        
        if (quote.bid_side().IsValid()) {
            vp.bid = bid;
            vp.valid_bid = true;
        }
        if (quote.ask_side().IsValid()) {
            vp.ask = ask;
            vp.valid_ask = true;
        }
    } 
    else if (basket_weights_.find(instrument) != basket_weights_.end()) {
        if (mid > 0) {
            last_mid_prices_[instrument] = mid;
        }
    }

    EvaluateArb();
}

void EtfArb1Strategy::EvaluateArb() {
    double fair_value = 0.0;
    int valid_components = 0;

    for (auto const& item : basket_weights_) {
        double price = last_mid_prices_[item.first];
        if (price > 0) {
            fair_value += price * item.second;
            valid_components++;
        }
    }

    if (valid_components != basket_weights_.size() || fair_value <= 0) return;

    int desired_position = 0;
    MarketCenterID best_venue = MARKET_CENTER_ID_IEX;
    double best_execution_price = 0.0;
    
    double highest_bid = std::numeric_limits<double>::lowest(); 
    double lowest_ask = std::numeric_limits<double>::max();     

    for (auto const& item : etf_venue_quotes_) {
        MarketCenterID venue = item.first;
        const VenuePrice& q = item.second;

        if (q.valid_bid && q.bid > (fair_value + entry_threshold_)) {
            if (q.bid > highest_bid) {
                highest_bid = q.bid;
                best_venue = venue;
                desired_position = -position_size_; 
                best_execution_price = q.bid;
            }
        }
        else if (q.valid_ask && q.ask < (fair_value - entry_threshold_)) {
            if (q.ask < lowest_ask) {
                lowest_ask = q.ask;
                best_venue = venue;
                desired_position = position_size_; 
                best_execution_price = q.ask;
            }
        }
    }

    if (desired_position != 0) {
        AdjustPosition(desired_position, best_venue, best_execution_price);
    }
}

void EtfArb1Strategy::AdjustPosition(int desired_position, MarketCenterID venue, double market_price) {
    int current_position = portfolio().position(etf_instrument_);
    int trade_size = desired_position - current_position;

    if (trade_size == 0) return;
    
    if (orders().num_working_orders(etf_instrument_) > 0) return;

    OrderSide side = (trade_size > 0) ? ORDER_SIDE_BUY : ORDER_SIDE_SELL;
    
    double limit_price = (side == ORDER_SIDE_BUY) 
                         ? market_price + aggressiveness_ 
                         : market_price - aggressiveness_;

    OrderParams op(
        *etf_instrument_,
        abs(trade_size), 
        limit_price, 
        venue, 
        side, 
        ORDER_TIF_DAY, 
        ORDER_TYPE_LIMIT
    );

    trade_actions()->SendNewOrder(op);
}

void EtfArb1Strategy::OnTrade(const TradeDataEventMsg& msg) {}
void EtfArb1Strategy::OnBar(const BarEventMsg& msg) {}
void EtfArb1Strategy::OnOrderUpdate(const OrderUpdateEventMsg& msg) {}

extern "C" {

    _STRATEGY_EXPORTS const char* GetType() {
        return "etf_arb";
    }

    _STRATEGY_EXPORTS IStrategy* CreateStrategy(const char* strategyType,
                                                unsigned strategyID,
                                                const char* strategyName,
                                                const char* groupName) {
        if (std::strcmp(strategyType, GetType()) == 0) {
            // Need to use conversion operator on object not pointer
            // this is to invoke IStrategy* operator
            return *(new EtfArb1Strategy(strategyID, strategyName, groupName));
        }
        return nullptr;
    }

    _STRATEGY_EXPORTS const char* GetAuthor() {
        return "dlariviere";
    }

    _STRATEGY_EXPORTS const char* GetAuthorGroup() {
        return "UIUC";
    }

    _STRATEGY_EXPORTS const char* GetReleaseVersion() {
        return Strategy::release_version();
    }
}

