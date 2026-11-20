from rest_framework.test import APITestCase


class BookApiTest(APITestCase):
    def test_register_list_and_lend(self):
        created = self.client.post('/api/books/', {'title': 'Domain-Driven Design', 'isbn': '9780321125217', 'author_name': 'Eric Evans'})
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()['author'], 'Eric Evans')

        listed = self.client.get('/api/books/')
        self.assertEqual([b['isbn'] for b in listed.json()], ['9780321125217'])

        lent = self.client.post('/api/books/9780321125217/lend/')
        self.assertEqual(lent.status_code, 200)
        self.assertEqual(self.client.post('/api/books/9780321125217/lend/').status_code, 409)
        self.assertEqual(self.client.get('/api/books/').json(), [])

    def test_invalid_isbn_is_rejected(self):
        response = self.client.post('/api/books/', {'title': 'X', 'isbn': '9780321125218', 'author_name': 'Y'})
        self.assertEqual(response.status_code, 400)
