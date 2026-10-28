[English](README.md) | 中文

# tRPC-Metrics-Prometheus

tRPC-Metrics-Prometheus 是 tRPC-Python 的 Prometheus 监控插件。导入后注册 `MetricsPlugin` 以及主调、被调 filter，在执行业务的 worker 进程里启动 HTTP exporter，并把指标暴露出来供 Prometheus 拉取；配置了 Pushgateway 地址时，还会按间隔推送。

## 核心特性

- **导入即注册**：`import trpc_metrics_prometheus` 即注册监控插件和 filter，模调由 filter 自动计数，业务 handler 里不用手写上报。
- **拉取**：默认在 `http://{ip}:8080/metrics` 提供本进程的指标。端口已被占用时只记 warning，服务继续启动。
- **推送**：配置 `push_gateway_addr` 后，按 `report_interval` 把同一份指标推到 Pushgateway，job 名为 `interval_batch_push`。
- **自定义指标**：`custom_counter`、`custom_gauge`、`custom_histogram` 用来统计业务函数的调用次数、并发和耗时。

## 安装方式

### 环境要求

Python 版本: 3.8+

依赖：[`trpc-python`](https://github.com/trpc-group/trpc-python)（`trpc_sdk`）、`prometheus-client>=0.20.0`。

### 安装

使用 `pip` 安装：

```bash
pip install trpc_metrics_prometheus
```

## 快速体验

这里假设已经有一个 tRPC 项目。插件要同时完成两件事：导入包，并在框架配置里写上 `plugins.metrics.prometheus`。模调 filter 还要单独挂到 `server.filter` 或 `client.filter`。

#### 1. 导入插件

在服务入口最前面导入。导入过程会注册插件，需要放在框架启动之前。

```python
import trpc_metrics_prometheus
```

#### 2. 配置文件

`ip` 同时作为 `instance` 标签和 HTTP exporter 的监听地址。`port` 默认 `8080`，`path` 默认 `/metrics`，只有这个路径返回指标，其他路径返回 404。

`app`、`server`、`namespace`、`env_name`、`set_name`、`container`、`ip` 留空时，分别回退到 `server.app`、`server.server`、`global.namespace`、`global.env_name`、`global.full_set_name`、`global.container_name`、`global.local_ip`。

`push_gateway_addr` 留空时只提供拉取。`report_interval` 的代码默认值是 `0`，只在开启推送时生效；开启推送时请写成正数秒数，为 `0` 时推送循环会空转。`username` 和 `password` 都非空时使用 Basic 认证；只填其中一个时按无认证推送，此时网关需要免鉴权。

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

#### 3. 开启模调上报

主调上报挂在 client，被调上报挂在 server。两边可以只开其中一边。

```yaml
server:
  filter:
    - prometheus
client:
  filter:
    - prometheus
```

#### 4. 查看指标

启动服务后，按配置里的地址拉取。`ip` 为 `0.0.0.0` 时，换成这台机器实际访问的地址。

```sh
curl http://127.0.0.1:8080/metrics
```

#### 5. 独立拉取示例

[examples/pull_exporter.py](./examples/pull_exporter.py) 直接调用 `init_metrics`，往 `REGISTRY` 里写示例 Counter、Gauge、Summary，不启动 tRPC 服务。

```sh
python3 examples/pull_exporter.py
curl http://127.0.0.1:8080/metrics
```

示例说明见 [examples/README.md](./examples/README.md)。在仓库根目录执行 `./examples/run_examples.sh` 会启动 Greeter、发送 SayHello、检查 exporter，然后停掉服务。`./examples/run_examples.sh pull` 会跑上面的独立 exporter，然后停掉它。

## 指标说明

### 模调指标

filter 自动上报下面这些指标。`rpc_client_*` 是本服务发出的下游调用，`rpc_server_*` 是本服务收到的请求。

- `rpc_client_started_total`、`rpc_server_started_total`：请求开始次数
- `rpc_client_handled_total`、`rpc_server_handled_total`：请求结束次数，带 `code` 和 `code_type`
- `rpc_client_handled_seconds`、`rpc_server_handled_seconds`：处理耗时直方图，单位秒

每条 RPC 指标带这些标签：

- `system_name`：固定为 `trpc`
- `caller_service`、`caller_method`、`callee_service`、`callee_method`
- `namespace`、`app`、`server`、`env_name`、`set_name`、`instance`、`container`、`pid`

`instance` 的值是配置里的 `ip`，`pid` 是当前进程号。方法名为空时记为 `unknown`。

流式调用走 `run_stream`，原样透传，不计入上面的指标。

### 错误码

默认的 `code` 这样取值：调用出错时用异常的 `code`，异常没有 `code` 时用 `TRPC_INVOKE_UNKNOWN_ERR`；调用成功时依次尝试响应对象的 `retcode`、`ret_code`、`code`，都没有则为 `"0"`。

默认的 `code_type`：`""` 和 `"0"` 为 `success`，其他为 `exception`。

业务码不在上述字段里时，替换 filter 使用的取值函数：

```python
import trpc_metrics_prometheus.filter as prom_filter


def my_get_code(ctx, req, rsp, err) -> str:
    if err is not None:
        return str(getattr(err, "code", "1"))
    return str(getattr(rsp, "biz_code", "0"))


prom_filter.DEFAULT_GET_CODE_FUNC = my_get_code
```

需要把某些码标成超时或其他分类时，替换 `code_type` 映射。可选值包括 `success`、`exception`、`timeout`：

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

### 自定义指标

三个装饰器都接受指标名、说明、标签名，以及一个从函数参数算出标签值的函数。同步和异步函数都可以包。每条自定义指标还会附上公共标签 `namespace`、`app`、`server`、`env_name`、`set_name`、`instance`、`container`、`pid`。使用装饰器前需要先让插件完成初始化，否则这些标签没有取值。

- `custom_counter`：调用前增加 `{name}_started`，调用后增加 `{name}_finished`。抓取名是 `custom_{name}_started_total` 和 `custom_{name}_finished_total`。
- `custom_gauge`：调用前加一、返回后减一，值是当前并发。抓取名是 `custom_{name}`。
- `custom_histogram`：记录函数耗时，单位秒。抓取名是 `custom_{name}_bucket`、`custom_{name}_sum`、`custom_{name}_count`。

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

同一个指标名在进程内只会创建一次，之后同名上报会复用已有指标。

## 许可证

本项目采用 Apache-2.0 许可证。
