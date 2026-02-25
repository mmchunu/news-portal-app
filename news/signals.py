from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def assign_group_on_create(sender, instance, created, **kwargs):
    """
    Assign user to the correct group when created
    via registration or programmatic user creation.
    """
    if created:
        instance.assign_group()
