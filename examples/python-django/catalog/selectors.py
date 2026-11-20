from django.db.models import QuerySet

from catalog.models import Book


def available_books() -> 'QuerySet[Book]':
    return Book.objects.filter(available=True).select_related('author').order_by('title')


def book_by_isbn(isbn: str) -> Book:
    return Book.objects.select_related('author').get(isbn=isbn)
