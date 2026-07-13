"""OpenTelemetry provider setup.

This is *host* configuration (which exporters/providers to wire up), shared by
every adapter (Flask, serverless, ...). The actual instrumentation — spans and
counters — lives in the framework-agnostic core (``linker_app`` and
``link_service``), so the same telemetry is emitted regardless of the host.
"""

import logging

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_telemetry_configured = False


def configure_metrics(service_name):
    resource = Resource.create({"service.name": service_name})
    exporter = OTLPMetricExporter()
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)


def configure_tracing(service_name):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)


def configure_telemetry(service_name="linker-python", traces_enabled=True, testing=False):
    """Configure OTLP metrics and traces once for the running process."""
    global _telemetry_configured

    if testing or not traces_enabled or _telemetry_configured:
        return

    configure_metrics(service_name)
    configure_tracing(service_name)
    _telemetry_configured = True
