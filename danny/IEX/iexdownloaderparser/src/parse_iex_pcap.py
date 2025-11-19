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
import os
from time import timezone
from datetime import date
import pytz
from math import floor
import calendar



#Note to students: your copy is called "stockbook.py" and thus uses the second import below (this is just so I can toggle between your version and mine, inside stockbook_implemented.py)
# if 'USE_IMPLEMENTED' in os.environ:
    # from stockbook_implemented import StockBook
# else:
from stockbook import StockBook
import gzip
from pickle import NONE



#Note if running with pypy instead of default python interpreter, may need to run the following which will make sure pip is installed with pypy and then install the pytz library
#pypy -m ensurepip
#pypy -mpip install pytz


#In order to run parsing ALL files will probably need to increase the number of max open files, at least on linux this can be done with:
#ulimit -n 102400

#Note snippet for invoking this via command line without having to extract or convert the original downloaded IEX DEEP pcap files:
#gunzip -d -c data_feeds_20191031_20191031_IEXTP1_DEEP1.0.pcap.gz | tcpdump -r - -w - -s 0 | python2 ~/dev/20191107_iex_parser/ie598_sp2019_iex/src/parse_iex_pcap.py /dev/stdin

#Snippet to forloop the above:
#for file in $(ls ~/Downloads/data_feeds*); do gunzip -d -c $file | tcpdump -r - -w - -s 0 | python2 ~/dev/20191107_iex_parser/ie598_sp2019_iex/src/parse_iex_pcap.py /dev/stdin; done

class BasicPcapParser():
    def __init__(self, filename, symbols_of_interest, trades_output_filename, book_updates_output_filename, timestamp_output_filename, num_price_levels):
        self.filename = filename
        self.trades_output_filename = trades_output_filename
        self.book_updates_output_filename = book_updates_output_filename
        self.timestamp_output_filename = timestamp_output_filename
        self.num_price_levels = num_price_levels 
        
        self.trades_per_symbol_output_file_hash = {} #dictionary to store each individual stock's trades output file for that specific date
        
        #Generate a dictionary mapping each symbol of interest to a StockBook object
        self.symbol_to_book_dictionary = {}
        
        self.open_files_list = []
        
        self.print_stdout = False
        
        self.output_gz = True #if true will generate CSV files wrapped in gzip instead of just plain CSV files
        
        #This assumes that symbols_of_interest contains a single string containing comma separated list of stock symbols to output. the below creates a list containing each individually
        if symbols_of_interest is not None:
            self.symbols_list = symbols_of_interest.split(",")
            for symbol in self.symbols_list:
                self.add_symbol_of_interest(symbol)
            self.add_all_symbols = False
        else: #else assume ALL symbols are of interest... will initialize based on stock directory information
            self.symbols_list = None
            self.add_all_symbols = True

        self.cur_packet_message_count = 0
        self.total_num_messages_processed = 0
        
        #precreate the Struct decoders for several of the most invoked struct decoders (to only create once instead of once per function call)
        self.pcap_packet_header_struct = struct.Struct("IIII").unpack
        self.iex_packet_header_struct = struct.Struct("bbHIIHHQQQ").unpack
        
        #######
        #Begin init output files
        #For purposes of providing students with market data to backtest, only concerned for now with trade messages, assume one file per message
        if trades_output_filename is not None:
            if self.output_gz is False:
                self.trades_output_file = open(self.trades_output_filename, "w")
            else:
                self.trades_output_filename = "%s.gz" % (self.trades_output_filename)
                self.trades_output_file = gzip.open(self.trades_output_filename, "wt")
            self.open_files_list.append(self.trades_output_file)
            self.trades_output_file.write("COLLECTION_TIME,MESSAGE_ID,MESSAGE_TYPE,SYMBOL,PRICE,SIZE,TRADE_ID,TRADE_FLAGS\n")
        else:
            self.trades_output_file = None
        
        
        # self.book_updates_output_file = None
        # self.timestamp_output_file    = None
        
        if book_updates_output_filename is not None:
            if self.output_gz is False:
                self.book_updates_output_file = open(self.book_updates_output_filename, "w")
            else: #else open up gzipped 
                self.book_updates_output_filename = "%s.gz" % (self.book_updates_output_filename)
                self.book_updates_output_file = gzip.open(self.book_updates_output_filename, "wt")
                
            self.open_files_list.append(self.book_updates_output_file)
            columns = [ "COLLECTION_TIME", "MESSAGE_ID", "MESSAGE_TYPE", "SYMBOL" ]
            for i in range(0, self.num_price_levels):
                columns.append("BID_PRICE_%d" % (i+1))
                columns.append("BID_SIZE_%d" % (i+1))
            for i in range(0, self.num_price_levels):
                columns.append("ASK_PRICE_%d" % (i+1))
                columns.append("ASK_SIZE_%d" % (i+1))
             
            book_updates_csv_header = ",".join(columns)
            self.book_updates_output_file.write("%s\n" % (book_updates_csv_header))
        else: 
            self.book_updates_output_file = None
         
        if timestamp_output_filename is not None:
            self.timestamp_output_file = open(self.timestamp_output_filename, "w")
            self.timestamp_output_file.write("MESSAGE_ID,NETWORK_TIMESTAMP,SENDING_TIMESTAMP,EVENT_TIMESTAMP\n")
        else:
            self.timestamp_output_file = None
        #end init output files
        #######
