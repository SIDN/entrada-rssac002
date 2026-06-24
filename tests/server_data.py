from functools import reduce


class ServerData:
    def __init__(self, traffic_volume, traffic_sizes, rcode_volume, unique_sources) -> None:

        self.traffic_volume = traffic_volume
        self.traffic_sizes = traffic_sizes
        self.rcode_volume = rcode_volume
        self.unique_sources = unique_sources


def sum_dict(left: dict, right: dict) -> dict:
    result = {}
    for key in left.keys() | right.keys():
        left_val = left.get(key, 0)
        right_val = right.get(key, 0)

        if isinstance(left_val, dict) and isinstance(right_val, dict):
            result[key] = sum_dict(left_val, right_val)
        elif isinstance(left_val, dict):
            result[key] = sum_dict(left_val, {})
        elif isinstance(right_val, dict):
            result[key] = sum_dict({}, right_val)
        else:
            result[key] = left_val + right_val

    return result


def sum_server_data(left: ServerData, right: ServerData) -> ServerData:
    return ServerData(
        sum_dict(left.traffic_volume, right.traffic_volume),
        sum_dict(left.traffic_sizes, right.traffic_sizes),
        sum_dict(left.rcode_volume, right.rcode_volume),
        sum_dict(left.unique_sources, right.unique_sources),
    )


def get_global_report(servers: list[ServerData]) -> ServerData:
    return reduce(sum_server_data, servers)
