#ifdef _WIN32
    #include "stdafx.h"
#endif

#include "EtfArbStrategy.h"

EtfArbStrategy::EtfArbStrategy(StrategyID strategyID, const std::string& strategyName, const std::string& groupName)
    : Strategy(strategyID, strategyName, groupName),
      etf_instrument_(nullptr),
      entry_threshold_(0.05), 
      exit_threshold_(0.01),
      position_size_(100) {
}

EtfArbStrategy::~EtfArbStrategy() {
}

void EtfArbStrategy::OnResetStrategyState() {
    last_prices_.clear();
}

void EtfArbStrategy::RegisterForStrategyEvents(StrategyEventRegister* eventRegister, DateType currDate) {
    // 1. Get the ETF (SPY)
    // In a real bot, we'd read this from params, but hardcoding for testing is fine
    if (instrument_manager()->TryGetInstrument("SPY", &etf_instrument_)) {
        eventRegister->RegisterForInstrument(etf_instrument_);
    }

    // 2. Get the Basket components
    // Weights are 1/3 each for simplicity
    std::vector<std::string> symbols = {"AAPL", "MSFT", "GOOG"};
    for (const auto& sym : symbols) {
        const Instrument* inst = nullptr;
        if (instrument_manager()->TryGetInstrument(sym, &inst)) {
            eventRegister->RegisterForInstrument(inst);
            basket_weights_[inst] = 1.0 / symbols.size(); 
            last_prices_[inst] = 0.0;
        }
    }
}

void EtfArbStrategy::OnTrade(const TradeDataEventMsg& msg) {
    const Instrument* instrument = msg.instrument();
    double price = msg.trade().price();

    // Cache the price
    if (instrument == etf_instrument_) {
        last_prices_[instrument] = price;
    } else if (basket_weights_.find(instrument) != basket_weights_.end()) {
        last_prices_[instrument] = price;
    }

    // Only calc if we have enough data
    UpdateFairValue();
}

void EtfArbStrategy::OnQuote(const QuoteDataEventMsg& msg) {}
void EtfArbStrategy::OnBar(const BarEventMsg& msg) {}

void EtfArbStrategy::UpdateFairValue() {
    // do we have the ETF and is its price valid?
    if (!etf_instrument_ || last_prices_[etf_instrument_] <= 0.0) return;

    double weighted_basket_sum = 0.0;
    int valid_components = 0;

    for (auto const& [inst, weight] : basket_weights_) {
        double price = last_prices_[inst];
        if (price > 0) {
            weighted_basket_sum += price * weight;
            valid_components++;
        }
    }

    // we don't arb if we're missing component data
    if (valid_components < basket_weights_.size()) return;

    double etf_price = last_prices_[etf_instrument_];
    double spread = etf_price - weighted_basket_sum;

    ExecuteArbitrage(spread);
}

void EtfArbStrategy::ExecuteArbitrage(double spread) {
    //Add position limit checks here so we don't blow up the account

    int current_position = portfolio()->position(etf_instrument_);
    int max_position = 100;

    // If we are already at max long position and spread indicates to buy more ETF, skip
    if (current_position >= max_position && spread < -entry_threshold_) {
        return;
    }
    // If we are already at max short position and spread indicates to sell more ETF, skip
    if (current_position <= -max_position && spread > entry_threshold_) {
        return;
    }

    
    if (spread > entry_threshold_) {
        // ETF is expensive -> Short ETF, Buy Basket
        // Sell ETF
        OrderParams etf_order(
            etf_instrument_, 
            position_size_, 
            last_prices_[etf_instrument_], 
            MARKET_CENTER_ID_IEX, 
            ORDER_SIDE_SELL, 
            ORDER_T11_NET_POSITION, 
            ORDER_TYPE_MARKET
        );
        trade_actions()->SendNewOrder(etf_order);

        // Buy Components
        for (auto const& [inst, weight] : basket_weights_) {
            OrderParams basket_order(
                inst, 
                position_size_ * weight, 
                last_prices_[inst], 
                MARKET_CENTER_ID_NASDAQ, 
                ORDER_SIDE_BUY, 
                ORDER_T11_NET_POSITION, 
                ORDER_TYPE_MARKET
            );
            trade_actions()->SendNewOrder(basket_order);
        }
    }
    else if (spread < -entry_threshold_) {
        // ETF is cheap -> Buy ETF, Short Basket
        
        // 1. Buy the ETF
        OrderParams etf_order(
            etf_instrument_, 
            position_size_, 
            last_prices_[etf_instrument_], 
            MARKET_CENTER_ID_IEX, 
            ORDER_SIDE_BUY, 
            ORDER_T11_NET_POSITION, 
            ORDER_TYPE_MARKET
        );
        trade_actions()->SendNewOrder(etf_order);

        // 2. Sell the Basket Components
        for (auto const& [inst, weight] : basket_weights_) {
            OrderParams basket_order(
                inst, 
                position_size_ * weight, 
                last_prices_[inst], 
                MARKET_CENTER_ID_NASDAQ, 
                ORDER_SIDE_SELL, 
                ORDER_T11_NET_POSITION, 
                ORDER_TYPE_MARKET
            );
            trade_actions()->SendNewOrder(basket_order);
        }
    }
}