#

    def close_all_files(self):
        for open_file in self.open_files_list:
            open_file.close()
        
    def add_symbol_of_interest(self, symbol):
        if symbol not in self.symbol_to_book_dictionary:
            print("interested in %s" % (symbol))
            self.symbol_to_book_dictionary[symbol] = StockBook(symbol)
    
    
    def parse(self, max_packets_to_parse):
        self.file = open(self.filename, "rb")
        
#         start_parse_time = time.localtime()
#         print("Starting parsing @ %s" % (time.strftime("%H:%M:%S", start_parse_time)))
        start_parse_time = datetime.datetime.now()
        print("Starting parsing @ %s" % (start_parse_time))
        pcap_header_len = 4 + 2 + 2 + 4 + 4 + 4 + 4
        byte = self.file.read(pcap_header_len)
        
        (magic_number, version_major, version_minor, this_zone, sigfigs, snaplen, network) = struct.unpack("IHHiIII", byte)
        
        #TODO: add back basic verification of magic number, versions etc, to detect when accidentally parsing pcapng instead of regular pcap files!
        
        num_packets = 0
        
        print("packet_timestamp,message_timestamp,symbol,size,price")
        while True:
            time_float = self.read_packet()
            num_packets = num_packets + 1
            
            if max_packets_to_parse is not None and num_packets > max_packets_to_parse:
                packet_time = datetime.datetime.fromtimestamp(time_float).strftime('%c')
                print("%s: %d packets processed" % (packet_time, num_packets))
                stop_parse_time = datetime.datetime.now()
                print("Stopped parsing @ %s" % (stop_parse_time))
#                 print("Stopping parsing @ %s" % (time.strftime("%H:%M:%S", stop_parse_time)))
                parsing_time = stop_parse_time - start_parse_time
                print("Parsed %d packets in %s" % (num_packets, parsing_time))
                print("Closing all output files")
                self.close_all_files()
                sys.exit(0)
            
            #every 100kth packet, print an update on the number of packets parsed and the current time (within the pcap packets timestamps) to track progress
            if num_packets % 100000 == 0:
#                 packet_time = datetime.datetime.fromtimestamp(int((time_float*1e9)//1e9)).strftime('%c')
                packet_time = datetime.datetime.fromtimestamp(time_float).strftime('%c')
                print("Parsed %d packets: %s" % (num_packets, packet_time))
        print("Finished end of parsing loop")
        self.file.close()
#         self.read_packet()
#         self.read_packet()
#         print("Finished processing all packets in pcap file")
    
    def read_packet(self):
#         typedef struct pcaprec_hdr_s {
#         guint32 ts_sec;         /* timestamp seconds */
#         guint32 ts_usec;        /* timestamp microseconds */
#         guint32 incl_len;       /* number of octets of packet saved in file */
#         guint32 orig_len;       /* actual length of packet */
#         } pcaprec_hdr_t;
        packet_header_len = 4 + 4 + 4 + 4
        
        bytes = self.file.read(packet_header_len)
        if bytes == '' or len(bytes) != 16:
            print("End of file reached... terminating!")
            self.close_all_files()
            sys.exit()
        #(ts_sec, ts_usec, incl_len, orig_len) = struct.unpack("IIII", bytes)
        (ts_sec, ts_usec, incl_len, orig_len) = self.pcap_packet_header_struct(bytes)
        
