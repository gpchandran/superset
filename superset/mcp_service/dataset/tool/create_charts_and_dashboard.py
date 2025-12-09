# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
# under the License.
"""Dataset-driven chart and dashboard generation MCP tool."""

from __future__ import annotations

from typing import List

from fastmcp import Context
from superset_core.mcp import tool

from superset.mcp_service.chart.schemas import GenerateChartRequest, GenerateChartResponse
from superset.mcp_service.chart.tool.generate_chart import generate_chart
from superset.mcp_service.dashboard.schemas import (
    GenerateDashboardRequest,
    GenerateDashboardResponse,
)
from superset.mcp_service.dashboard.tool.generate_dashboard import generate_dashboard
from superset.mcp_service.dataset.schemas import (
    CreateDatasetVisualizationsRequest,
    CreateDatasetVisualizationsResponse,
)
from superset.mcp_service.utils.schema_utils import parse_request


def _build_chart_requests(
    request: CreateDatasetVisualizationsRequest,
) -> List[GenerateChartRequest]:
    """Construct per-chart requests from the dataset-level request."""

    chart_requests: List[GenerateChartRequest] = []
    for chart_spec in request.charts:
        preview_formats = chart_spec.preview_formats or request.preview_formats
        chart_requests.append(
            GenerateChartRequest(
                dataset_id=request.dataset_id,
                config=chart_spec.config,
                save_chart=request.save_charts,
                generate_preview=request.generate_previews,
                preview_formats=preview_formats,
                cache_timeout=request.cache_timeout,
                force=request.force,
            )
        )

    return chart_requests


def _build_dashboard_request(
    request: CreateDatasetVisualizationsRequest, chart_ids: List[int]
) -> GenerateDashboardRequest:
    """Create a dashboard generation request using created chart IDs."""

    title = request.dashboard_title or f"Dashboard for dataset {request.dataset_id}"
    return GenerateDashboardRequest(
        chart_ids=chart_ids,
        dashboard_title=title,
        description=request.dashboard_description,
        published=request.publish_dashboard,
    )


@tool(tags=["mutate"])
@parse_request(CreateDatasetVisualizationsRequest)
async def create_charts_and_dashboard_from_dataset(
    request: CreateDatasetVisualizationsRequest, ctx: Context
) -> CreateDatasetVisualizationsResponse:
    """Create charts from a dataset and optionally assemble them into a dashboard."""

    await ctx.info(
        "Starting dataset visualization pipeline: dataset_id=%s, charts=%s",
        request.dataset_id,
        len(request.charts),
    )

    chart_requests = _build_chart_requests(request)
    chart_responses: List[GenerateChartResponse] = []

    for index, chart_request in enumerate(chart_requests, start=1):
        await ctx.report_progress(index, len(chart_requests), "Generating chart")
        chart_response = await generate_chart(chart_request, ctx)
        chart_responses.append(chart_response)

    successful_chart_ids = [
        chart_response.chart.id
        for chart_response in chart_responses
        if chart_response.success and chart_response.chart
    ]

    dashboard_response: GenerateDashboardResponse | None = None
    if request.create_dashboard:
        if successful_chart_ids:
            dashboard_request = _build_dashboard_request(request, successful_chart_ids)
            await ctx.report_progress(
                len(chart_requests) + 1,
                len(chart_requests) + 1,
                "Creating dashboard",
            )
            dashboard_response = generate_dashboard(dashboard_request, ctx)
        else:
            dashboard_response = GenerateDashboardResponse(
                dashboard=None,
                dashboard_url=None,
                error="No charts were created successfully; dashboard was not generated.",
            )

    success = all(response.success for response in chart_responses)
    if request.create_dashboard:
        success = success and bool(
            dashboard_response and dashboard_response.dashboard is not None
        )

    message = "Created charts successfully"
    if request.create_dashboard:
        message = (
            "Created charts and dashboard successfully"
            if success
            else "Charts created, but dashboard generation failed"
        )
        if dashboard_response and dashboard_response.error:
            message = dashboard_response.error

    return CreateDatasetVisualizationsResponse(
        charts=chart_responses,
        dashboard=dashboard_response.dashboard if dashboard_response else None,
        dashboard_url=dashboard_response.dashboard_url if dashboard_response else None,
        success=success,
        message=message,
    )
