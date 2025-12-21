#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "EtfArb1Strategy.h"
#include <sstream> 
#include <iostream>
#include <limits>
#include <cstring> 

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
      aggressiveness_(0.01),
      inventory_skew_(0.0001) {
}

EtfArb1Strategy::~EtfArb1Strategy() {}

void EtfArb1Strategy::DefineStrategyParams() {
    params().CreateParam(CreateStrategyParamArgs("etf", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_STRING, etf_symbol_param_));
    params().CreateParam(CreateStrategyParamArgs("basket", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_STRING, basket_symbols_param_));
    params().CreateParam(CreateStrategyParamArgs("threshold", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_DOUBLE, entry_threshold_));
    params().CreateParam(CreateStrategyParamArgs("size", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_DOUBLE, position_size_));
    params().CreateParam(CreateStrategyParamArgs("aggressiveness", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_DOUBLE, aggressiveness_));
    params().CreateParam(CreateStrategyParamArgs("skew", STRATEGY_PARAM_TYPE_RUNTIME, VALUE_TYPE_DOUBLE, inventory_skew_));
}

void EtfArb1Strategy::OnParamChanged(StrategyParam& param) {
    if (param.param_name() == "threshold") {
        if (!param.Get(&entry_threshold_)) return;
    } else if (param.param_name() == "size") {
        if (!param.Get(&position_size_)) return;
    } else if (param.param_name() == "aggressiveness") {
        if (!param.Get(&aggressiveness_)) return;
    } else if (param.param_name() == "skew") { //change: added handler for runtime skew updates
        if (!param.Get(&inventory_skew_)) return;
    }

}

void EtfArb1Strategy::OnResetStrategyState() {
    last_mid_prices_.clear();
    etf_venue_quotes_.clear();
}

void EtfArb1Strategy::RegisterForStrategyEvents(StrategyEventRegister* eventRegister, DateType currDate) {
    // resetting pointers
    etf_instrument_ = nullptr;
    basket_weights_.clear();
    last_mid_prices_.clear();

    // finding the instruments
    auto etf_it = instrument_find(etf_symbol_param_);

    if (etf_it != instrument_end()) {
        etf_instrument_ = etf_it->second;
        std::cout << "SUCCESS: Found ETF Instrument: " << etf_instrument_->symbol() << std::endl;
    } else {
        std::cout << "CRITICAL ERROR: Could not find ETF symbol: '" << etf_symbol_param_ << "'" << std::endl;
        // print all available instruments to debug
        for (auto it = instrument_begin(); it != instrument_end(); ++it) 
           std::cout << "Available: " << it->second->symbol() << std::endl;
    }


    // Parse the basket symbols first
    std::stringstream ss(basket_symbols_param_);
    std::string segment;

    // std::vector<std::string> symbol_list;
    // while (std::getline(ss, segment, ',')) {
    //     symbol_list.push_back(segment);
    // }

    while (std::getline(ss, segment, ',')) {

        // to get rid of whitespace from user input
        size_t first = segment.find_first_not_of(' ');
        
        if (std::string::npos == first) continue;
        size_t last = segment.find_last_not_of(' ');
        std::string clean_symbol = segment.substr(first, (last - first + 1));

        auto basket_it = instrument_find(clean_symbol);

        if (basket_it != instrument_end()) {
            const Instrument* inst = basket_it->second;
            basket_weights_[inst] = 1.0; 
            last_mid_prices_[inst] = 0.0;
            std::cout << "SUCCESS: Found Basket Component: " << inst->symbol() << std::endl;
        } else {
            std::cout << "CRITICAL ERROR: Could not find Basket symbol: '" << clean_symbol << "'" << std::endl;
        }

    }

    if (!basket_weights_.empty()) {
        double weight = 1.0 / basket_weights_.size();
        for (auto& item : basket_weights_) {
            item.second = weight;
        }
    }



    // // Iterate through instruments the system knows about and find the ones that match our parameters.
    // for (auto it = instrument_begin(); it != instrument_end(); ++it) {
    //     const Instrument* inst = it->second;
        
    //     // Check if this is our ETF
    //     if (inst->symbol() == etf_symbol_param_) {
    //         etf_instrument_ = inst;
    //         // No need to manually register if passed via command line, 
    //         // but if your API version requires it, you can uncomment:
    //         // eventRegister->RegisterInstrument(inst);
    //     }
        
    //     // Check if this is in our Basket/Proxy list
    //     for (const auto& sym : symbol_list) {
    //         if (inst->symbol() == sym) {
    //              basket_weights_[inst] = 1.0 / symbol_list.size(); 
    //              last_mid_prices_[inst] = 0.0;
    //             //  eventRegister->RegisterInstrument(inst);
    //         }
    //     }
    // }


    // Error checking
    if (!etf_instrument_) {
        std::cout << "CRITICAL ERROR: ETF Instrument " << etf_symbol_param_ << " not found! (Did you pass it in --symbols?)" << std::endl;
    }

    //error check to see we found all basket components
    if (basket_weights_.empty()) {
        std::cout << "CRITICAL ERROR: Expected " 
                  << " basket instruments, but found " << basket_weights_.size() 
                  << ". Check your symbol names!" << std::endl;
    }
}

