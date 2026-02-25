from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.db.models import Q

from .models import (
    CustomUser,
    Article,
    Newsletter,
    Publisher,
    PublisherSubscription,
    JournalistSubscription,
)
from .models import ROLE_EDITOR, ROLE_JOURNALIST, ROLE_READER
from .forms import ArticleForm, NewsletterForm, PublisherForm
from .services import notify_subscribers_of_article
from rest_framework import generics, permissions
from rest_framework.authentication import TokenAuthentication
from .serializers import ArticleSerializer

# Get the custom user model defined in settings
User = get_user_model()

# ==========================================================
# Authentication Views
# ==========================================================


class UserRegistrationForm(forms.ModelForm):
    """
    Form for registering a new user.
    """

    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = CustomUser
        fields = ["username", "email", "role"]

    def clean_password2(self):
        """
        Verify that both password entries match.
        """
        cd = self.cleaned_data
        if cd["password"] != cd["password2"]:
            raise forms.ValidationError("Passwords don't match.")
        return cd["password2"]


def user_register(request):
    """
    Handles user registration.
    """
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data["password"])
            new_user.save()
            messages.success(request, "Registration successful. You can now log in.")
            return redirect("login")
    else:
        form = UserRegistrationForm()

    return render(request, "news/register.html", {"form": form})


def user_login(request):
    """
    Handles user login.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "news/login.html")


@login_required
def user_logout(request):
    """
    Logs out the current user.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


# =====================================================
# Public / Reader Views
# =====================================================


def home(request):
    """
    Home page view.

    Displays:
    - Latest published articles
    - Latest published newsletters

    Content is visible to both authenticated users and guests.
    """

    # Get latest 5 published articles
    latest_articles = Article.objects.filter(
        published_at__isnull=False  # Only show published articles
    ).order_by("-published_at")[:5]

    # Get latest 5 published newsletters
    latest_newsletters = Newsletter.objects.filter(
        published_at__isnull=False  # Only show published newsletters
    ).order_by("-published_at")[:5]

    # Context dictionary passed to template
    context = {
        "latest_articles": latest_articles,
        "latest_newsletters": latest_newsletters,
    }

    # Render home template
    return render(request, "news/home.html", context)


def article_list(request):
    """
    Display a list of articles based on user role and publisher association.

    Rules:
    - Readers and journalists see only approved articles.
    - Editors see:
        * All approved articles.
        * Pending articles only from publishers they are associated with.
    - Independent articles (no publisher) are always visible.
    """
    user = request.user

    # Determine visible articles
    if user.is_authenticated and user.role == "editor":
        # Editors: approved + pending from their publishers
        approved_articles = Article.objects.filter(is_approved=True)
        pending_articles = Article.objects.filter(
            is_approved=False, publisher__editors=user
        )
        articles = (approved_articles | pending_articles).distinct()
    else:
        # Guests, readers, journalists: only approved articles
        articles = Article.objects.filter(is_approved=True)

    # Add permission flags for template
    for article in articles:
        article.can_edit = False
        article.can_delete = False
        article.can_approve = False

        if user.is_authenticated:
            # Author can edit/delete their own article
            if user == article.author:
                article.can_edit = True
                article.can_delete = True

            # Editors associated with the publisher
            if (
                article.publisher
                and user.role == "editor"
                and user in article.publisher.editors.all()
            ):
                article.can_edit = True
                article.can_delete = True
                if not article.is_approved:
                    article.can_approve = True

    # Order by newest published first
    articles = articles.order_by("-published_at", "-created_at")

    return render(request, "news/article_list.html", {"articles": articles})


