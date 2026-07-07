import unittest
from unittest.mock import MagicMock, patch
from link_service import LinkService

class TestInstrumentation(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock()
        self.mock_repo.link_exists.return_value = False
        self.service = LinkService(self.mock_repo, id_generator=lambda: "test_id")

    @patch("link_service.logger")
    @patch("link_service.tracer")
    @patch("link_service.links_failed_counter")
    @patch("link_service.url_length_histogram")
    def test_create_link_invalid_url_instrumentation(self, mock_histogram, mock_failed_counter, mock_tracer, mock_logger):
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

        with self.assertRaises(ValueError):
            self.service.create_short_link("htttp://bad-url")

        mock_logger.debug.assert_called()
        mock_logger.warning.assert_called_with("Attempt to register a URL with an invalid or empty format: %s", "htttp://bad-url")
        mock_logger.error.assert_called_with("The provided URL does not meet the minimum HTTP/HTTPS requirements.")

        mock_histogram.record.assert_called_once_with(15)
        mock_failed_counter.add.assert_called_once_with(1, {"reason": "invalid_url"})

        mock_tracer.start_as_current_span.assert_called_once_with("trace_create_link_flow")
        mock_span.set_attribute.assert_any_call("link.original_url", "htttp://bad-url")
        mock_span.set_attribute.assert_any_call("error", True)

    @patch("link_service.logger")
    @patch("link_service.tracer")
    @patch("link_service.links_created_counter")
    @patch("link_service.link_creation_duration")
    def test_create_link_success_instrumentation(self, mock_duration, mock_created_counter, mock_tracer, mock_logger):
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = MagicMock()

        self.service.create_short_link("https://example.com")

        mock_logger.debug.assert_called()
        mock_logger.info.assert_any_call("Successful storage mapping completed: %s -> %s", "test_id", "https://example.com")

        mock_created_counter.add.assert_called_once_with(1, {"type": "auto"})
        mock_duration.record.assert_called_once()

        mock_tracer.start_as_current_span.assert_any_call("trace_create_link_flow")
        mock_tracer.start_as_current_span.assert_any_call("span_save_to_database")

if __name__ == "__main__":
    unittest.main()
