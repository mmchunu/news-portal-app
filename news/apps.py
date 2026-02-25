from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_user_groups(sender, **kwargs):
    """
    Create user groups and assign permissions after migrations.

    Groups:
    - Reader: View articles only
    - Journalist: Create, view, update, delete articles
    - Editor: View, update, delete articles
    """
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    from .models import Article

    content_type = ContentType.objects.get_for_model(Article)

    # Reader group permissions
    reader_group, _ = Group.objects.get_or_create(name="Reader")
    view_article_perm = Permission.objects.get(
        codename="view_article", content_type=content_type
    )
    reader_group.permissions.set([view_article_perm])

    # Journalist group permissions
    journalist_group, _ = Group.objects.get_or_create(name="Journalist")
    journalist_perms = Permission.objects.filter(
        codename__in=[
            "add_article",
            "view_article",
            "change_article",
            "delete_article",
        ],
        content_type=content_type,
    )
    journalist_group.permissions.set(journalist_perms)

    # Editor group permissions
    editor_group, _ = Group.objects.get_or_create(name="Editor")
    editor_perms = Permission.objects.filter(
        codename__in=[
            "view_article",
            "change_article",
            "delete_article",
        ],
        content_type=content_type,
    )
    editor_group.permissions.set(editor_perms)


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news"

    def ready(self):
        """
        Register post-migrate signal to ensure
        groups and permissions are created automatically.
        """
        post_migrate.connect(create_user_groups, sender=self)
