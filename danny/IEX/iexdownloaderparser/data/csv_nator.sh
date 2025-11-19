(echo "packet_timestamp,message_timestamp,seq_num,source,side,price,size"; \
 gunzip -c "$1" | awk -F',' 'BEGIN{OFS=","} {print $1,$2,$3,$5,$6,$7,$8}') > "${2:-output}.csv"