@login_required
def article_detail(request, pk):
    """
    Display the full content of a single article.

    Access rules:
    - Approved articles:
        * Readers must be subscribed (publisher or journalist).
        * Editors and journalists can view normally.
    - Pending articles:
        * Only editors associated with that publisher can view.
    """

    # Get the article, 404 if it doesn't exist
    article = get_object_or_404(Article, pk=pk)
    user = request.user

    # DEFAULT: Editors & Journalists always have access
    has_access = True

    # Handle pending articles
    if not article.is_approved:
        if (
            user.role == "editor"
            and article.publisher
            and user in article.publisher.editors.all()
        ):
            has_access = True
        else:
            return HttpResponseForbidden(
                "You do not have permission to view this article."
            )

    # Handle approved articles
    else:
        # Subscription check only applies to readers
        if user.role == "reader":

            # If article belongs to a publisher
            if article.publisher:
                has_access = PublisherSubscription.objects.filter(
                    reader=user, publisher=article.publisher
                ).exists()

            # If article is independent
            else:
                has_access = JournalistSubscription.objects.filter(
                    reader=user, journalist=article.author
                ).exists()

        # Editors and journalists automatically have access
        else:
            has_access = True

    # Permission flags
    can_edit = False
    can_delete = False
    can_approve = False

    if user.is_authenticated:

        # Author permissions
        if user == article.author:
            can_edit = True
            can_delete = True

        # Editor permissions
        if (
            article.publisher
            and user.role == "editor"
            and user in article.publisher.editors.all()
        ):
            can_edit = True
            can_delete = True

            if not article.is_approved:
                can_approve = True

    return render(
        request,
        "news/article_detail.html",
        {
            "article": article,
            "has_access": has_access,
            "can_edit": can_edit,
            "can_delete": can_delete,
            "can_approve": can_approve,
        },
    )


@login_required
def newsletter_list(request):
    """
    Display all newsletters the user can access.

    Readers: only newsletters by editors they are subscribed to.
    Editors: all newsletters they created.
    """
    user = request.user

    if user.role == ROLE_READER:
        # Readers: filter by subscriptions
        newsletters = (
            Newsletter.objects.filter(is_published=True)
            .filter(
                Q(
                    author__subscribers__reader=user
                )  # independent newsletters (journalist)
                | Q(
                    publisher__subscribers__reader=user
                )  # editor newsletters (publisher)
            )
            .distinct()
        )
    else:
        # Editors & journalists: see all newsletters they authored
        newsletters = Newsletter.objects.filter(author=user)

    return render(request, "news/newsletter_list.html", {"newsletters": newsletters})


@login_required
def newsletter_detail(request, pk):
    """
    Display full newsletter content with access control.
    """
    newsletter = get_object_or_404(Newsletter, pk=pk)
    user = request.user
    has_access = False

    # Editors/Journalists can view their own newsletters
    if user == newsletter.author:
        has_access = True

    # Inside newsletter_detail view
    elif user.role == ROLE_READER:
        # Check if reader is subscribed
        if newsletter.publisher:
            # Newsletter belongs to a publisher → check publisher subscription
            has_access = PublisherSubscription.objects.filter(
                reader=user, publisher=newsletter.publisher
            ).exists()
        else:
            # Independent newsletter → check journalist subscription
            has_access = JournalistSubscription.objects.filter(
                reader=user, journalist=newsletter.author
            ).exists()

    return render(
        request,
        "news/newsletter_detail.html",
        {"newsletter": newsletter, "has_access": has_access},
    )


@login_required
def journalist_list(request):
    """
    Display all journalists.
    Readers can subscribe/unsubscribe.
    """

    journalists = CustomUser.objects.filter(role=ROLE_JOURNALIST)

    # Get subscriptions of current reader
    subscribed_journalist_ids = []
    if request.user.role == ROLE_READER:
        subscribed_journalist_ids = request.user.journalist_subscriptions.values_list(
            "journalist__id", flat=True
        )

    return render(
        request,
        "news/journalist_list.html",
        {
            "journalists": journalists,
            "subscribed_journalist_ids": subscribed_journalist_ids,
        },
    )


@login_required
def my_subscriptions(request):
    """
    Show all subscriptions of the current reader.
    Includes both journalist and publisher subscriptions.
    """
    user = request.user

    if user.role != ROLE_READER:
        # Only readers have subscriptions
        return HttpResponseForbidden("Only readers have subscriptions.")

    # Get actual subscription objects
    publisher_subscriptions = PublisherSubscription.objects.filter(reader=user)
    journalist_subscriptions = JournalistSubscription.objects.filter(reader=user)

    return render(
        request,
        "news/my_subscriptions.html",
        {
            "publisher_subscriptions": publisher_subscriptions,
            "journalist_subscriptions": journalist_subscriptions,
        },
    )


# =====================================================
# Journalist Views Only
# =====================================================


