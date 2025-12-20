#pragma once

#include <Strategy.h>
#include <MarketModels/Instrument.h>
#include <OrderParams.h>      // Match file list
#include <Order.h>            // Match file list
#include <BarEventMsg.h>      
#include <QuoteEventMsg.h>   
#include <map>
#include <vector>
#include <string>
#include <cmath>


using namespace RCM::StrategyStudio;
using namespace RCM::StrategyStudio::MarketModels;

struct VenuePrice {
    double bid = 0.0;
    double ask = 999999.0;
    bool valid_bid = false;
    bool valid_ask = false;
};

class EtfArb1Strategy : public Strategy {
public:
    EtfArb1Strategy(StrategyID strategyID, const std::string& strategyName, const std::string& groupName);
    ~EtfArb1Strategy();

public: 
    virtual void OnResetStrategyState() override;
    virtual void RegisterForStrategyEvents(StrategyEventRegister* eventRegister, DateType currDate) override;
    
    virtual void OnQuote(const QuoteDataEventMsg& msg) override; 
    
    virtual void OnTrade(const TradeDataEventMsg& msg) override;
    virtual void OnBar(const BarEventMsg& msg) override; 
    virtual void OnOrderUpdate(const OrderUpdateEventMsg& msg) override;

private: 
    void EvaluateArb();
    void AdjustPosition(int desired_position, MarketCenterID venue, double limit_price);

private: 
    const Instrument* etf_instrument_;
    std::map<const Instrument*, double> basket_weights_; 
    std::map<const Instrument*, double> last_mid_prices_; // Cache mid-prices of CL/Basket

    std::map<MarketCenterID, VenuePrice> etf_venue_quotes_;
    
    std::string etf_symbol_param_;      
    std::string basket_symbols_param_;  
    double entry_threshold_;            
    double position_size_;      
    double aggressiveness_; 
};