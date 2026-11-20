from django.db import models


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Author(TimeStamped):
    name = models.CharField(max_length=200, unique=True)


class Book(TimeStamped):
    title = models.CharField(max_length=300)
    isbn = models.CharField(max_length=13, unique=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    available = models.BooleanField(default=True)
