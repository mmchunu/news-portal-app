from rest_framework import serializers
from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    """
    Serializer for Article model.
    Converts Article instances to JSON and validates input if needed.
    """

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "content",
            "publisher",
            "author",
            "is_approved",
            "published_at",
        ]
