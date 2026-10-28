# tRPC-Metrics-Prometheus 示例

本目录有两个例子。Greeter 例子在创建服务之前导入 `trpc_metrics_prometheus`，服务监听 `127.0.0.1:8000`，指标导出在 `http://127.0.0.1:8080/metrics`。`SayHello` 把请求里的 `msg` 加上 `hello: ` 前缀后返回。另一个例子不启动 tRPC 服务，只把示例指标挂到 `REGISTRY` 上。

## 关键特性

- **导入即注册**：`trpc_main.py` 在 `create_server` 之前执行 `import trpc_metrics_prometheus`
- **一次批量调用**：`test_service_rpc.py` 默认打 20 次 `SayHello`，再打印 `rpc_server_started_total`
- **五种进程/线程模式**：同一套服务配五份 YAML。多进程时只有一个进程能绑上 8080
- **独立拉取**：`pull_exporter.py` 直接调用 `init_metrics`，写入 Counter、Gauge、Summary

关键文件：

- [trpc_main.py](trpc_main.py)：导入插件、加载配置、注册 Greeter，然后 `serve`
- [greeter.py](greeter.py)：`SayHello` 返回 `hello: ` 加上请求内容
- [test_service_rpc.py](test_service_rpc.py)：客户端。打完 SayHello 后读取 exporter
- [pull_exporter.py](pull_exporter.py)：不启动 tRPC 服务，只暴露示例指标
- [run_examples.sh](run_examples.sh)：起进程、等端口、跑检查、停进程
- [stub/](stub/)：helloworld 桩代码
- `trpc_python*.yaml`：每种模式一份。Greeter 都听 `127.0.0.1:8000`，exporter 都听 `127.0.0.1:8080`

调用关系：

```text
test_service_rpc.py
├── Greeter.SayHello  127.0.0.1:8000
│   └── 回复 msg = "hello: " + request.msg
└── GET http://127.0.0.1:8080/metrics
    └── rpc_server_started_total

trpc_main.py
└── import trpc_metrics_prometheus
    └── MetricsPlugin.start
        └── prometheus exporter running at 127.0.0.1:8080

pull_exporter.py
└── init_metrics("127.0.0.1", 8080, "/metrics")
    └── http_requests_total / system_cpu_usage_percent / http_response_time_seconds
```

## 环境要求

- Python >= 3.8
- macOS 或 Linux
- 本机 8000、8080 空闲
- 依赖：`trpc-python`、`prometheus-client>=0.20.0`。在仓库根目录执行 `uv sync` 或 `pip install -e .`

## 运行步骤

在 `examples` 目录下：

```bash
./run_examples.sh list
./run_examples.sh
./run_examples.sh service
./run_examples.sh service trpc_python_merge_processes.yaml
./run_examples.sh pull
./run_examples.sh modes
./run_examples.sh all
```

`./run_examples.sh` 和 `service` 一样，用 [trpc_python.yaml](trpc_python.yaml)。`service` 后面可以换成本目录里的另一份 YAML，或一个绝对路径。`pull` 只跑 [pull_exporter.py](pull_exporter.py)。`modes` 按下面表格的顺序各跑一遍 `service`。`all` 先跑 `pull`，再跑 `modes`。

解释器按 `$PYTHON`、`../.venv/bin/python`、`../venv/bin/python`、`python3` 的顺序选。进程日志写在 `examples/.server_run.log`。上一级目录里有 `trpc_sdk` 包时，脚本把它的父目录放在 `PYTHONPATH` 前面。

手动跑 Greeter：

```bash
# 终端 1，当前目录是 examples
python trpc_main.py -c trpc_python.yaml

# 终端 2
python test_service_rpc.py
curl -sS http://127.0.0.1:8080/metrics
```

手动跑独立拉取：

```bash
python pull_exporter.py
curl -sS http://127.0.0.1:8080/metrics
```

| 配置 | 模型 |
| --- | --- |
| `trpc_python.yaml` | merge，一个事件循环 |
| `trpc_python_merge_threads.yaml` | merge，两个 serving 线程 |
| `trpc_python_separate_thread.yaml` | merge，一个 I/O 线程和两个 handler 线程 |
| `trpc_python_separate.yaml` | separate，两个 rpc task |
| `trpc_python_merge_processes.yaml` | multi-process merge，两个 worker |

## 运行结果

`./run_examples.sh` 对每一项打印 `[PASS]` 或 `[FAIL]`。

`service` 成功时，客户端打印类似下面的内容，并以状态码 0 退出：

```text
20 SayHello calls succeeded
rpc_server_started_total{...} 20.0
```

单进程配置里，脚本要求这些 `rpc_server_started_total` 样本的和不少于调用次数。`trpc_python_separate.yaml` 和 `trpc_python_merge_processes.yaml` 里每个 worker 有自己的 registry，只有绑住 8080 的那个进程会被拉到，所以脚本只检查调用成功和 exporter 已启动。

进程日志里有：

```text
prometheus exporter running at 127.0.0.1:8080, metrics path /metrics
```

`pull` 成功时，输出里能看到 `http_requests_total`、`system_cpu_usage_percent` 和 `http_response_time_seconds_count`。

## 适用场景

- 确认插件在 `create_server` 前导入后，Greeter 能返回 `hello: hello N`，并且 exporter 上有服务端计数
- 换 YAML 之后确认 exporter 仍然启动
- 不启动 tRPC 服务，只确认 `init_metrics` 能暴露自定义指标

## 需要注意什么

1. **先导入插件**。`import trpc_metrics_prometheus` 要在 `create_server` 之前。
2. **端口**。五份配置都听 `8000` 和 `8080`。一键脚本发现端口已被占用会直接失败。
