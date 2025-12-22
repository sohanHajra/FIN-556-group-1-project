#pragma once

#ifndef _STRATEGY_STUDIO_ETF_ARB_STRATEGY_H_
#define _STRATEGY_STUDIO_ETF_ARB_STRATEGY_H_

#ifdef _WIN32
    #define _STRATEGY_EXPORTS __declspec(dllexport)
#else
    #ifndef _STRATEGY_EXPORTS
        #define _STRATEGY_EXPORTS
    #endif
#endif

#include <Strategy.h>
#include <MarketModels/Instrument.h>
#include <OrderParams.h>     
#include <Order.h>           
#include <BarEventMsg.h>      
#include <QuoteEventMsg.h>   
#include <map>
#include <vector>
#include <string>
#include <cmath>


using namespace RCM::StrategyStudio;
using namespace RCM::StrategyStudio::MarketModels;
using namespace RCM::StrategyStudio::Utilities;

struct VenuePrice { // updated the struct
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
    virtual void DefineStrategyParams() override; 
    virtual void OnParamChanged(StrategyParam& param) override;

    virtual void RegisterForStrategyEvents(StrategyEventRegister* eventRegister, DateType currDate) override;
    
    virtual void OnQuote(const QuoteEventMsg& msg) override; 
    
    virtual void OnTrade(const TradeDataEventMsg& msg) override;
    virtual void OnBar(const BarEventMsg& msg) override; 
    virtual void OnOrderUpdate(const OrderUpdateEventMsg& msg) override;

private: 
    void EvaluateArb();
    void AdjustPosition(int desired_position, MarketCenterID venue, double limit_price);

private: 
    const Instrument* etf_instrument_;
    std::map<const Instrument*, double> basket_weights_; 
    std::map<const Instrument*, double> last_mid_prices_; 
    std::map<MarketCenterID, VenuePrice> etf_venue_quotes_;
    std::string etf_symbol_param_;      
    std::string basket_symbols_param_;  
    double entry_threshold_;            
    double position_size_;      
    double aggressiveness_; 
    double inventory_skew_;
};
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
#endif