from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

# ==========================
# Role constants
# ==========================
ROLE_READER = "reader"
ROLE_JOURNALIST = "journalist"
ROLE_EDITOR = "editor"

ROLE_CHOICES = [
    (ROLE_READER, "Reader"),
    (ROLE_JOURNALIST, "Journalist"),
    (ROLE_EDITOR, "Editor"),
]


class CustomUser(AbstractUser):
    """
    Custom user model.

    Roles:
    - Reader: Can only view articles and newsletters
    - Journalist: Can create, view, update, delete articles/newsletters
    - Editor: Can view, update, delete articles/newsletters
    """

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_READER,
        help_text="Role of the user: Reader, Journalist, or Editor",
    )

    def assign_group(self) -> None:
        """
        Assign the user to the appropriate Django auth group
        based on their role.
        """
        role_to_group = {
            ROLE_READER: "Reader",
            ROLE_JOURNALIST: "Journalist",
            ROLE_EDITOR: "Editor",
        }

        group_name = role_to_group.get(self.role)

        if not group_name:
            return  # No valid role → no group assignment

        group, _ = Group.objects.get_or_create(name=group_name)

        # Ensure user belongs to only one role-based group
        self.groups.clear()
        self.groups.add(group)

    def save(self, *args, **kwargs):
        """
        Override save to ensure admin-created users
        are assigned to the correct group.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Admin creates user → signals may not fire reliably
        if is_new:
            self.assign_group()


class Publisher(models.Model):
    """
    Represents a news publisher.

    A publisher can have multiple editors and journalists.
    Articles may be published under a publisher.
    """

    name = models.CharField(
        max_length=255, unique=True, help_text="Unique name of the publisher."
    )
    description = models.TextField(
        blank=True, help_text="Optional description of the publisher."
    )
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="editor_publishers",
        blank=True,
        help_text="Editors associated with this publisher.",
    )
    journalists = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="journalist_publishers",
        blank=True,
        help_text="Journalists associated with this publisher.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the publisher was created."
    )

    def __str__(self) -> str:
        """
        String representation of the Publisher.
        """
        return self.name


class Article(models.Model):
    """
    Represents a news article.

    Publishing rules:
    - If published independently (no publisher), it is auto-approved.
    - If published under a publisher, it must be approved by
      an editor associated with that publisher.
    """

    title = models.CharField(max_length=255, help_text="Title of the article.")
    content = models.TextField(help_text="Full content of the article.")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="articles",
        help_text="Journalist who authored the article.",
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        help_text="Publisher under which the article is published (optional).",
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Indicates whether the article has been approved by an editor.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the article was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the article was last updated."
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the article is published (approved).",
    )

    class Meta:
        # Newest published articles appear first
        ordering = ["-published_at", "-created_at"]

    def save(self, *args, **kwargs):
        """
        Ensure that whenever an article is approved,
        it automatically gets a published_at timestamp.
        """

        # If approved but no publish time yet
        if self.is_approved and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """
        String representation of the Article.
        """
        return self.title

    def get_absolute_url(self):
        return reverse("article_detail", kwargs={"pk": self.pk})


class Newsletter(models.Model):
    """
    Represents a newsletter created by an editor or a journalist.

    Editors: newsletters must belong to a publisher.
    Journalists: newsletters are independent (no publisher).
    """

    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="newsletters"
    )
    publisher = models.ForeignKey(
        "Publisher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Required for editors, leave blank for journalists.",
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def save(self, *args, **kwargs):
        """Set published_at automatically when published."""
        # Ensure editors provide a publisher
        if self.author.role == ROLE_EDITOR and not self.publisher:
            raise ValueError("Editors must select a publisher for their newsletter.")

        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PublisherSubscription(models.Model):
    """
    A reader subscribes to a publisher.
    """

    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="publisher_subscriptions",
        limit_choices_to={"role": "reader"},  # Only readers can subscribe
    )
    publisher = models.ForeignKey(
        "Publisher", on_delete=models.CASCADE, related_name="subscribers"
    )
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reader", "publisher")  # Prevent duplicates

    def __str__(self):
        return f"{self.reader.username} → {self.publisher.name}"


class JournalistSubscription(models.Model):
    """
    A reader subscribes to a journalist.
    """

    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journalist_subscriptions",
        limit_choices_to={"role": "reader"},  # Only readers can subscribe
    )
    journalist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscribers",
        limit_choices_to={
            "role": "journalist"
        },  # Only journalists can be subscribed to
    )
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reader", "journalist")  # Prevent duplicates

    def __str__(self):
        return f"{self.reader.username} → {self.journalist.username}"
