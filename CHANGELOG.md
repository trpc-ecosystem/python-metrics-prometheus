# Change Log

## 1.0.0

- 支持 tRPC-Python 注册 Prometheus 监控插件，主调、被调 filter。
- 在业务进程启动 HTTP exporter 供拉取；配置 Pushgateway 后按间隔推送，并提供自定义 Counter、Gauge、Histogram。
