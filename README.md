English | [中文](README_zh_CN.md)

# tRPC-Metrics-Prometheus

tRPC-Metrics-Prometheus is the Prometheus metrics plugin for tRPC-Python. Importing it registers `MetricsPlugin` and the client and server filters. In the worker process that runs business code it starts an HTTP exporter and exposes metrics for Prometheus to scrape. When a Pushgateway address is configured, it also pushes on an interval.

## Features

- **Register on import**: `import trpc_metrics_prometheus` registers the metrics plugin and the filters. RPC metrics are counted by the filters, so business handlers do not report them by hand.
- **Pull**: By default this process serves its metrics at `http://{ip}:8080/metrics`. If the port is already in use, the plugin logs a warning and the service still starts.
- **Push**: After `push_gateway_addr` is set, the same metrics are pushed to the Pushgateway every `report_interval` seconds. The job name is `interval_batch_push`.
- **Custom metrics**: `custom_counter`, `custom_gauge`, and `custom_histogram` record call counts, in-flight concurrency, and duration of business functions.

## Installation

### Requirements

Python: 3.8+

Dependencies: [`trpc-python`](https://github.com/trpc-group/trpc-python) (`trpc_sdk`) and `prometheus-client>=0.20.0`.

### Install

Install with `pip`:

```bash
pip install trpc_metrics_prometheus
```

## Quick start

This assumes a tRPC project already exists. The plugin needs two things: import the package, and add `plugins.metrics.prometheus` to the framework config. The RPC filters are attached separately on `server.filter` or `client.filter`.

#### 1. Import the plugin

Import it at the top of the service entry point. Importing registers the plugin, so this must happen before the framework starts.

```python
import trpc_metrics_prometheus
```

#### 2. Configuration

`ip` is both the `instance` label and the HTTP exporter bind address. `port` defaults to `8080` and `path` defaults to `/metrics`. Only that path returns metrics. Other paths return 404.

When `app`, `server`, `namespace`, `env_name`, `set_name`, `container`, and `ip` are left empty, they fall back to `server.app`, `server.server`, `global.namespace`, `global.env_name`, `global.full_set_name`, `global.container_name`, and `global.local_ip`.

Leaving `push_gateway_addr` empty serves pull only. The code default of `report_interval` is `0`, and that value applies only when pushing is enabled. Set a positive number of seconds when pushing is on. `0` makes the push loop spin without sleeping. Basic auth is used when both `username` and `password` are non-empty. If only one of them is set, pushes are sent without auth, and the gateway must allow that.

```yaml
plugins:
  metrics:                              # 监控配置
    prometheus:                         # prometheus monitor
      report_interval: 5                # 推送间隔，单位秒。代码默认为 0；开启推送时请设为正数
      push_gateway_addr: x.x.x.x:9090   # Pushgateway 地址，host:port。留空则不推送
      username: 'xxxxx'                 # Basic 认证账号，可选
      password: 'xxxxxxxx'              # Basic 认证密码，可选
      app:       ${APP_NAME}            # 业务名。可选，未配置则与 server.app 一致
      server:    ${SERVER_NAME}         # 服务名。可选，未配置则与 server.server 一致
      namespace:  ${NAMESPACE}          # 物理环境。可选，未配置则与 global.namespace 一致
      env_name: ${DOCKER_ENV}           # 用户环境。可选，未配置则与 global.env_name 一致
      set_name: ${SET_NAME}             # 用户 Set。可选，未配置则与 global.full_set_name 一致
      container:  ${POD_NAME}           # 容器名称。可选，未配置则与 global.container_name 一致
      ip:        ${POD_IP}              # 本机 IP，同时是 exporter 监听地址。可选，未配置则与 global.local_ip 一致
      port: 8080                        # exporter 端口，可选，默认 8080
      path: /metrics                    # exporter 路径，可选，默认 /metrics
```

#### 3. Enable RPC metrics

Client-call metrics are attached on the client. Server-call metrics are attached on the server. Either side can be enabled on its own.

```yaml
server:
  filter:
    - prometheus
client:
  filter:
    - prometheus
```

#### 4. View metrics

After the service starts, scrape the address from the config. When `ip` is `0.0.0.0`, use an address that can actually reach this machine.

```sh
curl http://127.0.0.1:8080/metrics
```

#### 5. Standalone pull example

[examples/pull_exporter.py](./examples/pull_exporter.py) calls `init_metrics` directly and writes sample Counter, Gauge, and Summary metrics into `REGISTRY`. It does not start a tRPC service.

```sh
python3 examples/pull_exporter.py
curl http://127.0.0.1:8080/metrics
```

[examples/README.md](./examples/README.md) describes the Greeter service and this standalone exporter. From the repository root, `./examples/run_examples.sh` starts Greeter, sends SayHello, checks the exporter, and stops the server. `./examples/run_examples.sh pull` runs the standalone exporter and then stops it.

## Metrics

### RPC metrics

The filters report the metrics below. `rpc_client_*` is a downstream call made by this service. `rpc_server_*` is a request received by this service.

- `rpc_client_started_total`, `rpc_server_started_total`: number of calls started
- `rpc_client_handled_total`, `rpc_server_handled_total`: number of calls finished, with `code` and `code_type`
- `rpc_client_handled_seconds`, `rpc_server_handled_seconds`: handling-time histogram, in seconds

Each RPC metric carries these labels:

- `system_name`: always `trpc`
- `caller_service`, `caller_method`, `callee_service`, `callee_method`
- `namespace`, `app`, `server`, `env_name`, `set_name`, `instance`, `container`, `pid`

`instance` is the configured `ip`. `pid` is the current process id. An empty method name is recorded as `unknown`.

Streaming calls go through `run_stream` and are passed through unchanged. They are not counted in the metrics above.

### Error codes

The default `code` is chosen as follows. When the call fails, the exception's `code` is used, or `TRPC_INVOKE_UNKNOWN_ERR` when the exception has no `code`. When the call succeeds, the response object's `retcode`, `ret_code`, and `code` are tried in that order. If none of them is set, the code is `"0"`.

The default `code_type` maps `""` and `"0"` to `success`, and every other code to `exception`.

When the business code is not in those fields, replace the function the filter uses:

```python
import trpc_metrics_prometheus.filter as prom_filter


def my_get_code(ctx, req, rsp, err) -> str:
    if err is not None:
        return str(getattr(err, "code", "1"))
    return str(getattr(rsp, "biz_code", "0"))


prom_filter.DEFAULT_GET_CODE_FUNC = my_get_code
```

To classify some codes as timeout or another type, replace the `code_type` mapping. The values include `success`, `exception`, and `timeout`:

```python
from trpc_metrics_prometheus import CodeTypeException
from trpc_metrics_prometheus import CodeTypeSuccess
from trpc_metrics_prometheus import CodeTypeTimeout
from trpc_metrics_prometheus import set_code_type_func


def my_code_type(code: str) -> str:
    if code == "101":
        return CodeTypeTimeout
    if code in ("", "0"):
        return CodeTypeSuccess
    return CodeTypeException


set_code_type_func(my_code_type)
```

### Custom metrics

All three decorators take a metric name, a description, label names, and a function that computes label values from the wrapped function's arguments. They wrap both synchronous and asynchronous functions. Each custom metric also gets the common labels `namespace`, `app`, `server`, `env_name`, `set_name`, `instance`, `container`, and `pid`. The plugin must finish initializing before these decorators run, or those labels have no values.

- `custom_counter`: increments `{name}_started` before the call and `{name}_finished` after it. The scrape names are `custom_{name}_started_total` and `custom_{name}_finished_total`.
- `custom_gauge`: increments before the call and decrements after it returns. The value is the current in-flight count. The scrape name is `custom_{name}`.
- `custom_histogram`: records the function duration in seconds. The scrape names are `custom_{name}_bucket`, `custom_{name}_sum`, and `custom_{name}_count`.

```python
from trpc_metrics_prometheus import custom_counter
from trpc_metrics_prometheus import custom_gauge
from trpc_metrics_prometheus import custom_histogram


def label_values(ctx, req):
    return (req["method"],)


@custom_counter("order", "order calls", ["method"], label_values)
@custom_gauge("order_inflight", "in-flight order calls", ["method"], label_values)
@custom_histogram("order_seconds", "order call duration", ["method"], label_values)
async def create_order(ctx, req):
    return {"code": 0}
```

A metric name is created once in the process. Later reports that use the same name reuse the existing metric.

## License

This project is licensed under Apache-2.0.
