from django.urls import path

from catalog.api import BookListApi, LendBookApi

urlpatterns = [
    path('books/', BookListApi.as_view(), name='books'),
    path('books/<str:isbn>/lend/', LendBookApi.as_view(), name='lend-book'),
]