#         print("ts_usec: %d\nts_usec: %d\nincl_len: %d\norig_len: %d\n" % (ts_sec, ts_usec, incl_len, orig_len))
        time_float = ts_sec + (ts_usec * 1e-6)
        packet_capture_time_in_nanoseconds = (ts_sec * 1e9) + (ts_usec * 1e3)
        #packet_time = datetime.datetime.fromtimestamp(time_float).strftime('%c')
        
        #print the packet capture time as a human readable string - work in progress needs to be validated
        if False:
            packet_time_datetime = datetime.datetime.fromtimestamp(time_float)
            ss_formatted_collection_time_string = "PCAP Packet Capture Time: %s.%s" % (packet_time_datetime.strftime("%Y-%m-%d %H:%M:%S"), ts_usec)
            print(ss_formatted_collection_time_string)
            
        packet_payload_bytes = self.file.read(incl_len)
        
        #hard coded for the particular eth frame size (no vlans), IP (no additoinal headers), and UDP
        #FYI: students, dont do this normally, use proper parser that handles that various protocols above can have other lengths
        offset_into_iex_payload = 14 + 20 + 8
        iex_payload = packet_payload_bytes[offset_into_iex_payload:]
#         print(iex_payload)
        self.parse_iex_payload(iex_payload, packet_capture_time_in_nanoseconds)
        return time_float
#         print("\n")
        
    @staticmethod
    def convert_epoch_nanoseconds_to_datetime_string(nanoseconds_epoch, output_microseconds=False):
        epoch_seconds = floor(nanoseconds_epoch * 1e-9)
        epoch_partial_seconds = nanoseconds_epoch - int(epoch_seconds * 1e9)
        
        #Construct the "2019-10-30 06:20:51" portion of the datetime string (everything but the fractional seconds)
        sending_timestamp_string_containing_date_and_time_to_second = datetime.datetime.utcfromtimestamp(epoch_seconds).strftime('%Y-%m-%d %H:%M:%S')
        
        #Construct the fractional seconds portion of the string (i.e. "473258426")
        if output_microseconds is False: #then output partial nanoseconds
            fractional_seconds_string = "%09d" % epoch_partial_seconds
        else:
            fractional_seconds_string = "%06d" % int(round(epoch_partial_seconds/1000.0)) #convert from nanoseconds to microseconds
        
        full_date_time_fractional_seconds_string = "%s.%s" % (sending_timestamp_string_containing_date_and_time_to_second, fractional_seconds_string)
        
        return_string = "%s" % (full_date_time_fractional_seconds_string)
#         print(return_string)
        return return_string
    
    def parse_iex_payload(self, payload, packet_capture_time_in_nanoseconds):
        #version 1 byte
        #reserved 1
        #message protocol id 2
        #channel id 4
        #session id 4
        #payload length 2
        #message count 2
        #stream offset 8
        #first message seq num 8
        #sendtime 8 (timestamp format)
        
        #c = char (bytes)
        #b = signed char (but int)
        #B = uchar (but int)
        #Q = uint64_t
        #(version, reserved, protocol_id, channel_id, session_id, payload_len, message_count, stream_offset, first_msg_seq_num, send_time) = 
        #struct.unpack("bb")
        
#         print (len(payload))
        #(version, reserved, protocol_id, channel_id, session_id, payload_len, message_count, stream_offset, first_msg_seq_num, send_time) = struct.unpack("bbHIIHHQQQ", payload[0:40])
        (version, reserved, protocol_id, channel_id, session_id, payload_len, message_count, stream_offset, first_msg_seq_num, send_time) = self.iex_packet_header_struct(payload[0:40])
        # print("%d\t%d\t%d\t%d\t%d\t%d\t%d\t%ld\t%ld\t%ld" % (version, reserved, protocol_id, channel_id, session_id, payload_len, message_count, stream_offset, first_msg_seq_num, send_time))
        
        #sanity checks on protocol
        if len(payload) != payload_len + 40: #the number fourty comes from the length of standard IEX header which is fourty bytes. the payload length (amount of data inside the message) should be equal to length of full IEX message (which includes header) minus the header length
            raise Exception("Invalid parser state; the length of UDP packet payload should be fourty plus the payload_len within IEX header")
        
        message_bytes = payload[40:]
        
        cur_offset = 0
        self.cur_packet_message_count = message_count
        for i in range(0, message_count):
            self.total_num_messages_processed = self.total_num_messages_processed + 1
            message_id = self.total_num_messages_processed