void EtfArb1Strategy::OnQuote(const QuoteEventMsg& msg) {
    if (!etf_instrument_) return;

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
    else{
        return;
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

    //inventory skew
    // if long, then skew is +, fair_value drops, so we sell sooner
    // if short, then skew is -, fair_value increases, so we buy sooner

    int current_position = portfolio().position(etf_instrument_);
    double skew = current_position * inventory_skew_;
    double skewed_fair_value = fair_value - skew;

    int desired_position = 0;
    MarketCenterID best_venue = MARKET_CENTER_ID_IEX;
    double best_execution_price = 0.0;
    
    double highest_bid = std::numeric_limits<double>::lowest(); 
    double lowest_ask = std::numeric_limits<double>::max();     

    for (auto const& item : etf_venue_quotes_) {
        MarketCenterID venue = item.first;
        const VenuePrice& q = item.second;

        if (q.valid_bid && q.bid > (skewed_fair_value + entry_threshold_)) {
            if (q.bid > highest_bid) {
                highest_bid = q.bid;
                best_venue = venue;
                desired_position = -position_size_; 
                best_execution_price = q.bid;
            }
        }
        else if (q.valid_ask && q.ask < (skewed_fair_value - entry_threshold_)) {
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

    //can be made better
    else if (portfolio().position(etf_instrument_) != 0) { 
         // We need a price to exit at.
         // For simplicity we will use the best available opposite quote

         if (!etf_venue_quotes_.empty()) {
            // Just pick the first venue for now, or find the best one
            MarketCenterID venue = etf_venue_quotes_.begin()->first;
            double price = (portfolio().position(etf_instrument_) > 0) ? etf_venue_quotes_[venue].bid : etf_venue_quotes_[venue].ask;
            AdjustPosition(0, venue, price);
         }
    }

}

void EtfArb1Strategy::AdjustPosition(int desired_position, MarketCenterID venue, double market_price) {
    int current_position = portfolio().position(etf_instrument_);
    int trade_size = desired_position - current_position;

    if (trade_size == 0) return;
    
    if (orders().num_working_orders(etf_instrument_) > 0) return;

    OrderSide side = (trade_size > 0) ? ORDER_SIDE_BUY : ORDER_SIDE_SELL;
    
    //dynamic aggressiveness
    double dynamic_agg = aggressiveness_;

    if (abs(current_position) > 300) {
        dynamic_agg *= 2.0;
    }
    
    double limit_price = (side == ORDER_SIDE_BUY) 
                         ? market_price + dynamic_agg 
                         : market_price - dynamic_agg;

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
        return "EtfArb1Strategy";
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

