from django.db import transaction

from catalog.integrations.isbn import checksum_valid
from catalog.models import Author, Book


class BookError(ValueError):
    pass


@transaction.atomic
def register_book(*, title: str, isbn: str, author_name: str) -> Book:
    if not checksum_valid(isbn):
        raise BookError(f'invalid ISBN-13: {isbn}')
    author, _ = Author.objects.get_or_create(name=author_name)
    return Book.objects.create(title=title, isbn=isbn, author=author)


@transaction.atomic
def lend_book(*, isbn: str) -> Book:
    book = Book.objects.select_for_update().get(isbn=isbn)
    if not book.available:
        raise BookError(f'{isbn} is already lent out')
    book.available = False
    book.save(update_fields=['available'])
    return book
