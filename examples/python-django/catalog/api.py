from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog import selectors, services
from catalog.serializers import BookInputSerializer, BookOutputSerializer


class BookListApi(APIView):
    def get(self, request):
        return Response(BookOutputSerializer(selectors.available_books(), many=True).data)

    def post(self, request):
        payload = BookInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            book = services.register_book(**payload.validated_data)
        except services.BookError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookOutputSerializer(book).data, status=status.HTTP_201_CREATED)


class LendBookApi(APIView):
    def post(self, request, isbn: str):
        try:
            book = services.lend_book(isbn=isbn)
        except services.BookError as error:
            return Response({'detail': str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(BookOutputSerializer(book).data)
