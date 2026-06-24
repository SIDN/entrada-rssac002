REQUEST_BUCKETS = {*{f"{str(i)}-{i + 15}" for i in range(0, 287, 16)}, "288-"}
RESPONSE_BUCKETS = {*{f"{str(i)}-{i + 15}" for i in range(0, 4095, 16)}, "4096-"}
