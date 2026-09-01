#include <cstdint>
#include <vector>
#include <cstdio>
#include <iostream>
#include <fstream>
#include <sstream>
#include <chrono>
#include <iomanip>
#include <string>
#include <memory>
#include <stdexcept>

#include "MessageHeader.h"
#include "MDIncrementalRefreshBook46.h"

using namespace std;

#pragma pack(push, 1)

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

#pragma pack(pop)

// ---------- safe popen wrapper ----------
std::shared_ptr<FILE> popen_stream(const char* command) {
    std::shared_ptr<FILE> pipe(popen(command, "r"), pclose);
    if (!pipe) {
        throw std::runtime_error("popen() failed");
    }
    return pipe;
}

void template46(
    char* buffer,
    uint64_t blocklength,
    uint64_t bufferlength,
    uint64_t version,
    uint32_t timeSec,
    uint32_t timeUSec,
    std::ofstream& out
) {
    mktdata::MDIncrementalRefreshBook46 msg;
    msg.wrapForDecode(buffer, 10, blocklength, version, bufferlength);

    auto entries = msg.noMDEntries();

    std::time_t t = timeSec;
    struct tm* tm_info = std::gmtime(&t);

    time_t sec2 = msg.transactTime() / 1'000'000'000;
    int64_t ns = msg.transactTime() % 1'000'000'000;
    struct tm* tm_info2 = std::gmtime(&sec2);
    int32_t numOrders = 0;
    while (entries.hasNext()) {
        entries.next();

        if (entries.securityID() != 134373) continue;

        double price = entries.mDEntryPx().mantissa() * 1e-9;

        char side =
            (entries.mDEntryType() == 'E' || entries.mDEntryType() == '0') ? '1' : '2';

        int isImplied =
            (entries.mDEntryType() == '0' || entries.mDEntryType() == '1') ? 0 : 1;
        if(isImplied){
            numOrders = 0;
        }
        else{
            numOrders = entries.numberOfOrders();
        }
        out << std::put_time(tm_info, "%Y-%m-%d %H:%M:%S")
            << "." << setw(6) << setfill('0') << timeUSec << ","
            << std::put_time(tm_info2, "%Y-%m-%d %H:%M:%S")
            << "." << setw(9) << setfill('0') << ns
            << ",,P,CME,"
            << side << ","
            << price << ","
            << entries.mDEntrySize() << ","
            << numOrders << ","
            << isImplied
            << "\n";
    }
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " input.zst output.txt\n";
        return 1;
    }

    // ---------- open zstd stream ----------
    auto stream = popen_stream(
        ("zstd -d -c " + std::string(argv[1])).c_str()
    );

    std::ofstream out(argv[2], std::ios::out);
    if (!out) {
        std::cerr << "Failed to open output file\n";
        return 1;
    }

    // ---------- read global header ----------
    PcapGlobalHeader gh{};
    if (fread(&gh, sizeof(gh), 1, stream.get()) != 1) {
        std::cerr << "Invalid PCAP header\n";
        return 1;
    }

    out << "COLLECTION_TIME,SOURCE_TIME,SEQ_NUM,TICK_TYPE,"
           "MARKET_CENTER,SIDE,PRICE,SIZE,NUMBER_ORDERS,IS_IMPLIED\n";

    constexpr uint32_t MAX_PACKET_SIZE = 1 << 20; // 1 MB
    std::vector<uint8_t> packet;
    packet.reserve(65536);

    mktdata::MessageHeader mh;

    while (true) {
        PcapPacketHeader ph{};
        if (fread(&ph, sizeof(ph), 1, stream.get()) != 1)
            break;

        if (ph.incl_len == 0 || ph.incl_len > MAX_PACKET_SIZE)
            break;

        packet.resize(ph.incl_len);

        if (fread(packet.data(), ph.incl_len, 1, stream.get()) != 1)
            break;

        uint16_t version =
            (uint16_t(packet[63]) << 8) | packet[62];
        uint16_t messageSize =
            (uint16_t(packet[55]) << 8) | packet[54];

        char* buf = reinterpret_cast<char*>(packet.data() + 54);
        mh.wrap(buf, 2, version, ph.incl_len);

        if (mh.templateId() == 46) {
            template46(
                buf,
                mh.blockLength(),
                messageSize,
                mh.version(),
                ph.ts_sec,
                ph.ts_usec,
                out
            );
        }
    }

    return 0;
}