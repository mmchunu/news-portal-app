from django import forms
from django.contrib.auth import get_user_model
from .models import Article, Newsletter, Publisher
from .models import ROLE_EDITOR, ROLE_JOURNALIST

User = get_user_model()


class ArticleForm(forms.ModelForm):
    """
    Form to create or update an Article.
    """

    class Meta:
        model = Article

        # Fields displayed in the form
        fields = ["title", "content", "publisher"]

        # Custom input styling
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Enter title"}),
            "content": forms.Textarea(attrs={"placeholder": "Write your article here"}),
        }

    def __init__(self, *args, **kwargs):
        """
        Restrict publisher choices to only those
        the logged-in journalist is associated with.
        """

        # Extract user from kwargs (passed from view)
        user = kwargs.pop("user", None)

        # Call parent constructor
        super().__init__(*args, **kwargs)

        # If user is a journalist, filter publishers
        if user and user.role == "journalist":

            # Show only publishers linked to this journalist
            self.fields["publisher"].queryset = user.journalist_publishers.all()


class NewsletterForm(forms.ModelForm):
    """Form for creating/editing newsletters."""

    class Meta:
        model = Newsletter
        fields = ["title", "content", "publisher", "is_published"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 10}),
        }

    def __init__(self, *args, **kwargs):
        """Customize form fields based on user role."""
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            if user.role == ROLE_JOURNALIST:
                # Journalists cannot select publisher
                self.fields["publisher"].widget = forms.HiddenInput()
            elif user.role == ROLE_EDITOR:
                # Editors must select from existing publishers
                self.fields["publisher"].queryset = Publisher.objects.all()


class PublisherForm(forms.ModelForm):
    """
    Form for creating and managing publishers.
    """

    editors = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role="editor"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    journalists = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role="journalist"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Publisher
        fields = ["name", "description", "editors", "journalists"]
