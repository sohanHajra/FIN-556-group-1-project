'''
Created on November 18, 2025
IEX DEEP+ (DPLS) Protocol Parser
@author: parser_author
'''

import struct
import datetime
import sys
import gzip
from math import floor


class DeepPlusParser:
    """
    Parser for IEX DEEP+ protocol messages.
    DEEP+ provides order-by-order depth of book with individual order tracking.
    """
    
    def __init__(self, filename, symbols_of_interest, output_filename, num_price_levels):
        self.filename = filename
        self.output_filename = output_filename
        self.num_price_levels = num_price_levels
        self.output_gz = True
        
        # Order book tracking: symbol -> order_id -> order_info
        self.order_books = {}
        
        # Symbol filtering
        if symbols_of_interest is not None:
            self.symbols_list = symbols_of_interest.split(",")
            self.symbol_filter = set(self.symbols_list)
            self.add_all_symbols = False
        else:
            self.symbols_list = None
            self.symbol_filter = set()
            self.add_all_symbols = True
        
        self.total_messages_processed = 0
        self.open_files_list = []
        
        # Pre-create struct decoders for performance
        self.pcap_packet_header_struct = struct.Struct("IIII").unpack
        self.iex_packet_header_struct = struct.Struct("bbHIIHHQQQ").unpack
        
        # Initialize output file
        if output_filename is not None:
            if self.output_gz:
                self.output_filename = f"{output_filename}.gz"
                self.output_file = gzip.open(self.output_filename, "wt")
            else:
                self.output_file = open(output_filename, "w")
            self.open_files_list.append(self.output_file)
            self.output_file.write("COLLECTION_TIME,MESSAGE_ID,MESSAGE_TYPE,SYMBOL,SIDE,ORDER_ID,SIZE,PRICE,TRADE_ID,FLAGS\n")
        else:
            self.output_file = None
    
    def close_all_files(self):
        """Close all open file handles."""
        for open_file in self.open_files_list:
            open_file.close()
    
    def add_symbol_of_interest(self, symbol):
        """Add a symbol to track."""
        if symbol not in self.symbol_filter:
            print(f"Tracking symbol: {symbol}")
            self.symbol_filter.add(symbol)
            self.order_books[symbol] = {}  # order_id -> {side, size, price}
    
    @staticmethod
    def convert_epoch_nanoseconds_to_datetime_string(nanoseconds_epoch):
        """Convert nanosecond epoch timestamp to human-readable string."""
        epoch_seconds = floor(nanoseconds_epoch * 1e-9)
        epoch_partial_seconds = nanoseconds_epoch - int(epoch_seconds * 1e9)
        
        datetime_string = datetime.datetime.utcfromtimestamp(epoch_seconds).strftime('%Y-%m-%d %H:%M:%S')
        fractional_seconds = f"{epoch_partial_seconds:09d}"
        
        return f"{datetime_string}.{fractional_seconds}"
    
    def parse(self, max_packets_to_parse=None):
        """Main parsing loop for pcap file."""
        self.file = open(self.filename, "rb")
        
        start_time = datetime.datetime.now()
        print(f"Starting DEEP+ parsing @ {start_time}")
        
        # Read pcap global header
        pcap_header_len = 24
        pcap_header = self.file.read(pcap_header_len)
        (magic_number, version_major, version_minor, this_zone, 
         sigfigs, snaplen, network) = struct.unpack("IHHiIII", pcap_header)
        
        num_packets = 0
        
        while True:
            time_float = self.read_packet()
            if time_float is None:
                break
            
            num_packets += 1
            
            if max_packets_to_parse is not None and num_packets > max_packets_to_parse:
                break
            
            # Progress update every 100k packets
            if num_packets % 100000 == 0:
                packet_time = datetime.datetime.fromtimestamp(time_float).strftime('%c')
                print(f"Parsed {num_packets} packets: {packet_time}")
        
        end_time = datetime.datetime.now()
        print(f"Finished parsing @ {end_time}")
        print(f"Parsed {num_packets} packets in {end_time - start_time}")
        print(f"Total messages processed: {self.total_messages_processed}")
        
        self.file.close()
        self.close_all_files()
    
    def read_packet(self):
        """Read a single pcap packet."""
        packet_header_len = 16
        bytes_read = self.file.read(packet_header_len)
        
        if not bytes_read or len(bytes_read) != 16:
            return None
        
        (ts_sec, ts_usec, incl_len, orig_len) = self.pcap_packet_header_struct(bytes_read)
        time_float = ts_sec + (ts_usec * 1e-6)
        packet_capture_time_ns = (ts_sec * 1e9) + (ts_usec * 1e3)
        
        # Read packet payload
        packet_payload = self.file.read(incl_len)
        
        # Skip Ethernet (14) + IP (20) + UDP (8) headers = 42 bytes
        offset_into_iex_payload = 42
        iex_payload = packet_payload[offset_into_iex_payload:]
        
        self.parse_iex_payload(iex_payload, packet_capture_time_ns)
        
        return time_float
    
    def parse_iex_payload(self, payload, packet_capture_time_ns):
        """Parse IEX Transport Protocol payload containing DEEP+ messages."""
        if len(payload) < 40:
            return
        
        # Parse IEX-TP header
        (version, reserved, protocol_id, channel_id, session_id, 
         payload_len, message_count, stream_offset, first_msg_seq_num, 
         send_time) = self.iex_packet_header_struct(payload[0:40])
        
        # Verify protocol ID for DEEP+ (0x8005)
        if protocol_id != 0x8005:
            return
        
        message_bytes = payload[40:]
        cur_offset = 0
        
        for i in range(message_count):
            self.total_messages_processed += 1
            message_id = self.total_messages_processed
            
            # Read message length
            if cur_offset + 2 > len(message_bytes):
                break
            
            message_len = struct.unpack("H", message_bytes[cur_offset:cur_offset+2])[0]
            message_payload = message_bytes[cur_offset+2:cur_offset+2+message_len]
            
            self.parse_deepplus_message(message_id, packet_capture_time_ns, 
                                       send_time, message_payload)
            
            cur_offset += 2 + message_len
    
    def parse_deepplus_message(self, message_id, packet_time_ns, send_time, payload):
        """Route DEEP+ message to appropriate handler based on message type."""
        if len(payload) < 1:
            return
        
        message_type = chr(payload[0])
        
        # Administrative messages
        if message_type == 'S':
            self.parse_system_event(message_id, packet_time_ns, payload)
        elif message_type == 'D':
            self.parse_security_directory(message_id, packet_time_ns, payload)
        elif message_type == 'H':
            self.parse_trading_status(message_id, packet_time_ns, payload)
        elif message_type == 'O':
            self.parse_operational_halt(message_id, packet_time_ns, payload)
        elif message_type == 'P':
            self.parse_short_sale_test(message_id, packet_time_ns, payload)
        elif message_type == 'E':
            self.parse_security_event(message_id, packet_time_ns, payload)
        elif message_type == 'I':
            self.parse_retail_liquidity_indicator(message_id, packet_time_ns, payload)
        
        # Trading messages - order book updates
        elif message_type == 'a':  # Add Order (lowercase 'a')
            self.parse_add_order(message_id, packet_time_ns, send_time, payload)
        elif message_type == 'M':
            self.parse_order_modify(message_id, packet_time_ns, send_time, payload)
        elif message_type == 'R':
            self.parse_order_delete(message_id, packet_time_ns, send_time, payload)
        elif message_type == 'L':
            self.parse_order_executed(message_id, packet_time_ns, send_time, payload)
        elif message_type == 'T':
            self.parse_trade(message_id, packet_time_ns, send_time, payload)
        elif message_type == 'B':
            self.parse_trade_break(message_id, packet_time_ns, send_time, payload)
        elif message_type == 'C':
            self.parse_clear_book(message_id, packet_time_ns, send_time, payload)
    
    # Administrative Message Parsers
    
    def parse_system_event(self, message_id, packet_time_ns, payload):
        """Parse System Event Message (type S)."""
        (system_event, timestamp) = struct.unpack("=cQ", payload[1:10])
        # System events: O=Start, S=System Hours, R=Regular Hours, M=End Regular, E=End System, C=End Messages
    
    def parse_security_directory(self, message_id, packet_time_ns, payload):
        """Parse Security Directory Message (type D)."""
        (flags, timestamp, symbol_raw, round_lot_size, 
         adjusted_poc, luld_tier) = struct.unpack("=cQ8sIQc", payload[1:32])
        
        symbol = symbol_raw.decode().rstrip()
        
        if self.add_all_symbols:
            self.add_symbol_of_interest(symbol)
    
    def parse_trading_status(self, message_id, packet_time_ns, payload):
        """Parse Trading Status Message (type H)."""
        (trading_status, timestamp, symbol_raw, reason) = struct.unpack("=cQ8s4s", payload[1:23])
        # Trading status: H=Halted, O=Order Accept Period, P=Paused, T=Trading
    
    def parse_operational_halt(self, message_id, packet_time_ns, payload):
        """Parse Operational Halt Status Message (type O)."""
        (halt_status, timestamp, symbol_raw) = struct.unpack("=cQ8s", payload[1:19])
    
    def parse_short_sale_test(self, message_id, packet_time_ns, payload):
        """Parse Short Sale Price Test Status Message (type P)."""
        (test_status, timestamp, symbol_raw, detail) = struct.unpack("=cQ8sc", payload[1:20])
    
    def parse_security_event(self, message_id, packet_time_ns, payload):
        """Parse Security Event Message (type E)."""
        (security_event, timestamp, symbol_raw) = struct.unpack("=cQ8s", payload[1:19])
        # Events: O=Opening Complete, C=Closing Complete
    
    def parse_retail_liquidity_indicator(self, message_id, packet_time_ns, payload):
        """Parse Retail Liquidity Indicator Message (type I)."""
        (rli, timestamp, symbol_raw) = struct.unpack("=cQ8s", payload[1:19])
    
    # Trading Message Parsers (Order Book Updates)
    
    def parse_add_order(self, message_id, packet_time_ns, send_time, payload):
        """Parse Add Order Message (type 'a' - lowercase)."""
        (side, timestamp, symbol_raw, order_id, size, price_raw) = struct.unpack(
            "=cQ8sQIQ", payload[1:39])
        
        symbol = symbol_raw.decode().rstrip()
        
        # Check if we're tracking this symbol
        if not self.add_all_symbols and symbol not in self.symbol_filter:
            return
        
        if self.add_all_symbols and symbol not in self.symbol_filter:
            self.add_symbol_of_interest(symbol)
        
        price = price_raw * 1e-4  # Price has 4 implied decimal places
        side_str = "BUY" if side == b'8' else "SELL"
        
        # Track order in book
        if symbol not in self.order_books:
            self.order_books[symbol] = {}
        
        self.order_books[symbol][order_id] = {
            'side': side_str,
            'size': size,
            'price': price
        }
        
        # Write to output
        if self.output_file:
            collection_time = self.convert_epoch_nanoseconds_to_datetime_string(packet_time_ns)
            output_line = f"{collection_time},{message_id},ADD_ORDER,{symbol},{side_str},{order_id},{size},{price},,\n"
            self.output_file.write(output_line)
    
    def parse_order_modify(self, message_id, packet_time_ns, send_time, payload):
        """Parse Order Modify Message (type M)."""
        (modify_flags, timestamp, symbol_raw, order_id_ref, 
         new_size, new_price_raw) = struct.unpack("=cQ8sQIQ", payload[1:39])
        
        symbol = symbol_raw.decode().rstrip()
        
        if not self.add_all_symbols and symbol not in self.symbol_filter:
            return
        
        new_price = new_price_raw * 1e-4
        
        # Update order in book
        if symbol in self.order_books and order_id_ref in self.order_books[symbol]:
            order = self.order_books[symbol][order_id_ref]
            order['size'] = new_size
            order['price'] = new_price
            
            if self.output_file:
                collection_time = self.convert_epoch_nanoseconds_to_datetime_string(packet_time_ns)
                output_line = f"{collection_time},{message_id},MODIFY_ORDER,{symbol},{order['side']},{order_id_ref},{new_size},{new_price},,\n"
                self.output_file.write(output_line)
    
    def parse_order_delete(self, message_id, packet_time_ns, send_time, payload):
        """Parse Order Delete Message (type R)."""
        (reserved, timestamp, symbol_raw, order_id_ref) = struct.unpack(
            "=cQ8sQ", payload[1:27])
        
        symbol = symbol_raw.decode().rstrip()
        
        if not self.add_all_symbols and symbol not in self.symbol_filter:
            return
        
        # Remove order from book
        if symbol in self.order_books and order_id_ref in self.order_books[symbol]:
            order = self.order_books[symbol].pop(order_id_ref)
            
            if self.output_file:
                collection_time = self.convert_epoch_nanoseconds_to_datetime_string(packet_time_ns)
                output_line = f"{collection_time},{message_id},DELETE_ORDER,{symbol},{order['side']},{order_id_ref},,,\n"
                self.output_file.write(output_line)
    
    def parse_order_executed(self, message_id, packet_time_ns, send_time, payload):
        """Parse Order Executed Message (type L)."""
        (sale_flags, timestamp, symbol_raw, order_id_ref, 
         exec_size, exec_price_raw, trade_id) = struct.unpack(
            "=cQ8sQIQQ", payload[1:47])
        
        symbol = symbol_raw.decode().rstrip()
        
        if not self.add_all_symbols and symbol not in self.symbol_filter:
            return
        
        exec_price = exec_price_raw * 1e-4
        
        # Update order size in book
        if symbol in self.order_books and order_id_ref in self.order_books[symbol]:
            order = self.order_books[symbol][order_id_ref]
            order['size'] -= exec_size
            
            # Remove if fully executed
            if order['size'] <= 0:
                self.order_books[symbol].pop(order_id_ref)
            
            if self.output_file:
                collection_time = self.convert_epoch_nanoseconds_to_datetime_string(packet_time_ns)
                flags_str = self.decode_sale_flags(sale_flags)
                output_line = f"{collection_time},{message_id},EXECUTION,{symbol},{order['side']},{order_id_ref},{exec_size},{exec_price},{trade_id},{flags_str}\n"
                self.output_file.write(output_line)
    
    def parse_trade(self, message_id, packet_time_ns, send_time, payload):
        """Parse Trade Message (type T) - non-displayed order trade."""
        (sale_flags, timestamp, symbol_raw, size, price_raw, 
         trade_id) = struct.unpack("=cQ8sIQQ", payload[1:39])
        
        symbol = symbol_raw.decode().rstrip()
        
        if not self.add_all_symbols and symbol not in self.symbol_filter:
            return
        
        price = price_raw * 1e-4
        
        if self.output_file:
            collection_time = self.convert_epoch_nanoseconds_to_datetime_string(packet_time_ns)
            flags_str = self.decode_sale_flags(sale_flags)
            output_line = f"{collection_time},{message_id},TRADE,{symbol},,{trade_id},{size},{price},{trade_id},{flags_str}\n"
            self.output_file.write(output_line)
    
    def parse_trade_break(self, message_id, packet_time_ns, send_time, payload):
        """Parse Trade Break Message (type B)."""
        (sale_flags, timestamp, symbol_raw, size, price_raw, 
         trade_id) = struct.unpack("=cQ8sIQQ", payload[1:39])
        
        symbol = symbol_raw.decode().rstrip()
        
        if not self.add_all_symbols and symbol not in self.symbol_filter:
            return
        
        price = price_raw * 1e-4
        
        if self.output_file:
            collection_time = self.convert_epoch_nanoseconds_to_datetime_string(packet_time_ns)
            flags_str = self.decode_sale_flags(sale_flags)
            output_line = f"{collection_time},{message_id},TRADE_BREAK,{symbol},,{trade_id},{size},{price},{trade_id},{flags_str}\n"
            self.output_file.write(output_line)
    
    def parse_clear_book(self, message_id, packet_time_ns, send_time, payload):
        """Parse Clear Book Message (type C)."""
        (reserved, timestamp, symbol_raw) = struct.unpack("=cQ8s", payload[1:19])
        
        symbol = symbol_raw.decode().rstrip()
        
        # Clear all orders for this symbol
        if symbol in self.order_books:
            self.order_books[symbol].clear()
            
            if self.output_file:
                collection_time = self.convert_epoch_nanoseconds_to_datetime_string(packet_time_ns)
                output_line = f"{collection_time},{message_id},CLEAR_BOOK,{symbol},,,,,,\n"
                self.output_file.write(output_line)
    
    @staticmethod
    def decode_sale_flags(sale_flags):
        """Decode sale condition flags into human-readable string."""
        if isinstance(sale_flags, str):
            flags_int = ord(sale_flags[0])
        else:
            flags_int = int(sale_flags[0])
        
        flags = []
        if flags_int & 0x80:
            flags.append("ISO")
        if flags_int & 0x40:
            flags.append("EXTENDED_HOURS")
        else:
            flags.append("REGULAR_HOURS")
        if flags_int & 0x20:
            flags.append("ODD_LOT")
        if flags_int & 0x10:
            flags.append("TRADE_THROUGH_EXEMPT")
        if flags_int & 0x08:
            flags.append("SINGLE_PRICE_CROSS")
        
        return "|".join(flags) if flags else "NORMAL"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_iex_deepplus.py <pcap_file> [--symbols SYMBOLS] [--output OUTPUT_FILE]")
        sys.exit(1)
    
    pcap_file = sys.argv[1]
    symbols = None
    output_file = "deepplus_orders.csv"
    
    # Simple argument parsing
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--symbols":
            symbols = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output":
            output_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    print(f"Parsing DEEP+ file: {pcap_file}")
    if symbols:
        print(f"Filtering symbols: {symbols}")
    else:
        print("Tracking all symbols")
    
    parser = DeepPlusParser(pcap_file, symbols, output_file, num_price_levels=10)
    parser.parse(max_packets_to_parse=None)
    
    print("Parsing complete!")
