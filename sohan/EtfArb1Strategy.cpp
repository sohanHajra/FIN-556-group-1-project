#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "EtfArb1Strategy.h"
#include <InstrumentManager.h>
#include <Portfolio.h>
#include <sstream> 
#include <iostream>

using namespace RCM::StrategyStudio;
using namespace RCM::StrategyStudio::MarketModels;

EtfArb1Strategy::EtfArb1Strategy(StrategyID strategyID, const std::string& strategyName, const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      etf_instrument_(nullptr),
      etf_symbol_param_("USO"),                
      basket_symbols_param_("CL"),             
      entry_threshold_(0.05),                  
      position_size_(500),
      aggressiveness_(0.01) {

    params().CreateParam(CreateStrategyParam("etf", CommandUserType::STRATEGY_PARAM, etf_symbol_param_));
    params().CreateParam(CreateStrategyParam("basket", CommandUserType::STRATEGY_PARAM, basket_symbols_param_));
    params().CreateParam(CreateStrategyParam("threshold", CommandUserType::STRATEGY_PARAM, entry_threshold_));
    params().CreateParam(CreateStrategyParam("size", CommandUserType::STRATEGY_PARAM, position_size_));
    params().CreateParam(CreateStrategyParam("aggressiveness", CommandUserType::STRATEGY_PARAM, aggressiveness_));
}

EtfArb1Strategy::~EtfArb1Strategy() {}

void EtfArb1Strategy::OnResetStrategyState() {
    last_mid_prices_.clear();
    etf_venue_quotes_.clear();
}

void EtfArb1Strategy::RegisterForStrategyEvents(StrategyEventRegister* eventRegister, DateType currDate) {
    // subscribe to ETF
    if (instrument_manager()->TryGetInstrument(etf_symbol_param_, &etf_instrument_)) {
        eventRegister->RegisterForInstrument(etf_instrument_);
    } else {
        std::cout << "CRITICAL ERROR: ETF Instrument " << etf_symbol_param_ << " not found!" << std::endl;
    }

    // subscribe to the basket/ proxy
    std::stringstream ss(basket_symbols_param_);
    std::string segment;
    std::vector<std::string> symbol_list;

    while (std::getline(ss, segment, ',')) {
        symbol_list.push_back(segment);
    }

    for (const auto& sym : symbol_list) {
        const Instrument* inst = nullptr;
        if (instrument_manager()->TryGetInstrument(sym, &inst)) {
            eventRegister->RegisterForInstrument(inst);

            basket_weights_[inst] = 1.0 / symbol_list.size(); 
            last_mid_prices_[inst] = 0.0;
        } else {
             std::cout << "ERROR: Basket Component " << sym << " not found!" << std::endl;
        }
    }
}

void EtfArb1Strategy::OnQuote(const QuoteDataEventMsg& msg) {
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

    // safety check- waiting for all the data
    if (valid_components < basket_weights_.size() || fair_value <= 0) return;

    // find the BEST venue, not just the first one
    int desired_position = 0;
    MarketCenterID best_venue = MARKET_CENTER_ID_IEX;
    double best_execution_price = 0.0;
    
    // track best prices found so far
    double highest_bid = std::numeric_limits<double>::lowest(); 
    double lowest_ask = std::numeric_limits<double>::max();

    for (auto const& item : etf_venue_quotes_) {
        MarketCenterID venue = item.first;
        const VenuePrice& q = item.second;

        // ETF is expensive 
        if (q.valid_bid && q.bid > (fair_value + entry_threshold_)) {
            // Found a better bid?
            if (q.bid > highest_bid) {
                highest_bid = q.bid;
                best_venue = venue;
                desired_position = -position_size_; // Short
                best_execution_price = q.bid;
            }
        }

        // ETF is Cheap (We want to Buy at lowest Ask)
        else if (q.valid_ask && q.ask < (fair_value - entry_threshold_)) {
            // Found a cheaper ask?
            if (q.ask < lowest_ask) {
                lowest_ask = q.ask;
                best_venue = venue;
                desired_position = position_size_; // Long
                best_execution_price = q.ask;
            }
        }
    }

    // only execute if we found a valid opportunity
    if (desired_position != 0) {
        AdjustPosition(desired_position, best_venue, best_execution_price);
    }
}

void EtfArb1Strategy::AdjustPosition(int desired_position, MarketCenterID venue, double market_price) {
    int current_position = portfolio().position(etf_instrument_);
    int trade_size = desired_position - current_position;

    if (trade_size == 0) return;
    
    // don't stack orders
    if (orders().num_working_orders(etf_instrument_) > 0) return;
    
    OrderSide side = (trade_size > 0) ? ORDER_SIDE_BUY : ORDER_SIDE_SELL;
    
    double limit_price = (side == ORDER_SIDE_BUY) 
                         ? market_price + aggressiveness_ 
                         : market_price - aggressiveness_;

    OrderParams op(
        etf_instrument_, 
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
    const char* GetType() { return "EtfArb1Strategy"; }
    IStrategy* CreateStrategy(const char* strategyType, unsigned strategyID, const char* strategyName, const char* groupName) {
        if (strcmp(strategyType, GetType()) == 0) return new EtfArb1Strategy(strategyID, strategyName, groupName);
        return NULL;
    }
    const char* GetAuthor() { return "dlariviere"; }
    const char* GetAuthorGroup() { return "UIUC"; }
    const char* GetReleaseVersion() { return "1.0"; }
}