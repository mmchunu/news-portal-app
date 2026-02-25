from django.urls import path
from . import views
from .views import ArticleListAPIView

urlpatterns = [
    # Authentication URLs
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.user_register, name="register"),
    # Home URL
    path("", views.home, name="home"),
    # Article URLs
    path("articles/", views.article_list, name="article_list"),
    path("create/", views.article_create, name="article_create"),
    path("articles/<int:pk>/", views.article_detail, name="article_detail"),
    path("edit/<int:pk>/", views.article_update, name="article_update"),
    path("articles/pending/", views.pending_articles, name="pending_articles"),
    path("approve/<int:article_id>/", views.article_approve, name="article_approve"),
    path("delete/<int:pk>/", views.article_delete, name="article_delete"),
    path("articles/my/", views.my_articles, name="my_articles"),
    # Newsletter URLs
    path("newsletters/", views.newsletter_list, name="newsletter_list"),
    path("newsletters/<int:pk>/", views.newsletter_detail, name="newsletter_detail"),
    path("newsletters/create/", views.newsletter_create, name="newsletter_create"),
    path(
        "newsletters/<int:pk>/edit/", views.newsletter_update, name="newsletter_update"
    ),
    path(
        "newsletters/<int:pk>/delete/",
        views.newsletter_delete,
        name="newsletter_delete",
    ),
    path("newsletters/my/", views.my_newsletters, name="my_newsletters"),
    # Publisher URLs
    path("publishers/", views.publisher_list, name="publisher_list"),
    path("publishers/create/", views.publisher_create, name="publisher_create"),
    path("publishers/edit/<int:pk>/", views.publisher_update, name="publisher_update"),
    path(
        "publishers/delete/<int:pk>/", views.publisher_delete, name="publisher_delete"
    ),
    path("publishers/<int:pk>/", views.publisher_detail, name="publisher_detail"),
    path(
        "publishers/<int:pk>/subscribe/",
        views.publisher_subscribe,
        name="publisher_subscribe",
    ),
    # Journalist URLs
    path("journalists/", views.journalist_list, name="journalist_list"),
    path("journalists/<int:pk>/", views.journalist_detail, name="journalist_detail"),
    path(
        "journalists/<int:pk>/subscribe/",
        views.journalist_subscription,
        name="journalist_subscription",
    ),
    # Subscription URLs
    path("subscriptions/", views.my_subscriptions, name="my_subscriptions"),
    # API URLs
    path("api/articles/", ArticleListAPIView.as_view(), name="api-article-list"),
]
