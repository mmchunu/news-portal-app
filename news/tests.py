"""
Unit tests for the News application.

This file contains API tests for verifying:
- Authentication requirements
- Subscription-based article filtering
- Approval-based article visibility
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Publisher, Article, PublisherSubscription

User = get_user_model()


class ArticleAPITestCase(APITestCase):
    """
    Test suite for the Article API endpoint.

    These tests verify that:
    - Only authenticated users can access the endpoint
    - Readers only receive approved articles
    - Readers only receive articles from subscribed publishers
    - Readers with no subscriptions receive an empty list
    """

    def setUp(self):
        """
        Create test data before each test runs.
        """

        # Create reader user
        self.reader = User.objects.create_user(
            username="reader1",
            password="testpass123",
            role="reader",
        )

        # Create two publishers
        self.publisher1 = Publisher.objects.create(name="Tech Daily")
        self.publisher2 = Publisher.objects.create(name="Sports Weekly")

        # Subscribe reader to publisher1 only
        PublisherSubscription.objects.create(
            reader=self.reader,
            publisher=self.publisher1,
        )

        # Approved article from subscribed publisher
        self.approved_subscribed_article = Article.objects.create(
            title="AI Breakthrough",
            content="AI is advancing rapidly.",
            publisher=self.publisher1,
            author=self.reader,
            is_approved=True,
        )

        # Approved article from non-subscribed publisher
        self.approved_unsubscribed_article = Article.objects.create(
            title="Football Update",
            content="Latest match results.",
            publisher=self.publisher2,
            author=self.reader,
            is_approved=True,
        )

        # Unapproved article from subscribed publisher
        self.unapproved_article = Article.objects.create(
            title="Draft Article",
            content="This article is not approved.",
            publisher=self.publisher1,
            author=self.reader,
            is_approved=False,
        )

        # API endpoint URL
        self.url = reverse("api-article-list")

    def test_authentication_required(self):
        """
        Ensure unauthenticated users cannot access the API endpoint.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reader_receives_only_subscribed_and_approved_articles(self):
        """
        Ensure reader receives only:
        - Articles from subscribed publishers
        - Articles that are approved
        """
        # Log in the reader
        self.client.login(username="reader1", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Only one article should be returned
        self.assertEqual(len(response.data), 1)

        # Ensure the correct article is returned
        self.assertEqual(response.data[0]["title"], "AI Breakthrough")

    def test_reader_with_no_subscriptions_gets_empty_list(self):
        """
        Ensure a reader without subscriptions receives an empty list.
        """
        # Create new reader with no subscriptions
        User.objects.create_user(
            username="reader2",
            password="testpass123",
            role="reader",
        )

        self.client.login(username="reader2", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
