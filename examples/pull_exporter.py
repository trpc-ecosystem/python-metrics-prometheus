# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Serve example metrics from ``REGISTRY`` at http://127.0.0.1:8080/metrics without a tRPC server."""

import threading
import time

from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Summary
from trpc_sdk.log import logger

from trpc_metrics_prometheus import REGISTRY
from trpc_metrics_prometheus import init_metrics


def register_example_metrics():
    """Register example metrics to demonstrate functionality."""
    # Create example metrics.
    request_counter = Counter('http_requests_total',
                              'Total HTTP requests', ['method', 'endpoint', 'status_code'],
                              registry=REGISTRY)

    response_time = Summary('http_response_time_seconds',
                            'Time spent processing requests', ['endpoint'],
                            registry=REGISTRY)

    cpu_usage = Gauge('system_cpu_usage_percent', 'Current CPU usage percentage', registry=REGISTRY)

    # Return the metric objects for later use.
    return request_counter, response_time, cpu_usage


if __name__ == "__main__":

    init_metrics("127.0.0.1", 8080, "/metrics")

    request_counter, response_time, cpu_usage = register_example_metrics()

    logger.info("Example metrics registered")

    last_values = {'request_counter': 0, 'response_time': 0.0, 'cpu_usage': 0.0}

    # Lock shared state updated by the simulator thread.
    values_lock = threading.Lock()

    # Simulate metric updates.
    def simulate_metrics():
        import random
        from datetime import datetime

        while True:
            try:
                # Update the request counter.
                method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
                endpoint = random.choice(['/home', '/api', '/users', '/products'])
                status = random.choices([200, 400, 404, 500], weights=[8, 1, 1, 1])[0]

                # Increment the counter for this label set.
                counter = request_counter.labels(method=method, endpoint=endpoint, status_code=status)
                counter.inc()

                # Update the response time.
                start_time = time.time()
                time.sleep(random.uniform(0.01, 0.5))
                elapsed = time.time() - start_time
                response_time.labels(endpoint=endpoint).observe(elapsed)

                # Update CPU usage.
                current_minute = datetime.now().minute
                cpu_percent = 20 + (abs(30 - current_minute) * 2)
                cpu_usage.set(cpu_percent)

                # Update shared state.
                with values_lock:
                    last_values['request_counter'] += 1
                    last_values['response_time'] = elapsed
                    last_values['cpu_usage'] = cpu_percent

                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                time.sleep(5)

    # Start the simulator thread.
    simulator_thread = threading.Thread(target=simulate_metrics, daemon=True)
    simulator_thread.start()

    # Keep the main thread running.
    logger.info("Application running. Press Ctrl+C to exit.")
    try:
        while True:
            # Periodically print a status summary.
            with values_lock:
                total_requests = last_values['request_counter']
                avg_response = last_values['response_time']
                current_cpu = last_values['cpu_usage']

            logger.info(f"Current metrics: "
                        f"Total requests: {total_requests}, "
                        f"Last response: {avg_response:.4f}s, "
                        f"CPU: {current_cpu:.1f}%")
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
