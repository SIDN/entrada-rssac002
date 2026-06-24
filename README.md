This repository contains a tool that generates TLD-level DNS traffic metrics in a structure based on [version 5 of the existing RSSAC002 standard](https://itp.cdn.icann.org/en/files/root-server-system-advisory-committee-rssac-publications/rssac-002-measurements-root-22jun23-en.pdf). This metrics generator serves operators who collect data with [ENTRADA2](https://github.com/SIDN/entrada2) and functions as a first step towards DNS metric standardization at the TLD level.

### Features:
- Generation of TLD-level adaptations of the following RSSAC002v5-defined metrics:
	- `rcode-volume`
	- `traffic-sizes`
	- `traffic-volume`
	- `unique-sources`
- Support for flexible scheduling as a flexibility add-on, and is useful for non-additive metrics such as `unique-sources`. However, for standardization purposes, publishing metrics over the RSSAC002v5-defined, system default 00:00-23:59 UTC window is required.
- Report exporting to a user-specified directory. Further exporting is done according to the RSSAC002v5-defined directory structure.
- Support for per-nameserver metrics generation.
  
### Limitations:
This project was part of the 10-week, 2nd-year BSc course (CSE2000) at the Delft University of Technology. To fit into the time frame of the course, the tool has been limited to the generation of the previously mentioned subset of RSSAC002-defined metrics. The `zone-size` and `load-time` metrics are omitted to keep the scope fixed to metrics that can be derived from ENTRADA2.
### Configuration
The metrics generator can be configured through a .`yaml` file:
#### What is configurable?
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
	- `engine`: Query engine name. Currently only supports Trino.
	- `host`: Hostname or IP address of the query engine/database server the tool connects to in order to read ENTRADA2 query log data. -
	- `port`: Port number on which the query engine is listening for connections.
	- `user`: Username used to authenticate for the query engine.
	- `catalog`: The catalog under which the ENTRADA2 data is registered. Set this to match your ENTRADA2 deployment's catalog name.
	- `schema`: The database schema.

- `service_name`: RSSAC002 parameter for service-name.

- `short_service`: RSSAC002 parameter for short service-name (for filenames).

- `per_ns_mode`: A Boolean value for enabling per-nameserver generation.

  
Below is an example of a valid configuration file:

```YAML
db_timezone: UTC
export_root: ./RSSAC002-data
schedule:
  type: fixed_window
  start_time: 2026-05-25T09:38:59+00:00
  window_start: 00:00
  window_end: 00:00
  generation_time: 03:00

query_connection:
  engine: trino
  host: localhost
  port: 8085
  user: admin
  catalog: iceberg
  schema: entrada

service_name: TLD
short_service: .tld
per_ns_mode: true

```

  
### Running instructions

To run the tool, ensure `uv` is installed correctly. Then, from the `core-tool` directory, run:

```

uv run python -m src.main --config [CONFIG_LOCATION]

```

There also exists a `-d` or `--debug` option, which can be used to obtain more detailed logging for debugging purposes.

If not specified, config location defaults to `/core-tool/rssac002config.yaml`.

## Project Origin

This project originated as a TU Delft CSE2000 Software Project for SIDN Labs. The broader project investigated whether RSSAC002-style reporting can be adapted for TLD-level DNS traffic metrics. This public repository contains only the Metrics Generator component.

## Related Projects

 Within the CSE2000 course, we have also developed an [RSSAC002 analysis dashboard](https://codeberg.org/RSSAC002-TLD/RSSAC002-Analysis-Dashboard). 

## License
This project is licensed under the GNU General Public License v3. See [`LICENSE.md`]().