#             print("Processing message %d where packet started on %d" % (self.total_num_messages_processed, first_msg_seq_num))
            #message_len 2
            #message data (variable)
            (tuple_message_len) = struct.unpack("H", message_bytes[cur_offset:cur_offset+2])
            message_len = tuple_message_len[0]
#             print("Message of len: %d" % (message_len))
            self.parse_iex_message(message_id, packet_capture_time_in_nanoseconds, send_time, message_bytes[cur_offset+2:cur_offset+2+message_len])
            cur_offset = cur_offset + 2 + message_len
            
#         print("Cur offset: %d" % (cur_offset))
        
        #sanity check: should now have parsed all bytes exactly
        if cur_offset != payload_len:
            raise Exception("Invalid parser state; cur_offset after parsing all messages within packet should be equal to IEX header reported payload_len")
        
        
    
    def parse_iex_message(self, message_id, packet_capture_time_in_nanoseconds, send_time, message_payload):
        message_type_byte = struct.unpack("c", message_payload[:1])[0]
        message_type = message_type_byte.decode() # convert from byte to char / string
#         print("\tMessage Type: %c" % (message_type))
#         message_type_raw = message_payload[:1]
#         print("%c vs %c" % (message_type, message_type_raw))
        message_event_timestamp = None # will be set (where available) to the internal timestamp of the particular message / event (presumably from OME?)
        if message_type == 'S':
            self.parse_system_event(message_payload)
            pass
        elif message_type == 'H':
            self.parse_trading_status_message(message_payload)
            pass
        elif message_type == 'O':
            self.parse_operational_halt_message(message_payload)
            pass
        elif message_type == 'P':
            self.parse_short_sale_test_status_message(message_payload)
            pass
        elif message_type == '8':
            message_event_timestamp = self.parse_buy_price_level_update(message_id, packet_capture_time_in_nanoseconds, send_time, message_payload)
            pass
        elif message_type == '5':
            message_event_timestamp = self.parse_sell_price_level_update(message_id, packet_capture_time_in_nanoseconds, send_time, message_payload)
            pass
        elif message_type == 'T':
            message_event_timestamp = self.parse_trade_report_message(message_id, packet_capture_time_in_nanoseconds, send_time, message_payload)
#             pass
        elif message_type == 'E':
            self.parse_security_event_message(message_payload)
        elif message_type == 'D':
            self.parse_security_directory_message(message_payload)
        elif message_type == 'A':
            pass #do not handle auction information for now
        elif message_type == 'X': 
            pass #do not handle "Official Price Message" (opening / closing price for IEX-listed stocks, which right now is just IB)
        elif message_type == 'B': 
            pass #do not handle Trade Break message; note first time this was observed myself was on 2020-03-09 (during the COVID crashes / trading halts)
        elif message_type == 'I':
            pass #do not handle Retail Liquidity Indicator Message for now
        else:
            print("Unhandled message type: %c" % (message_type)) 
            raise Exception("Unhandled message type: %c" % (message_type))
        
        if message_event_timestamp is not None and self.timestamp_output_file is not None:
            timestamp_output_string = "%d,%d,%d,%d\n" % (message_id, packet_capture_time_in_nanoseconds, send_time, message_event_timestamp)
            self.timestamp_output_file.write(timestamp_output_string)
                
    
    def parse_system_event(self, payload):
        (system_event, timestamp_raw) = struct.unpack("=cQ", payload[1:])
#         print("\tSystem event: %c\ttimestamp_raw: %ld" % (system_event.decode(), timestamp_raw))

    def parse_trading_status_message(self, payload):
#         print(len(payload))
        (trading_status, timestamp_raw, symbol_raw, reason_raw) = struct.unpack("=cQ8s4s", payload[1:])
        symbol = symbol_raw.decode()
