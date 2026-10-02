from abc import ABC, abstractmethod


class QueryCatalog(ABC):
    @abstractmethod
    def get_rcode_volume_global_query() -> str:
        pass

    @abstractmethod
    def get_rcode_volume_per_ns_query() -> str:
        pass

    @abstractmethod
    def get_unique_sources_global_query() -> str:
        pass

    @abstractmethod
    def get_unique_sources_per_ns_query() -> str:
        pass

    @abstractmethod
    def get_traffic_volume_global_query() -> str:
        pass

    @abstractmethod
    def get_traffic_volume_per_ns_query() -> str:
        pass

    @abstractmethod
    def get_traffic_sizes_global_request_query() -> str:
        pass

    @abstractmethod
    def get_traffic_sizes_per_ns_request_query() -> str:
        pass

    @abstractmethod
    def get_traffic_sizes_global_response_query() -> str:
        pass

    @abstractmethod
    def get_traffic_sizes_per_ns_response_query() -> str:
        pass


class EntradaQueryCatalog(QueryCatalog):
    @staticmethod
    def get_rcode_volume_global_query() -> str:
        return """
            SELECT dns_rcode, COUNT(*) FROM dns
            WHERE time >= ?
            AND time < ?
            AND dns_tld = ?
            GROUP BY dns_rcode
        """

    @staticmethod
    def get_rcode_volume_per_ns_query() -> str:
        return """
            SELECT server, dns_rcode, COUNT(*) FROM dns
            WHERE time >= ?
            AND time < ?
            AND dns_tld = ?
            GROUP BY dns_rcode, server
        """

    @staticmethod
    def get_unique_sources_global_query() -> str:
        return """
            SELECT
                COUNT(DISTINCT CASE WHEN ip_version = 4 THEN ip_src END) AS num_sources_ipv4,
                COUNT(DISTINCT CASE WHEN ip_version = 6 THEN ip_src END) AS num_sources_ipv6,
                COUNT(DISTINCT CASE WHEN ip_version = 6 THEN concat(
                    split_part(ip_src, ':', 1), ':',
                    split_part(ip_src, ':', 2), ':',
                    split_part(ip_src, ':', 3), ':',
                    split_part(ip_src, ':', 4)
                ) END) AS num_sources_ipv6_aggregate
            FROM dns
            WHERE time >= ?
            AND time < ?
            AND dns_tld = ?
        """

    @staticmethod
    def get_unique_sources_per_ns_query() -> str:
        return """
            SELECT
                server,
                COUNT(DISTINCT CASE WHEN ip_version = 4 THEN ip_src END) AS num_sources_ipv4,
                COUNT(DISTINCT CASE WHEN ip_version = 6 THEN ip_src END) AS num_sources_ipv6,
                COUNT(DISTINCT CASE WHEN ip_version = 6 THEN concat(
                    split_part(ip_src, ':', 1), ':',
                    split_part(ip_src, ':', 2), ':',
                    split_part(ip_src, ':', 3), ':',
                    split_part(ip_src, ':', 4)
                ) END) AS num_sources_ipv6_aggregate
            FROM dns
            WHERE time >= ?
            AND time < ?
            AND dns_tld = ?
            GROUP BY server
        """

    @staticmethod
    def get_traffic_volume_global_query() -> str:
        return """
            SELECT 
            COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 17 AND ip_version = 4
                THEN 1 END
            ) AS dns_udp_queries_received_ipv4,
           COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 17 AND ip_version = 6
                THEN 1 END
            ) AS dns_udp_queries_received_ipv6,
            COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 6 AND ip_version = 4
                THEN 1 END
            ) AS dns_tcp_queries_received_ipv4,
           COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 6 AND ip_version = 6
                THEN 1 END
            ) AS dns_tcp_queries_received_ipv6,
            COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 17 AND ip_version = 4
                THEN 1 END
            ) AS dns_udp_responses_sent_ipv4,
           COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 17 AND ip_version = 6
                THEN 1 END
            ) AS dns_udp_responses_sent_ipv6,
            COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 6 AND ip_version = 4
                THEN 1 END
            ) AS dns_tcp_responses_sent_ipv4,
           COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 6 AND ip_version = 6
                THEN 1 END
            ) AS dns_tcp_responses_sent_ipv6
            FROM dns
            WHERE time >= ?
            AND time < ?
            AND dns_tld = ?
        """

    @staticmethod
    def get_traffic_volume_per_ns_query() -> str:
        return """
            SELECT server, 
            COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 17 AND ip_version = 4
                THEN 1 END
            ) AS dns_udp_queries_received_ipv4,
           COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 17 AND ip_version = 6
                THEN 1 END
            ) AS dns_udp_queries_received_ipv6,
            COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 6 AND ip_version = 4
                THEN 1 END
            ) AS dns_tcp_queries_received_ipv4,
           COUNT(
                CASE WHEN dns_req_len IS NOT NULL 
                AND dns_req_len > 0 
                AND prot = 6 AND ip_version = 6
                THEN 1 END
            ) AS dns_tcp_queries_received_ipv6,
            COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 17 AND ip_version = 4
                THEN 1 END
            ) AS dns_udp_responses_sent_ipv4,
           COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 17 AND ip_version = 6
                THEN 1 END
            ) AS dns_udp_responses_sent_ipv6,
            COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 6 AND ip_version = 4
                THEN 1 END
            ) AS dns_tcp_responses_sent_ipv4,
           COUNT(
                CASE WHEN dns_res_len IS NOT NULL 
                AND dns_res_len > 0 
                AND prot = 6 AND ip_version = 6
                THEN 1 END
            ) AS dns_tcp_responses_sent_ipv6
            FROM dns
            WHERE time >= ?
            AND time < ?
            AND dns_tld = ?
            GROUP BY server
        """

    @staticmethod
    def get_traffic_sizes_global_request_query() -> str:
        return """
            SELECT prot,
                CASE
                    WHEN dns_req_len < 288
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '288-'
                END AS bucket,
                COUNT(*) AS count
            FROM (
                SELECT prot, dns_req_len,
                    CAST(FLOOR(dns_req_len / 16.0) * 16 AS INTEGER) AS bucket_start
                FROM dns
                WHERE dns_req_len IS NOT NULL
                AND time >= ? AND time < ? 
                AND dns_tld = ?
            ) t
            GROUP BY prot, 
                CASE
                    WHEN dns_req_len < 288
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '288-'
                END
        """

    @staticmethod
    def get_traffic_sizes_per_ns_request_query() -> str:
        return """
            SELECT server, prot,
                CASE
                    WHEN dns_req_len < 288
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '288-'
                END AS bucket,
                COUNT(*) AS count
            FROM (
                SELECT server, prot, dns_req_len,
                    CAST(FLOOR(dns_req_len / 16.0) * 16 AS INTEGER) AS bucket_start
                FROM dns
                WHERE dns_req_len IS NOT NULL
                AND time >= ? AND time < ?
                AND dns_tld = ?
            ) t
            GROUP BY server, prot, 
                CASE
                    WHEN dns_req_len < 288
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '288-'
                END
        """

    @staticmethod
    def get_traffic_sizes_global_response_query() -> str:
        return """
            SELECT prot,
                CASE
                    WHEN dns_res_len < 4096
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '4096-'
                END AS bucket,
                COUNT(*) AS count
            FROM (
                SELECT prot, dns_res_len,
                    CAST(FLOOR(dns_res_len / 16.0) * 16 AS INTEGER) AS bucket_start
                FROM dns
                WHERE dns_res_len IS NOT NULL
                AND time >= ? AND time < ?
                AND dns_tld = ?
            ) t
            GROUP BY prot, 
                CASE
                    WHEN dns_res_len < 4096
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '4096-'
                END
        """

    @staticmethod
    def get_traffic_sizes_per_ns_response_query() -> str:
        return """
            SELECT server, prot,
                CASE
                    WHEN dns_res_len < 4096
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '4096-'
                END AS bucket,
                COUNT(*) AS count
            FROM (
                SELECT server, prot, dns_res_len,
                    CAST(FLOOR(dns_res_len / 16.0) * 16 AS INTEGER) AS bucket_start
                FROM dns
                WHERE dns_res_len IS NOT NULL
                AND time >= ? AND time < ?
                AND dns_tld = ?
            ) t
            GROUP BY server, prot, 
                CASE
                    WHEN dns_res_len < 4096
                        THEN CONCAT(CAST(bucket_start AS VARCHAR), '-', CAST(bucket_start + 15 AS VARCHAR))
                    ELSE '4096-'
                END
        """