@login_required
@permission_required("news.add_article", raise_exception=True)
def article_create(request):
    """
    Allow journalists to create new articles.

    Publishing rules:
    - If no publisher is selected → auto-approved.
    - If a publisher is selected → must be approved by an editor
      associated with that publisher.
    """

    if request.method == "POST":
        form = ArticleForm(request.POST, user=request.user)

        if form.is_valid():
            article = form.save(commit=False)

            # Assign logged-in user as author
            article.author = request.user

            # Independent publishing (no publisher selected)
            if article.publisher is None:
                article.is_approved = True
                article.published_at = timezone.now()
            else:
                # Requires editor approval
                article.is_approved = False

            article.save()

            # Notify subscribers for independent articles
            if article.is_approved:
                notify_subscribers_of_article(article, request)

            messages.success(request, "Article created successfully.")
            return redirect("my_articles")
    else:
        form = ArticleForm(user=request.user)

    # Render the article creation form template
    return render(request, "news/article_create.html", {"form": form})


@login_required
def newsletter_create(request):
    """
    Allow editors to create newsletters.
    """
    user = request.user

    if user.role not in [ROLE_EDITOR, ROLE_JOURNALIST]:
        return HttpResponseForbidden("Only editors can create newsletters.")

    if request.method == "POST":
        form = NewsletterForm(request.POST, user=user)
        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.author = user
            newsletter.save()

            messages.success(request, "Newsletter created successfully.")
            return redirect("newsletter_detail", pk=newsletter.pk)
    else:
        form = NewsletterForm(user=user)

    return render(
        request, "news/newsletter_form.html", {"form": form, "newsletter": None}
    )


# =====================================================
# Journalist and Editor Views
# =====================================================


@login_required
@permission_required("news.change_article", raise_exception=True)
def article_update(request, pk):
    """
    Allows the journalist or editor to update an existing article.
    """
    article = get_object_or_404(Article, pk=pk)
    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()

            messages.success(request, "Article updated successfully.")
            return redirect("article_detail", pk=article.pk)
    else:
        form = ArticleForm(instance=article)
    return render(request, "news/article_edit.html", {"form": form, "article": article})


@login_required
def article_delete(request, pk):
    """
    Delete an article with proper ownership checks.

    Rules:
    - Journalists can delete their own articles.
    - Editors can delete articles belonging to publishers they manage.
    """

    article = get_object_or_404(Article, pk=pk)

    # Journalist: can delete ONLY their own article
    if request.user.role == "journalist":
        if article.author != request.user:
            return HttpResponseForbidden("You can only delete your own articles.")

    # Editor: can delete ONLY articles from publishers they belong to
    elif request.user.role == "editor":
        if article.publisher:
            if request.user not in article.publisher.editors.all():
                return HttpResponseForbidden(
                    "You can only delete articles from publishers you manage."
                )
        else:
            # Editors cannot delete independent articles
            return HttpResponseForbidden("You cannot delete independent articles.")

    # Anyone else → forbidden
    else:
        return HttpResponseForbidden(
            "You do not have permission to delete this article."
        )

    # Delete confirmation
    if request.method == "POST":
        article.delete()

        messages.success(request, "Article deleted successfully.")
        return redirect("my_articles")

    return render(request, "news/article_delete.html", {"article": article})


@login_required
def newsletter_update(request, pk):
    """
    Allow editors and journalists to edit their own newsletters.
    Only the author can edit.
    """

    # Get newsletter or 404
    newsletter = get_object_or_404(Newsletter, pk=pk)

    # Prevent non-authors from editing
    if request.user != newsletter.author:
        return HttpResponseForbidden("You cannot edit this newsletter.")

    if request.method == "POST":
        form = NewsletterForm(request.POST, instance=newsletter, user=request.user)
        if form.is_valid():
            form.save()

            messages.success(request, "Newsletter updated successfully.")
            return redirect("newsletter_detail", pk=newsletter.pk)
    else:
        form = NewsletterForm(instance=newsletter, user=request.user)

    return render(
        request, "news/newsletter_form.html", {"form": form, "newsletter": newsletter}
    )


