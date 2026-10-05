> **This is a fork** of the [RSSAC002-TLD Metrics Generator](https://codeberg.org/RSSAC002-TLD/RSSAC002-TLD-Metrics-Generator), with some changes. The changes are listed in [Changes compared to the original](#changes-compared-to-the-original).
>
> **Credit:** the tool was built by computer science bachelor students at [TU Delft](https://tudelft.nl) as part of their [Software Project course](https://sp.pages.ewi.tudelft.nl/site/), in a project for SIDN Labs. Many thanks to them. All credit for the original design and implementation goes to them.

This repository contains a tool that generates TLD-level DNS traffic metrics in a structure based on [version 5 of the existing RSSAC002 standard](https://itp.cdn.icann.org/en/files/root-server-system-advisory-committee-rssac-publications/rssac-002-measurements-root-22jun23-en.pdf). This metrics generator serves operators who collect data with [ENTRADA2](https://github.com/SIDN/entrada2) and functions as a first step towards DNS metric standardization at the TLD level.

## Changes compared to the original

- **TLD selection:** queries are restricted to one TLD, set with the new `tld_evaluated` option (required).
- **Correct IPv6 prefix counting:** the original matched prefixes by substring, which gives wrong counts. Prefixes are now compared properly.
- **OAuth2 authentication for Trino:** new `auth` (`oauth2` or `none`) and `http_scheme` options. `schema` and `user` are now optional, and `engine` defaults to `trino`. The config is validated: `auth: none` requires a `user`, and `auth: oauth2` requires `https`.
- **One shared query executor:** a single executor is used by all generators, so OAuth2 only authenticates once per run instead of four times.
- **Optional overwrite of existing reports:** reports can be overwritten, written atomically through a temporary file, so an interrupted run never leaves a partial report. By default existing reports are never overwritten.
- **NULL RCODE fix:** the `rcode-volume` report no longer crashes when a query has no RCODE. These are reported under RCODE `-1`, which means the DNS query had no response, or ENTRADA could not match it to a response. Report validation now accepts `-1` (`RCODE_MIN`).
- **Configurable query catalog:** the new `query_catalog` option selects the query set (default: `entrada`).
- **Default runner is one-shot:** the project entrypoint now executes the query runner by default instead of entering the long-running scheduler loop. The scheduler remains available as an explicit opt-in mode with `--scheduler`.

**Breaking changes:** `tld_evaluated` is required, so config files for the original version need this option added.

## Features
- Generation of TLD-level adaptations of the following RSSAC002v5-defined metrics:
	- `rcode-volume`
	- `traffic-sizes`
	- `traffic-volume`
	- `unique-sources`
- Support for flexible scheduling as a flexibility add-on, and is useful for non-additive metrics such as `unique-sources`. However, for standardization purposes, publishing metrics over the RSSAC002v5-defined, system default 00:00-23:59 UTC window is required.
- Report exporting to a user-specified directory. Further exporting is done according to the RSSAC002v5-defined directory structure.
- Support for per-nameserver metrics generation.
- Metrics restricted to a single TLD.
- Trino authentication with OAuth2.

## Limitations
The original project was part of the 10-week, 2nd-year BSc course (CSE2000) at the Delft University of Technology. To fit into the time frame of the course, the tool has been limited to the generation of the previously mentioned subset of RSSAC002-defined metrics. The `zone-size` and `load-time` metrics are omitted to keep the scope fixed to metrics that can be derived from ENTRADA2.

## Configuration
The metrics generator can be configured through a `.yaml` file.

### What is configurable?
- Database time zone (`db_timezone`): specifies the timezone the database operates in. Important for range queries over time.
- Export root (`export_root`): directory to which generated reports should be exported.

- Schedule information (`schedule`):
	- Schedule type (`type`): the type of schedule you want to run. Currently only a fixed sliding window (`type: fixed_window`) report generation schedule with a detached generation time is implemented.
	- For the fixed window schedule type, 4 parameters can be defined:
	- `window_start`, `window_end`: start and end times of the window. These should be plain times, because these times will be fixed for each day.
		DEFAULT: 00:00 UTC time.
	- `generation_time`: Defines the time at which the reports should be generated.
		DEFAULT: 3AM UTC time.
	- `start_time`: Datetime from which the tool should start. There is also an option to put in `startup` as the value for this key. The tool will start generating reports at the soonest occurrence of the `generation_time` after `start_time`.
		DEFAULT: Startup time

- Query executor information (`query_connection`):
	- `engine`: Query engine name. Currently only supports Trino. DEFAULT: `trino`.
	- `host`: Hostname or IP address of the query engine/database server the tool connects to in order to read ENTRADA2 query log data.
	- `port`: Port number on which the query engine is listening for connections.
	- `catalog`: The catalog under which the ENTRADA2 data is registered. Set this to match your ENTRADA2 deployment's catalog name.
	- `schema`: The database schema. Optional.
	- `http_scheme`: `http` or `https`. Optional. Must be `https` (or omitted) when using OAuth2.
	- `auth`: Authentication mode: `oauth2` or `none`. DEFAULT: `none`. With `oauth2` the tool starts an OAuth2 login flow once per run.
	- `user`: Username used to authenticate for the query engine. Required when `auth` is `none` (or omitted), not used with `oauth2`.
	- `query_catalog`: Which set of queries to use. DEFAULT: `entrada`.

- `service_name`: RSSAC002 parameter for service-name.

- `short_service`: RSSAC002 parameter for short service-name (for filenames).

- `per_ns_mode`: A Boolean value for enabling per-nameserver generation.

- `tld_evaluated`: The TLD the metrics are calculated for (for example `nl`). Required.

Below is an example of a valid configuration file, using OAuth2:

```YAML
db_timezone: UTC
export_root: ./NL-RSSAC002-data
schedule:
  type: fixed_window
  start_time: 2026-08-30T00:00:00+00:00
  window_start: 00:00
  window_end: 00:00
  generation_time: 09:00

query_connection:
  host: trino.example.org  # your Trino host
  port: 443                # your Trino port
  catalog: iceberg
  schema: entrada          # optional
  http_scheme: https
  auth: oauth2             # "oauth2" or "none" (or omit for username auth)
  user: null               # used only when auth is none/omitted
  query_catalog: entrada

service_name: nl_servers
short_service: nl
per_ns_mode: true
tld_evaluated: nl
```

For a setup without OAuth2, use username authentication instead:

```YAML
query_connection:
  host: localhost
  port: 8085
  catalog: iceberg
  schema: entrada
  auth: none
  user: admin
```

### RCODE `-1`
In the `rcode-volume` report, an RCODE of `-1` means the DNS query had no response, or ENTRADA could not match it to a response. This is not an RCODE defined by the RSSAC002 standard.

## Running instructions

The default project entrypoint is the one-shot query runner. It executes the configured query catalog for the selected time range and exits instead of entering the long-running scheduler loop.

To run it with a config file and a date range:

```bash
uv run python -m src.main --config ./path/to/config.yaml --start 2026-05-21 --end 2026-05-21
```

If you want to force the older long-running scheduler behavior, enable it explicitly:

```bash
uv run python -m src.main --scheduler --config ./path/to/config.yaml
```

For local smoke testing without a Trino connection, the in-memory SQLite runner is also available:

```bash
uv run python -m src.main --sqlite --start 2026-05-21 --end 2026-05-21 --tld nl
```

There also exists a `-d` or `--debug` option, which can be used to obtain more detailed logging for debugging purposes.

If `--config` is not specified, the config location defaults to `rssac002config.yaml` in the current directory.

## Project Origin

The original project was a TU Delft CSE2000 Software Project, carried out by bachelor students for SIDN Labs. The broader project investigated whether RSSAC002-style reporting can be adapted for TLD-level DNS traffic metrics. The upstream repository contains only the Metrics Generator component, and this fork is derived from it.

Original repository: https://codeberg.org/RSSAC002-TLD/RSSAC002-TLD-Metrics-Generator

## Related Projects

 Within the CSE2000 course, the original authors also developed an [RSSAC002 analysis dashboard](https://codeberg.org/RSSAC002-TLD/RSSAC002-Analysis-Dashboard).

## License
This project is licensed under the GNU General Public License v3, the same license as the original. See [`LICENSE.md`](LICENSE.md). The original copyright notices are kept, and changes in this fork are made available under the same license.
