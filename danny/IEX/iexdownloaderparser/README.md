# IexDownloaderParser

This project is designed to both automatically download and parse market data from IEX, including generating the file formats expected by Strategy Studio for backtesting. It will be intended to be easily usable by the Strategy Student Vagrant VM.

# Checkout and Usage

```
git clone git@gitlab.engr.illinois.edu:shared_code/iexdownloaderparser.git
cd iexdownloaderparser
./vm_go.sh
```



# Dependencies

## Downloader (substitute with whatever version of python interpreter you are using)
1. pypy3.7 -m pip install requests
2. pypy3.7 -m pip install tqdm


