#include <cstdint>
#include <vector>
#include <cstdio>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <chrono>
#include <thread>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <string>
#include <ctime>
// #include "DebugUtil.h"
#include "MessageHeader.h"
#include "MDInstrumentDefinitionSpread56.h"
#include "MDIncrementalRefreshOrderBook47.h"
#include "MDInstrumentDefinitionOption55.h"
#include "MDInstrumentDefinitionFuture54.h"
#include "MDIncrementalRefreshBook46.h"
#include "AdminHeartbeat12.h"
using namespace std;
#pragma pack(push, 1)


void template46(char* buffer, uint64_t blocklength ,uint64_t bufferlength,uint64_t version,uint32_t timeSec, uint32_t timeUSec, stringstream& message){
            string result = "";
            mktdata::MDIncrementalRefreshBook46 temp2;
            temp2.wrapForDecode(buffer,10,blocklength,version,bufferlength);
            mktdata::MDIncrementalRefreshBook46::NoMDEntries mbofd = temp2.noMDEntries();
            std::chrono::seconds sec(timeSec);
            std::chrono::microseconds usec(timeUSec);

            // Create a time_point object
            std::chrono::time_point<std::chrono::system_clock> timestamp(sec + usec);

            // Convert to time_t for formatting
            std::time_t t = std::chrono::system_clock::to_time_t(timestamp);

            // Convert to UTC time
            struct tm *tm_info = std::gmtime(&t);

            // Convert to seconds (as we know the timestamp is in nanoseconds)
            time_t sec2 = temp2.transactTime() / 1000000000;  // seconds part
            int64_t ns = temp2.transactTime() % 1000000000;  // remaining nanoseconds part
            // cout << "Entered first 46 message" << endl;
            struct tm* tm_info2 = std::gmtime(&sec2);  // Convert to UTC time
            while(mbofd.hasNext()){
                // if(hasOne) message <<",";
                mbofd.next();
                // cout << "next" << endl;
                if(mbofd.securityID()==134373){
                    //CLM5
                    // message << ",{" << mbofd.orderID() << "," << mbofd.mDOrderPriority() << "," << mbofd.mDEntryPx() << "," << mbofd.mDDisplayQty() << "," << mbofd.securityID() << "," << mbofd.mDUpdateAction() << "," << mbofd.mDEntryType()<<"}";
                    double mantissa = mbofd.mDEntryPx().mantissa() * 1e-9;
                    int side = 0;
                    int numOrders = 0;
                    if(mbofd.mDEntryType()=='E'){
                        message << std::put_time(tm_info, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(6) << std::setfill('0') << timeUSec << ","<< std::put_time(tm_info2, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(9) << std::setfill('0') << ns<<",,P,CME," << "1" << "," << mantissa << ","<< mbofd.mDEntrySize() << ",0" << "," << "1" <<"\n";
                    }
                    else if(mbofd.mDEntryType()=='F'){
                        message << std::put_time(tm_info, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(6) << std::setfill('0') << timeUSec << ","<< std::put_time(tm_info2, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(9) << std::setfill('0') << ns<<",,P,CME," << "2" << "," << mantissa << ","<< mbofd.mDEntrySize() << ",0" << "," << "1" <<"\n";
                    }
                    else if(mbofd.mDEntryType()=='0'){
                        message << std::put_time(tm_info, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(6) << std::setfill('0') << timeUSec << ","<< std::put_time(tm_info2, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(9) << std::setfill('0') << ns<<",,P,CME," << "1" << "," << mantissa << ","<< mbofd.mDEntrySize() << "," <<mbofd.numberOfOrders()<< "," << "0" <<"\n";
                    }
                    else if(mbofd.mDEntryType()=='1'){
                        message << std::put_time(tm_info, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(6) << std::setfill('0') << timeUSec << ","<< std::put_time(tm_info2, "%Y-%m-%d %H:%M:%S")<< "." << std::setw(9) << std::setfill('0') << ns<<",,P,CME," << "2" << "," << mantissa << ","<< mbofd.mDEntrySize() << "," <<mbofd.numberOfOrders()<< "," << "0" <<"\n";
                    }
                }
                // else if(mbofd.securityID()==423318){
                //     double mantissa = mbofd.mDEntryPx().mantissa() * 1e-9;
                //     message << mbofd.orderID() << "," << mbofd.mDOrderPriority() << "," << mantissa << "," << mbofd.mDDisplayQty() << "," << "CLK5" << "," << mbofd.mDUpdateAction() << "," << mbofd.mDEntryType()<<"\n";;
                // }

            }
            // message <<",,P,CME,"<< temp2;
        }
struct PcapGlobalHeader {
    uint32_t magic_number;
    uint16_t version_major;
    uint16_t version_minor;
    int32_t  thiszone;
    uint32_t sigfigs;
    uint32_t snaplen;
    uint32_t network;
};

struct PcapPacketHeader {
    uint32_t ts_sec;
    uint32_t ts_usec;
    uint32_t incl_len;
    uint32_t orig_len;
};

struct packet{
            mktdata::MessageHeader mh;
            char* buffer;
            int bufSize;
            int packetNum;
            uint32_t sec;
            uint32_t uSec;
        };
#pragma pack(pop)

int main(int argc, char* argv[]) {
    // const char* filename = "dc3-glbx-a-20250401T001000.pcap";
    const char* filename = argv[1];


    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cerr << "Failed to open pcap file: " << filename << std::endl;
        return 1;
    }

    // Open output file
    std::ofstream out(argv[2]);
    if (!out) {
        std::cerr << "Failed to open output.txt for writing" << std::endl;
        return 1;
    }

    // Read global header
    PcapGlobalHeader gh{};
    file.read(reinterpret_cast<char*>(&gh), sizeof(gh));

    out << "COLLECTION_TIME,SOURCE_TIME,SEQ_NUM,TICK_TYPE,MARKET_CENTER,SIDE,PRICE,SIZE,NUMBER_ORDERS,IS_IMPLIED" << endl;

    std::size_t packetCount = 0;
    mktdata::MessageHeader temp;
    stringstream content;
    // Loop over packets
    size_t addedPackets = 0;
    while (true) {
        PcapPacketHeader ph{};
        if (!file.read(reinterpret_cast<char*>(&ph), sizeof(ph))) {
            break;
        }

        std::vector<std::uint8_t> packet(ph.incl_len);
        if (!file.read(reinterpret_cast<char*>(packet.data()), ph.incl_len)) {
            break;
        }

        ++packetCount;

        // Write packet info to output.txt
        // out << "Packet #" << packetCount
        //     << " ts=" << ph.ts_sec << "." << ph.ts_usec
        //     << " incl_len=" << ph.incl_len
        //     << " orig_len=" << ph.orig_len << "\n";

        std::size_t showLen = std::min<std::size_t>(ph.incl_len, 16);
        // out << "  First " << showLen << " bytes: ";
        // for (std::size_t i = 0; i < showLen; ++i) {
        //     char buf[4];
        //     std::snprintf(buf, sizeof(buf), "%02x", packet[i]);
        //     out << buf << ' ';
        // }
        uint16_t version = (uint16_t(uint8_t(packet[63]))<<8) | (uint16_t(uint8_t(packet[62])));
        uint16_t messageSize = (uint16_t(uint8_t(packet[55]))<<8) | (uint16_t(uint8_t(packet[54])));;
        char* buf = reinterpret_cast<char*>(packet.data() + 54);
        temp.wrap(buf,2,version,showLen);
        if(temp.templateId()==46){
            template46(buf,temp.blockLength(),messageSize,temp.version(),ph.ts_sec,ph.ts_usec,content);
            addedPackets++;
        }
        if(addedPackets>=10000){
            out << content.str();
            content.str("");
            content.clear();
        }
        // out << "MessageSize " << messageSize << " " << temp.blockLength() << " " << temp.templateId() << " " << temp.schemaId() << " " << temp.version() << endl;
        // out << "\n";
    }

    // out << "Done. Total packets: " << packetCount << std::endl;
    return 0;
}
