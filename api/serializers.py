from rest_framework import serializers

class DocumentProcessSerializer(serializers.Serializer):
    file = serializers.FileField()
    extract_entities = serializers.BooleanField(default=True)
    force_ocr = serializers.BooleanField(default=False)
    language = serializers.CharField(default="eng")

class DocumentSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=True)
    document_type = serializers.CharField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    limit = serializers.IntegerField(default=20)
    offset = serializers.IntegerField(default=0)

class DocumentBatchProcessSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(), min_length=1)
    async_process = serializers.BooleanField(default=True, source='async')
