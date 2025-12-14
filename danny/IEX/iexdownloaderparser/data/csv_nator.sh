(
    echo "COLLECTION_TIME,SOURCE_TIME,SEQ_NUM,TICK_TYPE,MARKET_CENTER,SIDE,PRICE,SIZE,NUM_ORDERS,IS_IMPLIED,REASON,IS_PARTIAL"

    gunzip -c "$1" | \
    awk -F',' 'BEGIN{OFS=","} {
        # IEX tick format:
        # 1: COLLECTION_TIME
        # 2: SOURCE_TIME
        # 3: SEQ_NUM
        # 4: TICK_TYPE
        # 5: MARKET_CENTER
        # 6: SIDE
        # 7: PRICE
        # 8: SIZE
        # 9: (empty)
        # 10: (empty)
        # 11: (empty)
        # 12: IS_PARTIAL

        print $1,      \
              $2,      \
              $3,      \
              $4,      \
              $5,      \
              $6,      \
              $7,      \
              $8,      \
              "",       \
              "",       \
              "",       \
              $12
    }'
) > "${2:-output}.csv"
