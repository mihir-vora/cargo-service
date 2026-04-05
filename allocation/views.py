from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .allocator import AllocationError, allocate, parse_cargos, parse_tanks
from .models import OptimizationJob
from .serializers import (
    InputPayloadSerializer,
    JobCreatedResponseSerializer,
    OptimizePayloadSerializer,
    OptimizeResponseSerializer,
    ResultsQuerySerializer,
    ResultsResponseSerializer,
)


def _first_error(errors):
    for key, val in errors.items():
        if isinstance(val, list) and val:
            return f"{key}: {val[0]}"
        if isinstance(val, dict):
            inner = _first_error(val)
            if inner:
                return f"{key}: {inner}"
    return "invalid request"


class InputView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        inbound = InputPayloadSerializer(data=request.data)
        if not inbound.is_valid():
            return Response({"error": _first_error(inbound.errors)}, status=400)

        cargos = [dict(row) for row in inbound.validated_data["cargos"]]
        tanks = [dict(row) for row in inbound.validated_data["tanks"]]
        try:
            parse_cargos(cargos)
            parse_tanks(tanks)
        except AllocationError as err:
            return Response({"error": str(err)}, status=400)

        job = OptimizationJob.objects.create(cargos=cargos, tanks=tanks)
        outbound = JobCreatedResponseSerializer(data={"job_id": str(job.id)})
        outbound.is_valid(raise_exception=True)
        return Response(outbound.data)


class OptimizeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        inbound = OptimizePayloadSerializer(data=request.data)
        if not inbound.is_valid():
            return Response({"error": _first_error(inbound.errors)}, status=400)

        job_id = inbound.validated_data["job_id"]
        try:
            job = OptimizationJob.objects.get(id=job_id)
        except OptimizationJob.DoesNotExist:
            return Response({"error": "job not found"}, status=404)

        try:
            cargo_specs = parse_cargos(job.cargos)
            tank_specs = parse_tanks(job.tanks)
        except AllocationError as err:
            return Response({"error": str(err)}, status=400)

        result = allocate(cargo_specs, tank_specs)
        job.result = result
        job.optimized_at = timezone.now()
        job.save(update_fields=["result", "optimized_at"])

        outbound = OptimizeResponseSerializer(
            data={"job_id": str(job.id), "status": "ok"},
        )
        outbound.is_valid(raise_exception=True)
        return Response(outbound.data)


class ResultsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        inbound = ResultsQuerySerializer(data=request.query_params)
        if not inbound.is_valid():
            return Response({"error": _first_error(inbound.errors)}, status=400)

        job_id = inbound.validated_data["job_id"]
        try:
            job = OptimizationJob.objects.get(id=job_id)
        except OptimizationJob.DoesNotExist:
            return Response({"error": "job not found"}, status=404)

        if job.result is None:
            return Response(
                {"error": "optimization has not been run for this job"},
                status=409,
            )

        payload = {
            "job_id": str(job.id),
            "assignments": job.result["assignments"],
            "total_loaded_volume": job.result["total_loaded_volume"],
            "cargo_remaining": job.result["cargo_remaining"],
        }
        outbound = ResultsResponseSerializer(data=payload)
        outbound.is_valid(raise_exception=True)
        return Response(outbound.data)