#         reason = reason_raw.decode()
        reason = reason_raw
#         print("\ttimestamp_raw: %ld\tsymbol: %s\treason: %s" % (timestamp_raw, symbol, reason))
    
    
    def parse_operational_halt_message(self, payload):
        (halt_status, timestamp_raw, symbol_raw) = struct.unpack("=cQ8s", payload[1:])
        symbol = symbol_raw.decode()
#         print("\tHalt status: %c\ttimestamp_raw: %ld\tsymbol: %s" % (halt_status.decode(), timestamp_raw, symbol))
    
        
    def parse_short_sale_test_status_message(self, payload):
        (short_sale_price_status, timestamp_raw, symbol_raw, detail_raw) = struct.unpack("=cQ8sc", payload[1:])
        symbol = symbol_raw.decode()
        detail = detail_raw.decode()
#         print("\tShort Sale Price status: %c\ttimestamp_raw: %ld\tsymbol: %s\tdetail: %s" % (short_sale_price_status.decode(), timestamp_raw, symbol, detail))
    
    def parse_security_directory_message(self, payload):
        (flags, timestamp_raw, symbol_raw, round_lot_size, adjusted_poc_price, luld_tier) = struct.unpack("=cQ8sIQc", payload[1:])
        symbol = symbol_raw.decode().rstrip()
        if self.add_all_symbols is True:
            self.add_symbol_of_interest(symbol)
        return
    
    
    def parse_price_level_update(self, message_id, packet_capture_time_in_nanoseconds, send_time, payload, buy_or_sell):
        (event_flags, timestamp_raw, symbol_raw, size, price_raw) = struct.unpack("=cQ8sIQ", payload[1:])
        
        #uncomment below to not output price levels
        # return timestamp_raw
        
        symbol = symbol_raw.decode().rstrip() #convert from bytes to string and remove trailing whitespace
        
        #check if this message is even for a symbol we are tracking, else return immediately (skip additional processing)
        if self.add_all_symbols is True and symbol not in self.symbol_to_book_dictionary:
            self.add_symbol_of_interest(symbol)
        
        if symbol not in self.symbol_to_book_dictionary:
            return timestamp_raw
        
        price = price_raw * 1e-4
        event_flags_txt = ""
        if event_flags == b'\0':
            event_flags_txt = "Processing Event"
        elif event_flags == b'\1':
            event_flags_txt = "Event processing completed"
        
        
        symbol_book = self.symbol_to_book_dictionary[symbol]    
        
        if buy_or_sell == "BID":
            symbol_book.on_buy_price_level_update(price, size)
        elif buy_or_sell == "ASK":
            symbol_book.on_sell_price_level_update(price, size)
            
        if event_flags == b'\1' and False:
            # num_price_levels_to_print = 5
            if symbol_book.get_min_book_depth() >= num_price_levels_to_print:
                symbol_book.print_price_levels(send_time, num_price_levels_to_print)
            
        
        collection_time_string = self.convert_epoch_nanoseconds_to_datetime_string(packet_capture_time_in_nanoseconds)
        source_time_string = self.convert_epoch_nanoseconds_to_datetime_string(send_time)
        
#         if event_flags == b'\0':
#         print("Book After: %s Side Price Level Update: %s\ttimestamp_raw: %ld\tsymbol: %s\tprice: %f\tsize: %d" % (buy_or_sell, event_flags_txt, timestamp_raw, symbol, price_float, size))
        if event_flags == b'\1' and symbol_book.get_min_book_depth() >= self.num_price_levels: 
            book_update_string = symbol_book.get_price_level_snapshot_string(self.num_price_levels)
            if self.book_updates_output_file is not None:
                event_output_string = "%s,%d,%s_UPDATE,%s,%s\n" % (collection_time_string, message_id, buy_or_sell, symbol, book_update_string)
                self.book_updates_output_file.write(event_output_string)
            if False: #for now dont print book related just to speed up demo for class
                print("%s:%s" % (self.book_updates_output_filename, event_output_string[:-1]))
        
        if buy_or_sell == "BID":
            side_int = 1
        elif buy_or_sell == "ASK":
            side_int = 2
        else:
            raise Exception("Invalid state; unknown value for buy_or_sell (%s); should be either BID or ASK" % (buy_or_sell))
        
        if event_flags == b'\0':
            is_partial_int = 1 #for StrategyStudy implies it is a partial event
        elif event_flags == b'\1':
            is_partial_int = 0
        else:
            raise Exception("Invalid IEX event_flag (%d); expecting either binary value of 0 or 1" % (int(event_flags)))
            
        seq_num = int(message_id)
        feed_type = 2 #2 for StrategyStudio refers to direct data feed (vs SIP or depth)
        book_price_level_output_string = "%s,%s,%d,P,IEX,%d,%lf,%d,,,,%d\n" % (collection_time_string, source_time_string, seq_num, side_int, price, size, is_partial_int)
