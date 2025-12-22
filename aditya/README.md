# CME-PCAP-Decoder

A tool for parsing and processing CME PCAP (Packet Capture) files, and preparing the resulting data for backtesting and analysis.

## Parsing CME PCAPs

To parse CME PCAP files, follow the steps below:

### 1. **Compile the Decoder**

First, you need to compile the `StreamParse.cpp` file to generate the executable:

```bash
g++ StreamParse.cpp -o a.out
````

This will create the `a.out` executable that is used in the parsing process.

### 2. **Run the Multithreaded Parsing Script**

Next, you can run the `multithreadedParse.sh` script to parse PCAP files for a specific date.

Before running the script, make sure to edit the following parameters within the `multithreadedParse.sh`:

* **Input files**: Ensure the correct PCAP files are specified for parsing.
* **Output files**: Set the correct output file paths for storing the parsed data.
* **Number of cores**: Adjust the number of cores to maximize efficiency based on your machine's capabilities.

Example:

```bash
./multithreadedParse.sh
```

## Combining PCAPs

After parsing the files, you can combine all the tick files for a given day using the `combineData.sh` script. This is necessary to prepare the data for backtesting software.

Make sure to **zip the combined files** after merging them, as the backtesting software may require compressed files.

To combine data:

```bash
./combineData.sh
```

## Generating Updated Header Files

The tool used for compiling the header files can be found [here](https://github.com/real-logic/simple-binary-encoding). Follow the instructions on the page to download and use the **SBE-tool**.

### Important Notes:

* CME regularly releases updated XML schema files. Make sure you are using the **correct schema** version before generating header files and parsing the dates you need.

Visit the [SBE-tool documentation](https://github.com/real-logic/simple-binary-encoding) for further details.
