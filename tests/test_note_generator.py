"""
Unit tests for the note generator module.
"""

import unittest
import json
import os
from unittest.mock import patch, MagicMock
from src.note_generator import NoteGenerator


class TestNoteGenerator(unittest.TestCase):
    """Tests for the NoteGenerator class."""

    def setUp(self):
        """Set up test environment."""
        # Load sample data
        sample_data_path = os.path.join(
            os.path.dirname(__file__), "test_data", "sample_github_data.json"
        )
        with open(sample_data_path, "r") as f:
            self.sample_github_data = json.load(f)

        # Mock environment variable
        self.env_patcher = patch.dict("os.environ", {"OPENAI_API_KEY": "mock_api_key"})
        self.env_patcher.start()

    def tearDown(self):
        """Tear down test environment."""
        self.env_patcher.stop()

    @patch("openai.OpenAI")
    def test_generate_release_notes(self, mock_openai):
        """Test release notes generation."""
        # Set up the mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = (
            "# Release Notes\n\n## Summary\n\nThis release includes new dashboard features, bug fixes for mobile devices, and improved API documentation."
        )
        mock_client.chat.completions.create.return_value = mock_completion

        # Create the note generator
        generator = NoteGenerator()

        # Generate release notes
        notes = generator.generate_release_notes(
            self.sample_github_data, version="v1.0.0"
        )

        # Check that the OpenAI client was called correctly
        mock_client.chat.completions.create.assert_called_once()

        # Verify that the mock response was returned
        self.assertIn("Release Notes", notes)
        self.assertIn("Summary", notes)
        self.assertIn("dashboard features", notes)

    @patch("openai.OpenAI")
    def test_generate_documentation_update(self, mock_openai):
        """Test documentation update generation."""
        # Set up the mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = (
            "# Documentation Updates\n\n## API Documentation\n\nUpdate the REST API documentation to include the new endpoints."
        )
        mock_client.chat.completions.create.return_value = mock_completion

        # Create the note generator
        generator = NoteGenerator()

        # Generate documentation updates
        updates = generator.generate_documentation_update(self.sample_github_data)

        # Check that the OpenAI client was called correctly
        mock_client.chat.completions.create.assert_called_once()

        # Verify that the mock response was returned
        self.assertIn("Documentation Updates", updates)
        self.assertIn("API Documentation", updates)
        self.assertIn("REST API documentation", updates)


if __name__ == "__main__":
    unittest.main()