#         trade_output_string = "%d,TRADE,%s,%lf,%d,%d,%s\n" % (message_id, symbol, price, size, trade_id, sale_condition_string)
        if size is None:
            raise Exception("Strange size")
        #trade_output_string = "%d,TRADE,%s,%lf,%d,%d,%s\n" % (message_id, symbol, price, size, trade_id, sale_condition_string)
        
        #if self.trades_output_file is not None:
        #    self.trades_output_file.write(trade_output_string)
        symbol_output_file = self.get_symbol_trades_file(symbol, datetime.datetime.fromtimestamp(send_time//1000000000))
        symbol_output_file.write(book_price_level_output_string)
        if self.print_stdout is True:
            print("%s:%s" % (self.trades_output_filename, book_price_level_output_string[:-1]))
#       
        
        return timestamp_raw
    
    def parse_buy_price_level_update(self, message_id, packet_capture_time_in_nanoseconds, send_time, payload):
        return self.parse_price_level_update(message_id, packet_capture_time_in_nanoseconds, send_time, payload, "BID")
    
    def parse_sell_price_level_update(self, message_id, packet_capture_time_in_nanoseconds, send_time, payload):
        return self.parse_price_level_update(message_id, packet_capture_time_in_nanoseconds, send_time, payload, "ASK")
    
    @staticmethod
    def convert_trade_sale_condition_to_string(sale_condition_flags):
        #if python2, the type will be str instead of bytes
        if isinstance(sale_condition_flags,str):
            sale_condition_flags_int = ord(sale_condition_flags[0])
        #else if python3, will be bytes
        else:
            sale_condition_flags_int = int(sale_condition_flags[0])
        sale_condition_strings = []
        if sale_condition_flags_int & 0x80 != 0:
            sale_condition_strings.append("INTERMARKET_SWEEP")
        if sale_condition_flags_int & 0x40 != 0:
            sale_condition_strings.append("EXTENDED_HOURS")
        else:
            sale_condition_strings.append("REGULAR_HOURS")
        if sale_condition_flags_int & 0x20 != 0:
            sale_condition_strings.append("ODD_LOT")
        if sale_condition_flags_int & 0x10 != 0:
            sale_condition_strings.append("TRADE_THROUGH_EXEMPT")
        if sale_condition_flags_int & 0x08 != 0:
            sale_condition_strings.append("SINGLE_PRICE_CROSS")
        
        #Generate a single string containing all of the fields that encoded within the sale_condition_flags into a single string, separated by '|'
        sale_condition_string = "|".join(sale_condition_strings)
        return sale_condition_string
    
    def parse_trade_report_message(self, message_id, packet_capture_time_in_nanoseconds, send_time, payload):
        (sale_condition_flags, timestamp_raw, symbol_raw, size, price_raw, trade_id) = struct.unpack("=cQ8sIQQ", payload[1:])
        symbol = symbol_raw.decode().rstrip()
        
        if self.add_all_symbols is True and symbol not in self.symbol_to_book_dictionary:
            self.add_symbol_of_interest(symbol)
            
        #check if this message is even for a symbol we are tracking, else return immediately (skip additional processing)
        if symbol not in self.symbol_to_book_dictionary:
            return timestamp_raw
        
        price = price_raw * 1e-4
        
        sale_condition_string = BasicPcapParser.convert_trade_sale_condition_to_string(sale_condition_flags)
        
        #below two line snippet will convert epoch timpestamp in nanoseconds to a "second level" local time zone accurate human readable string, i.e. Mon May 15 08:30:59 2017
#         packet_time = datetime.datetime.fromtimestamp(send_time//1000000000)
#         packet_time_string = packet_time.strftime('%c')
        
        #Desired format for StrategyStudio:
        #convert_epoch_nanoseconds_to_datetime_string
        #COLLECTION_TIME,SOURCE_TIME,SEQ_NUM,TICK_TYPE,MARKET_CENTER,PRICE,SIZE[,FEED_TYPE,[SIDE[,TRADE_COND_TYPE,TRADE_COND]]]
        collection_time_string = self.convert_epoch_nanoseconds_to_datetime_string(packet_capture_time_in_nanoseconds)
        source_time_string = self.convert_epoch_nanoseconds_to_datetime_string(send_time)
        seq_num = int(message_id)
        #tick_type = "T" #StrategyStudio tick type code for trades
        market_center = "IEX"
        feed_type = 2 #2 for StrategyStudio refers to direct data feed (vs SIP or depth)
        trade_output_string = "%s,%s,%d,T,IEX,%lf,%d\n" % (collection_time_string, source_time_string, seq_num, price, size)
#         trade_output_string = "%d,TRADE,%s,%lf,%d,%d,%s\n" % (message_id, symbol, price, size, trade_id, sale_condition_string)
        if size is None:
            raise Exception("Strange size")
        #trade_output_string = "%d,TRADE,%s,%lf,%d,%d,%s\n" % (message_id, symbol, price, size, trade_id, sale_condition_string)
        
        #if self.trades_output_file is not None:
        #    self.trades_output_file.write(trade_output_string)
        symbol_output_file = self.get_symbol_trades_file(symbol, datetime.datetime.fromtimestamp(send_time//1000000000))
        symbol_output_file.write(trade_output_string)
        if self.print_stdout is True:
            print("%s:%s" % (self.trades_output_filename, trade_output_string[:-1]))
#         self.get_symbol_trades_file(symbol, datetime.datetime.fromtimestamp(send_time//1000000000))

        #Generate message that goes into the universal trades.csv file
        #format: "COLLECTION_TIME,MESSAGE_ID,MESSAGE_TYPE,SYMBOL,PRICE,SIZE,TRADE_ID,TRADE_FLAGS\n"),
        if self.trades_output_file is not None:
            trade_str = "%s,%d,T,%s,%f,%d,%d,%s\n" % (collection_time_string, message_id, symbol, price, size, trade_id, sale_condition_string)
            self.trades_output_file.write(trade_str)

        return timestamp_raw
    
    
    def get_symbol_trades_file(self, symbol, trade_date):
        #Note expected strategy studio format example: "tick_SPY_20191030.txt", so generate that string format below as expected filename
        
        if self.output_gz is False:
            filename_string = "tick_%s_%s.txt" % (symbol, trade_date.strftime('%Y%m%d'))
        else:
            filename_string = "tick_%s_%s.txt.gz" % (symbol, trade_date.strftime('%Y%m%d'))
#         print("Attempting to locate file for %s on %s: %s" % (symbol, trade_date, filename_string))
        
        #TODO: make this a command line arg
        #filename_string = "../data/output/%s" % (filename_string)
        filename_string = "data/text_tick_data/%s" % (filename_string)
        
        #if we haven't already created a tick file for this symbol on this day, do so and store in hash
        if filename_string not in self.trades_per_symbol_output_file_hash:
            if self.output_gz is False:
                symbol_trades_file = open(filename_string, "w")
                self.open_files_list.append(symbol_trades_file)
            else:
                symbol_trades_file = gzip.open(filename_string, "wt")
                self.open_files_list.append(symbol_trades_file)
            
            self.trades_per_symbol_output_file_hash[filename_string] = symbol_trades_file
            return symbol_trades_file
        else: #else we've already created, simply write the string
            return self.trades_per_symbol_output_file_hash[filename_string]
        
    
    def parse_security_event_message(self, payload):
        (security_event, timestamp_raw, symbol_raw) = struct.unpack("=cQ8s", payload[1:])
        symbol = symbol_raw.decode()
#         print("\tSecurity Event Message:\ttimestamp_raw: %ld\tsymbol" % (timestamp_raw, symbol))
#         print("\tSecurity Event Message")
        
        pass
        

#Note potential symbols of interest to dump for students:
#SPY VOO IVV
#QQQ
#TLT LQD HYG
#AAPL AMZN FB NFLX
#USO
#VXX
#TODO: add some inverse ETFs
    

if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise Exception("Invalid use; you need to specify command line options!")
    
    iex_pcap_file_to_parse = sys.argv[1]
    
    stocks_to_output = "SPY,IVV,VOO,VXX,QQQ,TLT,LQD,HYG,USO,SPXL,DDG,FINZ,OILD,PSQ,PST,SDS,MSFT,AAPL,AMZN,FB,GOOGL,GOOG,DIA,BA,UNH,AAPL,GS,HD,MCD,V,MMM,UTX,DIS,CAT,JNJ,TRV,JPM,IBM,PG,AXP,WMT,CVX,NKE,MRK,XOM,VZ,WBA,INTC,KO,DOW,CSCO,PFE"
    stocks_to_output = "SH,TCEHY,NPSNY,DELL,VMW,CYB"
    stocks_to_output = "BRK.A,BRK.B,AAPL,BAC,KO,AXP,KHC,MCO,USB,DVA,WFC,GM,CHTR,BK,VRSN,ABBV,SNOW,V,BMY,MRK,LSXMK,AMZN,MA,STNE"
    stocks_to_output = "SPY,IVV,VOO,VXX,QQQ,TLT,LQD,HYG,USO,SPXL,DDG,FINZ,OILD,PSQ,PST,SDS,MSFT,AAPL,AMZN,FB,GOOGL,GOOG,DIA,BA,UNH,AAPL,GS,HD,MCD,V,MMM,UTX,DIS,CAT,JNJ,TRV,JPM,IBM,PG,AXP,WMT,CVX,NKE,MRK,XOM,VZ,WBA,INTC,KO,DOW,CSCO,PFE,SH,TCEHY,NPSNY,DELL,VMW,CYB,BRK.A,BRK.B,AAPL,BAC,KO,AXP,KHC,MCO,USB,DVA,WFC,GM,CHTR,BK,VRSN,ABBV,SNOW,V,BMY,MRK,LSXMK,AMZN,MA,STNE"
    stocks_to_output = "SPY"
    #stocks_to_output = None
    
    
    #TODO: do NOT write code like this. use an actual python command line arg parsing library. this is hacked to together in interests of time
    
    if len(sys.argv) > 2: #assume if more than 2, then actually 4, contains --symbols
        if sys.argv[2] != "--symbols":
            raise Exception("Invalid argument: %s" % (sys.argv[2]))
        stocks_to_output = sys.argv[3]
    
        if stocks_to_output is "ALL":
            stocks_to_output = None
    
    # stocks_to_output = "SPY"
    
    if len(sys.argv) > 4:
        if sys.argv[4] != "--trade-date":
            raise Exception("Invalid argument: %s" % (sys.argv[4]))
        
        trade_date = sys.argv[5]
    
    if len(sys.argv) > 6:
        if sys.argv[6] != "--output-deep-books-too":
            raise Exception("Invalid argument: %s" % (sys.argv[6]))
        else:
            trades_output_file_name = "data/book_snapshots/%s_trades.csv" % (trade_date)
            book_updates_output_file_name = "data/book_snapshots/%s_book_updates.csv" % (trade_date)
            # timestamp_output_filename = "data/book_snapshots/%s_message_timestamps.csv"% (trade_date)
            timestamp_output_filename = None #disable this for now as the files are HUGE
    else:
        trades_output_file_name = None
        book_updates_output_file_name = None
        timestamp_output_filename = None
    
    
    max_packets_to_parse = 1e9
    
    
    
    
    num_price_levels_to_print = 3
    parser = BasicPcapParser(iex_pcap_file_to_parse, stocks_to_output, trades_output_file_name, book_updates_output_file_name, timestamp_output_filename, num_price_levels_to_print)
    
    should_benchmark = False #change me to True in order to benchmark code
    
    if should_benchmark is True:
        cProfile.run('parser.parse(max_packets_to_parse)')
    else:
        parser.parse(max_packets_to_parse)
    
    print("Finished parsing %s; closing all output files" % (iex_pcap_file_to_parse))
    parser.close_all_files()
