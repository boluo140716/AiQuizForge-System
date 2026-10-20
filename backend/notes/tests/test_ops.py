import os
from unittest import mock

from notes.tests import BaseAPITestCase


class OpsTests(BaseAPITestCase):
    def test_health_ok(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_metrics_prometheus_format(self):
        response = self.client.get('/metrics/')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('quizforge_up 1', body)
        self.assertIn('quizforge_notes_total', body)
        self.assertIn('quizforge_quizzes_total', body)

    @mock.patch.dict(os.environ, {'METRICS_TOKEN': 'secret'})
    def test_metrics_requires_token_when_configured(self):
        denied = self.client.get('/metrics/')
        self.assertEqual(denied.status_code, 403)

        allowed = self.client.get('/metrics/', HTTP_X_METRICS_TOKEN='secret')
        self.assertEqual(allowed.status_code, 200)
