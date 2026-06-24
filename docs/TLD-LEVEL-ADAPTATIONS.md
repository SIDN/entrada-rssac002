This document is not meant to function as the definition of a TLD-level data publishing standard. Rather, it aims to explain deviations from [the root-level RSSAC002 advisory](https://itp.cdn.icann.org/en/files/root-server-system-advisory-committee-rssac-publications/rssac-002-measurements-root-22jun23-en.pdf), that were deemed appropriate for the scope of this project. 

## Metrics Generated
As noted in [`README.md`](), the scope of the project was limited to fit into its time frame.
The effect of this scope limitation on the difference between the root-level RSSAC002 advisory is that the `load-time` and `zone-size` metrics are omitted. The metrics `rcode-volume`, `traffic-volume`, `traffic-sizes`, and `unique-sources` are generated in full compliance with the RSSAC002v5 advisory.

## Report Exporting and the 'service' field

The export semantics of this metrics generator is similar to that defined under section 6.8 of the RSSAC002v5 working document.  Reports over all name servers are exported as defined in RSSAC002v5, i.e.:

```
<base-url>/<year>/<month>/<metric>/<short-service>-<yyyymmdd>-<metric>.yaml
```

However, the RSSAC002 advisory does not provide guidelines for exporting reports at a different level of granularity. In this metrics generator, we fill this gap by defining the following set of rules for per-name server reports:
- The version field of a report generated over a single name server should start with the same service name as for reports over all name servers, and should be followed by a hyphen, and a name server identifier (e.g name, or ID). See the following example:
	Report over all name servers:
		`service: some_TLD`
	Report over a single name server, with identifier `ns1`:
		`service: some_TLD-ns1`
 - A construction similar to the one defined above applies to the 'short-service' field in the URL: the 'short-service' as used in a report over all name servers should be followed by a name server identifier. Hence, the definition of the file name for per-nameserver reports is defined as follows:
```
<short-service>-<server-identifier>-<yyyymmdd>-<metric>.yaml`
```
- With this construction, however, it requires parsing semantics to derive the core RSSAC002-defined metrics, because name server reports are now mixed with global reports, thus making this harder to achieve. To address this issue, a nested directory `nameservers` gets added. This is why name server reports are exported following the URL below.
```
<base-url>/<year>/<month>/<metric>/nameservers/<short-service>-<server-identifier>-<yyyymmdd>-<metric>.yaml
```
