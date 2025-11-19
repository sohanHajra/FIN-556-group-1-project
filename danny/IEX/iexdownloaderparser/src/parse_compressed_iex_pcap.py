'''
Created on Novemeber 8, 2021

@author: dlariviere
'''
import sys
from subprocess import Popen,PIPE



'''
this script is intended to mimick in a single python script invoking the following:

do gunzip -d -c $file | tcpdump -r - -w - -s 0 | pypy parse_iex_pcap.py /dev/stdin; done

where $file is the path to some IEX compressed pcap file.

All three processes (gunzip, tcpudmp, and pypy) will be running in parallel
'''

def parse_compressed_pcap(filename, stocks_to_output):
    print("Will attempt to decompress, convert to normal pcap format, and decode %s" % (compressed_filename))
    
    default_buf_size = 16 * 1024 * 1024 # 16MB buffer
    
    python_interpreter = "python3"
    python_interpreter = "python3"
    
    gunzip_process  = Popen(["gunzip","-d", "-c", filename], bufsize=default_buf_size, stdout=PIPE)
    tcpdump_process = Popen(["tcpdump", "-r", "-", "-w", "-", "-s", "0"], bufsize=default_buf_size, stdin=gunzip_process.stdout, stdout=PIPE)
    if stocks_to_output is None:
        parse_process   = Popen([python_interpreter, "parse_iex_pcap.py", "/dev/stdin"], bufsize=default_buf_size, stdin=tcpdump_process.stdout, stdout=PIPE)
    else:
        parse_process   = Popen([python_interpreter, "parse_iex_pcap.py", "/dev/stdin", "--symbols", stocks_to_output], bufsize=default_buf_size, stdin=tcpdump_process.stdout, stdout=PIPE)
        
    #parse_process   = Popen(["tcpdump", "-r", "-"], universal_newlines=False, stdin=tcpdump_process.stdout, stdout=PIPE)
    
    
    while parse_process.poll() is None:
        l = parse_process.stdout.readline() # This blocks until it receives a newline.
        print(l)
        
    # When the subprocess terminates there might be unconsumed output 
    # that still needs to be processed.
    print(parse_process.stdout.read())

if __name__ == "__main__":
    print("Python interpreter: %s" % (sys.argv[0]))
    
    for count, arg in enumerate(sys.argv):
        print(count, arg)
    
    if len(sys.argv)<2:
        raise Exception("invalid number of arguments; expecting at least filename of compressed IEX pcap file")
    compressed_filename = sys.argv[1]
    
    #Optionally can add two more args in the form of "--symbol SPY,GLD,MSFT,GOOG" to request specific symbols
    if len(sys.argv) > 2: #assume if more than 2, then actually 4, contains --symbols
        if sys.argv[2] != "--symbols":
            raise Exception("Invalid argument: %s" % (sys.argv[2]))
        stocks_to_output = sys.argv[3]
    
        if stocks_to_output is "ALL":
            stocks_to_output = None
    else:
        stocks_to_output = None
    
    #TODO: consider modifying this code to simply pass all other args after the first two straight through to underlying
    
    parse_compressed_pcap(compressed_filename, stocks_to_output)
    
    sys.exit(0)
