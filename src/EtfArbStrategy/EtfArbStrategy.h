#pragma once

#include <Strategy.h>
#include <MarketModels/Instrument.h>
#include <map>

using namespace RCM::StrategyStudio;

class EtfArbStrategy : public Strategy {
public:
    EtfArbStrategy(StrategyID strategyID, const std::string& strategyName, const std::string& groupName);
    ~EtfArbStrategy();

public: 
    virtual void OnResetStrategyState() override;
    virtual void RegisterForStrategyEvents(StrategyEventRegister* eventRegister, DateType currDate) override;
    
    // Market data events
    virtual void OnTrade(const TradeDataEventMsg& msg) override;
    virtual void OnQuote(const QuoteDataEventMsg& msg) override; 
    virtual void OnBar(const BarEventMsg& msg) override; 

private: 
    void UpdateFairValue();
    void ExecuteArbitrage(double spread);

private: 
    const Instrument* etf_instrument_;
    std::map<const Instrument*, double> basket_weights_; 
    std::map<const Instrument*, double> last_prices_;    
    
    double entry_threshold_;
    double exit_threshold_; // Unused currently, but good to have
    double position_size_; // Changed to double for better precision with weights
};