#pragma once

#ifndef _STRATEGY_STUDIO_VENUE_ARB_PERSISTENT_STRATEGY_H_
#define _STRATEGY_STUDIO_VENUE_ARB_PERSISTENT_STRATEGY_H_

#ifdef _WIN32
    #define _STRATEGY_EXPORTS __declspec(dllexport)
#else
    #ifndef _STRATEGY_EXPORTS
        #define _STRATEGY_EXPORTS
    #endif
#endif

#include <Strategy.h>
#include <MarketModels/Instrument.h>
#include <Utilities/ParseConfig.h>

#include <boost/unordered_map.hpp>
#include <cmath>
#include <deque>

using namespace RCM::StrategyStudio;
using namespace RCM::StrategyStudio::MarketModels;

struct VenueQuote {
    double bid = NAN;
    double ask = NAN;

    bool valid() const {
        return std::isfinite(bid) && std::isfinite(ask);
    }
};

// Track spread state over time
struct SpreadState {
    bool opportunity_exists = false;  // true if spread > threshold
    int direction = 0;  // 1 = buy NASDAQ, -1 = buy IEX
    int consecutive_count = 0;  // how many consecutive quotes with opportunity
};

class venue_arb_persistent : public Strategy {
public:
    venue_arb_persistent(StrategyID strategyID,
             const std::string& strategyName,
             const std::string& groupName);

    ~venue_arb_persistent();

public: 
    virtual void OnQuote(const QuoteEventMsg& msg);
    virtual void OnOrderUpdate(const OrderUpdateEventMsg& msg) {}

    void OnResetStrategyState();
    void OnStrategyCommand(const StrategyCommandEventMsg& msg);
    void OnParamChanged(StrategyParam& param);

private:
    virtual void RegisterForStrategyEvents(StrategyEventRegister* eventRegister,
                                           DateType currDate);
    virtual void DefineStrategyParams();
    virtual void DefineStrategyCommands();

private:
    void EvaluateArb(const Instrument* inst);
    void AdjustPortfolio(const Instrument* inst, int desired_position, MarketCenterID venue);
    void SendOrder(const Instrument* inst,
                   int trade_size,
                   MarketCenterID venue);

private:
    // venue state
    boost::unordered_map<const Instrument*, VenueQuote> nasdaq_quotes_;
    boost::unordered_map<const Instrument*, VenueQuote> iex_quotes_;
    
    // persistent state tracking
    boost::unordered_map<const Instrument*, SpreadState> spread_states_;

    // strategy params
    double arb_threshold_;
    double aggressiveness_;
    int position_size_;
    int persistence_count_;  // number of consecutive quotes required
    bool debug_;
};


extern "C" {

    _STRATEGY_EXPORTS const char* GetType() {
        return "venue_arb_persistent";
    }

    _STRATEGY_EXPORTS IStrategy* CreateStrategy(const char* strategyType,
                                                unsigned strategyID,
                                                const char* strategyName,
                                                const char* groupName) {
        if (strcmp(strategyType, GetType()) == 0)
            return *(new venue_arb_persistent(strategyID, strategyName, groupName));
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