@login_required
def newsletter_delete(request, pk):
    """
    Allow editors and journalists to delete their own newsletters.
    Only the author can delete.
    """

    newsletter = get_object_or_404(Newsletter, pk=pk)

    # Prevent non-authors from deleting
    if request.user != newsletter.author:
        return HttpResponseForbidden("You cannot delete this newsletter.")

    if request.method == "POST":
        newsletter.delete()

        messages.success(request, "Newsletter deleted successfully.")
        return redirect("my_newsletters")

    return render(
        request, "news/newsletter_confirm_delete.html", {"newsletter": newsletter}
    )


@login_required
def my_articles(request):
    """
    Display all articles created by the logged-in user (journalist or editor).

    Shows:
    - Independent articles
    - Articles under a publisher
    - All statuses (pending, approved, draft, etc.)
    """
    # Filter articles authored by the current user
    articles = Article.objects.filter(author=request.user).order_by("-created_at")

    return render(request, "news/my_articles.html", {"articles": articles})


@login_required
def my_newsletters(request):
    """
    Display newsletters created by the logged-in user.

    Only editors and journalists are allowed to access this page.
    Each user can only see their own newsletters.
    """

    # Allow only editor and journalist roles
    if request.user.role not in ["editor", "journalist"]:
        messages.error(request, "You do not have permission to view this page.")
        return redirect("home")

    # Filter newsletters belonging to the logged-in user
    newsletters = Newsletter.objects.filter(author=request.user)

    return render(request, "news/my_newsletters.html", {"newsletters": newsletters})


# =====================================================
# Editor Views Only
# =====================================================


@login_required
def publisher_list(request):
    """
    List all publishers.

    - Readers: see all publishers with subscribe/unsubscribe buttons.
    - Editors/Journalists: see only publishers they manage/are associated with.
    """
    user = request.user

    if user.role == ROLE_READER:
        # All publishers for readers
        publishers = Publisher.objects.all()

        # Get IDs of publishers the user is subscribed to
        subscribed_publisher_ids = user.publisher_subscriptions.values_list(
            "publisher__id", flat=True
        )
    else:
        # Editors & journalists: see only associated publishers
        publishers = Publisher.objects.filter(editors=user) | Publisher.objects.filter(
            journalists=user
        )
        publishers = publishers.distinct()
        subscribed_publisher_ids = []  # not used for editors

    return render(
        request,
        "news/publisher_list.html",
        {
            "publishers": publishers,
            "subscribed_publisher_ids": subscribed_publisher_ids,
        },
    )


@login_required
def publisher_create(request):
    """
    Allows an editor to create a new publisher.

    Only users with the Editor role can create publishers.
    """

    # Ensure only editors can create publishers
    if request.user.role != ROLE_EDITOR:
        return HttpResponseForbidden("Only editors can create publishers.")

    # Handle form submission
    if request.method == "POST":
        form = PublisherForm(request.POST)

        if form.is_valid():
            # Save publisher instance without committing many-to-many relationships yet
            publisher = form.save(commit=False)
            publisher.save()

            # Save any many-to-many relationships (editors/journalists) from the form
            form.save_m2m()

            # Automatically add the current editor as one of the publisher's editors
            publisher.editors.add(request.user)

            # Success message
            messages.success(
                request, f'Publisher "{publisher.name}" created successfully.'
            )

            # Redirect to publisher list (more logical than article list)
            return redirect("publisher_list")

    else:
        # GET request — display blank form
        form = PublisherForm()

    return render(request, "news/publisher_create.html", {"form": form})


@login_required
def publisher_update(request, pk):
    """
    Allow editors to update a publisher they are associated with.
    """
    publisher = get_object_or_404(Publisher, pk=pk)

    # Permission check: editor must be linked to publisher
    if request.user.role != ROLE_EDITOR or request.user not in publisher.editors.all():
        return HttpResponseForbidden(
            "You do not have permission to edit this publisher."
        )

    if request.method == "POST":
        form = PublisherForm(request.POST, instance=publisher)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'Publisher "{publisher.name}" updated successfully.'
            )
            return redirect("publisher_list")
    else:
        form = PublisherForm(instance=publisher)

    # Render the correct template for editing
    return render(request, "news/publisher_edit.html", {"form": form})


