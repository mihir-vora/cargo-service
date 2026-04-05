from rest_framework import serializers


class CargoRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    volume = serializers.IntegerField(min_value=0)


class TankRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    capacity = serializers.IntegerField(min_value=0)


class InputPayloadSerializer(serializers.Serializer):
    cargos = CargoRowSerializer(many=True)
    tanks = TankRowSerializer(many=True)


class OptimizePayloadSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()


class ResultsQuerySerializer(serializers.Serializer):
    job_id = serializers.UUIDField()


class JobCreatedResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()


class OptimizeResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    status = serializers.CharField()


class AssignmentSerializer(serializers.Serializer):
    tank_id = serializers.CharField()
    cargo_id = serializers.CharField()
    loaded_volume = serializers.IntegerField()


class ResultsResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    assignments = AssignmentSerializer(many=True)
    total_loaded_volume = serializers.IntegerField()
    cargo_remaining = serializers.DictField(child=serializers.IntegerField())
