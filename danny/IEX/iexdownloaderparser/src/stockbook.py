'''
Created on May 17, 2017

@author: dlariviere
'''
import unittest
import struct
import datetime
import sys
import cProfile
import time


class StockBook():
    def __init__(self, symbol):
        self.symbol = symbol
        # print("TODO: initialize additional required data structures for maintaining price levels of %s" % (symbol))
        self.per_stock_event_count = 0 #increase by one each time there is any change on this stock (trade or book update, at least)
        self.bid_price_levels = {} #dict mapping price to size at that price on bid side
        self.ask_price_levels = {} #dict mapping price to size at that price on bid side
        
        
    def on_buy_price_level_update(self, price, size):
        if size == 0 and price in self.bid_price_levels:
            del self.bid_price_levels[price]
            # print("%s: deleting bid price level %f" % ( self.symbol, price))
        else:
            self.bid_price_levels[price] = size
            # print("%s: updating bid price level %f = %d" % (self.symbol, price, size))
    
    def on_sell_price_level_update(self, price, size):
        if size == 0 and price in self.ask_price_levels:
            del self.ask_price_levels[price]
            # print("%s: deleting ask price level %f" % ( self.symbol, price))
        else:
            self.ask_price_levels[price] = size
            # print("%s: updating ask price level %f = %d" % (self.symbol, price, size))
    
    #Returns the minimum of the either number price levels on the bid or on the ask
    #used to determine when it is ok to start calling print_price_levels
    def get_min_book_depth(self):
        return min(len(self.ask_price_levels.keys()), len(self.bid_price_levels.keys()))

    #Assume num_levels = 2:
    #This function should dump a comma separated list of (price,size) pairs, starting with best bid through ("Nth" best bid) followed by best ask through "Nth" best ask)
    #Example:
    #    ASK (second price level): 260.03 x 200
    #    ASK (best   price level): 260.02 x 300
    #    BID (best   price level): 260.01 x 100
    #    BID (second price level): 260.00 x 400
    #This function would return a string "260.01,100,260.00,400,260.02,300,260.03,200"
    #
    #Example 2:
    #Same situation as above, except num_levels = 3
    #This function would return a string "260.01,100,260.00,400,NULL,NULL,260.02,300,260.03,200,NULL,NULL"
    #Note NULLs are used for cases where asking for more price levels than actually available in the order book
    def get_price_level_snapshot_string(self, num_levels):
        # for price in sorted(price_dict.keys()):
            # print("Price %f ==> %d" % (price, price_dict[price]))
        # return "TODO: dump %d price levels of %s into a single line" % (num_levels, self.symbol)
        
        # price_levels = [*self.bid_price_levels.keys()]
        # subset_price_levels = price_levels[0:num_levels]
        # print(subset_price_levels)
        price_levels_str = ""
        for price_level in sorted([*self.bid_price_levels.keys()], reverse=True)[0:num_levels]:
            price_levels_str = "%s%f,%d," % (price_levels_str, price_level, self.bid_price_levels[price_level])
        
        for price_level in sorted([*self.ask_price_levels.keys()])[0:num_levels]:
            price_levels_str = "%s%f,%d," % (price_levels_str, price_level, self.ask_price_levels[price_level])
        
        price_levels_str = price_levels_str[:-1] #remove last trailing comma
        return price_levels_str
    
    def print_price_levels(self,send_time, num_levels):
        print(self.get_price_level_snapshot_string(num_levels))