@login_required
def publisher_delete(request, pk):
    """
    Allow editors to delete a publisher they are associated with.
    """
    publisher = get_object_or_404(Publisher, pk=pk)

    # Permission check
    if request.user.role != ROLE_EDITOR or request.user not in publisher.editors.all():
        return HttpResponseForbidden(
            "You do not have permission to delete this publisher."
        )

    if request.method == "POST":
        publisher.delete()
        messages.success(request, f'Publisher "{publisher.name}" deleted successfully.')
        return redirect("publisher_list")

    return render(
        request, "news/publisher_confirm_delete.html", {"publisher": publisher}
    )


@login_required
def pending_articles(request):
    """
    Display all articles that are currently pending approval.

    Only users with the 'editor' role are allowed to access this page.
    """
    # Ensure only editors can access this view
    if request.user.role != "editor":
        messages.error(request, "You do not have permission to view this page.")
        return redirect("home")

    # Get all articles with status 'pending'
    articles = Article.objects.filter(is_approved=False)

    return render(request, "news/pending_articles.html", {"articles": articles})


@login_required
@permission_required("news.change_article", raise_exception=True)
def article_approve(request, article_id):
    """
    Allow editors to approve articles.
    Sends emails to subscribers.

    Conditions:
    - User must have the Editor role.
    - User must be associated with the article's publisher.
    - Article must belong to a publisher.
    """

    article = get_object_or_404(Article, id=article_id)

    # Ensure user is actually an editor
    if request.user.role != "editor":
        return HttpResponseForbidden("Only editors can approve articles.")

    # Article must be linked to a publisher
    if article.publisher is None:
        return HttpResponseForbidden("Independent articles do not require approval.")

    # Editor must belong to this publisher
    if article.publisher not in request.user.editor_publishers.all():
        return HttpResponseForbidden("You are not associated with this publisher.")

    # Mark article as approved
    article.is_approved = True
    article.published_at = timezone.now()  # set publish timestamp
    article.save()

    # Send email notifications if article belongs to a publisher
    notify_subscribers_of_article(article, request)

    # Success message
    messages.success(
        request,
        f'Article "{article.title}" has been approved and subscribers notified.',
    )
    return redirect("pending_articles")


# =====================================================
# Error Handlers
# =====================================================


def permission_denied(request, exception=None):
    """
    Custom 403 permission denied handler.
    """
    return HttpResponseForbidden("You do not have permission to perform this action.")


# =====================================================
# Reader Views
# =====================================================


@login_required
def publisher_detail(request, pk):
    """
    Display publisher details and subscription status.
    """

    publisher = get_object_or_404(Publisher, pk=pk)
    user = request.user

    is_subscribed = False

    # Only readers can subscribe
    if user.role == "reader":
        is_subscribed = PublisherSubscription.objects.filter(
            reader=user, publisher=publisher
        ).exists()

    # Articles for this publisher
    if user.is_authenticated and user.role == "editor":
        # Editors: approved + pending from this publisher
        approved_articles = Article.objects.filter(
            is_approved=True, publisher=publisher
        )
        pending_articles = Article.objects.filter(
            is_approved=False, publisher=publisher, publisher__editors=user
        )
        articles = (approved_articles | pending_articles).distinct()
    else:
        # Readers & guests: only approved articles
        articles = Article.objects.filter(is_approved=True, publisher=publisher)

    # Permission flags (for edit/delete/approve buttons)
    for article in articles:
        article.can_edit = False
        article.can_delete = False
        article.can_approve = False

        if user.is_authenticated:
            if user == article.author:
                article.can_edit = True
                article.can_delete = True

            if (
                article.publisher
                and user.role == "editor"
                and user in article.publisher.editors.all()
            ):
                article.can_edit = True
                article.can_delete = True
                if not article.is_approved:
                    article.can_approve = True

    # Order articles by newest published first
    articles = articles.order_by("-published_at", "-created_at")

    return render(
        request,
        "news/publisher_detail.html",
        {
            "publisher": publisher,
            "is_subscribed": is_subscribed,
            "articles": articles,
        },
    )


