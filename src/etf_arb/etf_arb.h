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
#include <boost/unordered_map.hpp>
#include <cmath>

using namespace RCM::StrategyStudio;
using namespace RCM::StrategyStudio::MarketModels;

struct VenueQuote {
    double bid = NAN;
    double ask = NAN;

    bool valid() const {
        return std::isfinite(bid) && std::isfinite(ask);
    }

    double mid() const {
        return 0.5 * (bid + ask);
    }
};

class etf_arb : public Strategy {
public:
    etf_arb(StrategyID strategyID,
            const std::string& strategyName,
            const std::string& groupName);

    ~etf_arb();

public:
    virtual void OnQuote(const QuoteEventMsg& msg) override;
    virtual void OnOrderUpdate(const OrderUpdateEventMsg& msg) override {}

    void OnResetStrategyState() override;
    void OnStrategyCommand(const StrategyCommandEventMsg& msg) override;
    void OnParamChanged(StrategyParam& param) override;

private:
    virtual void RegisterForStrategyEvents(StrategyEventRegister* eventRegister,
                                           DateType currDate) override;
    virtual void DefineStrategyParams() override;
    virtual void DefineStrategyCommands() override;

private:
    void EvaluateArb();
    void AdjustPosition(int desired_position);
    void SendOrder(int trade_size, MarketCenterID venue);

private:
    const Instrument* uso_;
    const Instrument* cl_;

    boost::unordered_map<MarketCenterID, VenueQuote> uso_quotes_;
    VenueQuote cl_quote_;

    double arb_threshold_;
    double hedge_ratio_;
    double aggressiveness_;
    int position_size_;
};

extern "C" {

    _STRATEGY_EXPORTS const char* GetType() {
        return "etf_arb";
    }

    _STRATEGY_EXPORTS IStrategy* CreateStrategy(const char* strategyType,
                                                unsigned strategyID,
                                                const char* strategyName,
                                                const char* groupName) {
        if (strcmp(strategyType, GetType()) == 0)
            return new etf_arb(strategyID, strategyName, groupName);
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
