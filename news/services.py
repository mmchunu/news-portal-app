"""
Service functions for article-related side effects
(e.g., email notifications, social media posting).
"""

from django.core.mail import send_mail
import tweepy
from django.conf import settings


def notify_subscribers_of_article(article, request):
    """
    Sends emails to:
    - Publisher subscribers (if article belongs to publisher)
    - Journalist subscribers (if independent article)
    """

    recipient_list = []

    # Publisher article
    if article.publisher:
        subscriptions = article.publisher.subscribers.all()
        recipient_list = [sub.reader.email for sub in subscriptions if sub.reader.email]

    # Independent article
    else:
        subscriptions = article.author.subscribers.all()
        recipient_list = [sub.reader.email for sub in subscriptions if sub.reader.email]

    if recipient_list:
        send_mail(
            subject=f"New Article Published: {article.title}",
            message=(
                f"Hello,\n\n"
                f"{article.author.username} has published a new article:\n"
                f"{article.title}\n\n"
                f"Read it here:\n"
                f"{request.build_absolute_uri(article.get_absolute_url())}"
            ),
            from_email=None,
            recipient_list=recipient_list,
            fail_silently=False,
        )


def post_article_to_x(article, request):
    """
    Share an approved article on X (formerly Twitter).

    On the free tier (no credits), the tweet will be simulated
    and printed to the console instead of posted.

    Parameters:
    - article: Approved Article instance.
    - request: Current HTTP request (used to build full URL).

    Returns:
    - True if posted successfully or simulated successfully.
    - False if an unexpected error occurs.
    """

    # Build tweet content
    tweet_text = (
        f"{article.title}\n\n"
        f"Read more: {request.build_absolute_uri(article.get_absolute_url())}"
    )

    try:
        # Create API v2 client
        client = tweepy.Client(
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_SECRET,
        )

        # Attempt to post tweet
        client.create_tweet(text=tweet_text)

        print("Tweet posted successfully.")
        return True

    except tweepy.errors.Forbidden as e:
        # Free tier / permission issues handled here
        print("X API restriction detected.")
        print("Simulating tweet instead:\n")
        print(f"[SIMULATED X POST]\n{tweet_text}")
        return True

    except tweepy.errors.TooManyRequests:
        print("Rate limit exceeded. Tweet not posted.")
        return False

    except Exception as e:
        print(f"Unexpected error posting to X: {e}")
        return False