@login_required
def publisher_subscribe(request, pk):
    """
    Subscribe or unsubscribe a reader to a publisher.
    """

    publisher = get_object_or_404(Publisher, pk=pk)
    user = request.user

    # Only readers can subscribe
    if user.role != "reader":
        return redirect("publisher_detail", pk=pk)

    subscription = PublisherSubscription.objects.filter(
        reader=user, publisher=publisher
    )

    if subscription.exists():
        # If already subscribed → unsubscribe
        subscription.delete()
    else:
        # If not subscribed → subscribe
        PublisherSubscription.objects.create(reader=user, publisher=publisher)

    # Redirect back if 'next' parameter exists, else go to publisher detail
    next_url = request.GET.get("next")
    if next_url:
        return redirect(next_url)

    return redirect("publisher_detail", pk=pk)


@login_required
def journalist_detail(request, pk):
    """
    Display the journalist profile page.

    Shows journalist information and whether the
    current logged-in user is subscribed to them.
    """
    journalist = get_object_or_404(User, pk=pk)
    user = request.user

    # Only journalists should have this page
    if journalist.role != "journalist":
        return HttpResponseForbidden("This user is not a journalist.")

    # Check if the current user is subscribed to this journalist
    is_subscribed = False
    if request.user.role == "reader":
        is_subscribed = JournalistSubscription.objects.filter(
            reader=request.user, journalist=journalist
        ).exists()

    # Articles by this journalist
    if user.is_authenticated and user.role == "editor":
        # Editors: all approved + pending for editor's publishers
        approved_articles = Article.objects.filter(is_approved=True, author=journalist)
        pending_articles = Article.objects.filter(
            is_approved=False, author=journalist, publisher__editors=user
        )
        articles = (approved_articles | pending_articles).distinct()
    else:
        # Readers & guests: only approved articles
        articles = Article.objects.filter(is_approved=True, author=journalist)

    # Add permission flags
    for article in articles:
        article.can_edit = False
        article.can_delete = False
        article.can_approve = False

        if user.is_authenticated:
            if user == article.author:
                article.can_edit = True
                article.can_delete = True

            if (
                article.publisher
                and user.role == "editor"
                and user in article.publisher.editors.all()
            ):
                article.can_edit = True
                article.can_delete = True
                if not article.is_approved:
                    article.can_approve = True

    # Order newest first
    articles = articles.order_by("-published_at", "-created_at")

    return render(
        request,
        "news/journalist_detail.html",
        {
            "journalist": journalist,
            "is_subscribed": is_subscribed,
            "articles": articles,
        },
    )


@login_required
def journalist_subscription(request, pk):
    """
    Subscribe or unsubscribe the current user
    from a journalist.
    """
    journalist = get_object_or_404(CustomUser, pk=pk)

    # Ensure target is a journalist
    if journalist.role != "journalist":
        return HttpResponseForbidden("Cannot subscribe to a non-journalist.")

    # Only readers can subscribe
    if request.user.role != "reader":
        return HttpResponseForbidden("Only readers can subscribe to journalists.")

    # Check if subscription exists
    subscription = JournalistSubscription.objects.filter(
        reader=request.user, journalist=journalist
    ).first()

    if subscription:
        # Already subscribed → unsubscribe
        subscription.delete()
    else:
        # Not subscribed → subscribe
        JournalistSubscription.objects.create(
            reader=request.user, journalist=journalist
        )

    # Redirect back if 'next' parameter exists, else go to journalist detail
    next_url = request.GET.get("next")
    if next_url:
        return redirect(next_url)

    # Redirect back to journalist profile
    return redirect("journalist_detail", pk=pk)


# =====================================================
# API Views
# =====================================================


class ArticleListAPIView(generics.ListAPIView):
    """
    API view to list articles for authenticated readers.
    Only returns approved articles from publishers the reader is subscribed to.
    """

    serializer_class = ArticleSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Override get_queryset to filter articles based on reader subscriptions.
        Returns:
            QuerySet: Articles approved and from subscribed publishers.
        """
        user = self.request.user

        # If user is not a reader, return empty queryset
        if user.role != "reader":
            return Article.objects.none()

        # Get IDs of publishers the user is subscribed to
        subscribed_publishers = user.publisher_subscriptions.values_list(
            "publisher", flat=True
        )

        # Return approved articles only from subscribed publishers
        return Article.objects.filter(
            publisher__in=subscribed_publishers, is_approved=True
        )
