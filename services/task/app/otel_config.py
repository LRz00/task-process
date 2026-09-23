"""OpenTelemetry configuration for Task Service."""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


def init_opentelemetry(service_name: str = "task-service") -> None:
    """Initialize OpenTelemetry with Jaeger exporter."""
    
    jaeger_host = os.getenv("JAEGER_HOST", "localhost")
    jaeger_port = int(os.getenv("JAEGER_PORT", 6831))
    
    # Create Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )
    
    # Create tracer provider with resource
    resource = Resource.create({SERVICE_NAME: service_name})
    tracer_provider = TracerProvider(resource=resource)
    
    # Add span processor with Jaeger exporter
    tracer_provider.add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )
    
    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # Instrument requests for inter-service communication
    RequestsInstrumentor().instrument(tracer_provider=tracer_provider)


def instrument_fastapi_app(app) -> None:
    """Instrument a FastAPI app instance."""
    FastAPIInstrumentor.instrument_app(
        app=app,
        excluded_urls=".*health.*",  # Exclude all health endpoints
    )

