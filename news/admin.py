from django.contrib import admin
from .models import CustomUser, Publisher, Article, Newsletter


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """
    Admin configuration for CustomUser.
    """

    list_display = ("username", "email", "role", "is_staff")
    list_filter = ("role", "is_staff")
    search_fields = ("username", "email")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    """
    Admin interface for Publisher model.
    """

    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """
    Admin interface for Article model.
    """

    list_display = ("title", "author", "publisher", "is_approved", "created_at")
    list_filter = ("is_approved", "publisher")
    search_fields = ("title", "content", "author__username")


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """
    Admin interface for Newsletter model.
    """

    list_display = ("title", "author", "publisher", "is_published", "created_at")
    list_filter = ("is_published", "publisher")
    search_fields = ("title", "content", "author__username")
