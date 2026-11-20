from rest_framework import serializers


class BookInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300)
    isbn = serializers.CharField(min_length=13, max_length=13)
    author_name = serializers.CharField(max_length=200)


class BookOutputSerializer(serializers.Serializer):
    title = serializers.CharField()
    isbn = serializers.CharField()
    author = serializers.CharField(source='author.name')
    available = serializers.BooleanField()
