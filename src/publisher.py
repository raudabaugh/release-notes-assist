"""
Publisher module for Release Notes & Documentation Assistant.
Publishes release notes to GitHub releases, Confluence, and Slack.
"""

import os
import logging
import json
import requests
from datetime import datetime
from github import Github, GithubException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from atlassian import Confluence

logger = logging.getLogger(__name__)


class Publisher:
    def __init__(
        self,
        github_token=None,
        slack_token=None,
        confluence_url=None,
        confluence_username=None,
        confluence_token=None,
    ):
        """
        Initialize the publisher with API tokens.

        Args:
            github_token (str, optional): GitHub API token
            slack_token (str, optional): Slack API token
            confluence_url (str, optional): Confluence URL
            confluence_username (str, optional): Confluence username
            confluence_token (str, optional): Confluence API token
        """
        # GitHub configuration
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.github = None
        if self.github_token:
            self.github = Github(self.github_token)

        # Slack configuration
        self.slack_token = slack_token or os.environ.get("SLACK_TOKEN")
        self.slack_client = None
        if self.slack_token:
            self.slack_client = WebClient(token=self.slack_token)

        # Confluence configuration
        self.confluence_url = confluence_url or os.environ.get("CONFLUENCE_URL")
        self.confluence_username = confluence_username or os.environ.get(
            "CONFLUENCE_USERNAME"
        )
        self.confluence_token = confluence_token or os.environ.get("CONFLUENCE_TOKEN")
        self.confluence = None
        if all([self.confluence_url, self.confluence_username, self.confluence_token]):
            self.confluence = Confluence(
                url=self.confluence_url,
                username=self.confluence_username,
                password=self.confluence_token,
            )

    def publish_to_github(
        self,
        repo_name,
        tag_name,
        release_notes,
        name=None,
        draft=False,
        prerelease=False,
    ):
        """
        Publish release notes to GitHub Releases.

        Args:
            repo_name (str): Repository name in format 'owner/repo'
            tag_name (str): Tag for the release (e.g., v1.0.0)
            release_notes (str): Release notes content
            name (str, optional): Release title
            draft (bool, optional): Whether the release is a draft
            prerelease (bool, optional): Whether the release is a prerelease

        Returns:
            bool: Success status
        """
        if not self.github:
            logger.error(
                "GitHub client not initialized. Make sure GITHUB_TOKEN is set."
            )
            return False

        try:
            repo = self.github.get_repo(repo_name)

            # Create release
            release = repo.create_git_release(
                tag=tag_name,
                name=name or f"Release {tag_name}",
                message=release_notes,
                draft=draft,
                prerelease=prerelease,
            )

            logger.info(f"Successfully published release {tag_name} to GitHub")
            return True

        except GithubException as e:
            logger.error(f"Failed to publish to GitHub: {e}")
            return False

    def publish_to_slack(self, channel_id, release_notes, title=None):
        """
        Publish release notes to Slack.

        Args:
            channel_id (str): Slack channel ID
            release_notes (str): Release notes content
            title (str, optional): Title for the Slack message

        Returns:
            bool: Success status
        """
        if not self.slack_client:
            logger.error("Slack client not initialized. Make sure SLACK_TOKEN is set.")
            return False

        try:
            # Format the release notes for Slack
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title or "📝 New Release Notes",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": release_notes[:3000],  # Slack has text limits
                    },
                },
            ]

            # If release notes are too long, add a continuation message
            if len(release_notes) > 3000:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "...(content truncated due to length limits. See full release notes on GitHub)...",
                        },
                    }
                )

            # Post the message
            response = self.slack_client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=title or "New Release Notes",  # Fallback text
            )

            logger.info(
                f"Successfully published release notes to Slack channel {channel_id}"
            )
            return True

        except SlackApiError as e:
            logger.error(f"Failed to publish to Slack: {e}")
            return False

    def publish_to_confluence(
        self, space_key, parent_page_id, release_notes, title=None
    ):
        """
        Publish release notes to Confluence.

        Args:
            space_key (str): Confluence space key
            parent_page_id (str): Parent page ID
            release_notes (str): Release notes content (in markdown)
            title (str, optional): Title for the Confluence page

        Returns:
            bool: Success status
        """
        if not self.confluence:
            logger.error(
                "Confluence client not initialized. Make sure CONFLUENCE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_TOKEN are set."
            )
            return False

        try:
            page_title = (
                title or f"Release Notes - {datetime.now().strftime('%Y-%m-%d')}"
            )

            # Check if page already exists
            existing_page = self.confluence.get_page_by_title(
                space=space_key, title=page_title
            )

            # Convert markdown to Confluence storage format (simplified approach)
            # In a real scenario, you might want to use a proper markdown to Confluence converter
            content = f'<ac:structured-macro ac:name="markdown">\n<ac:plain-text-body><![CDATA[\n{release_notes}\n]]></ac:plain-text-body>\n</ac:structured-macro>'

            if existing_page:
                # Update existing page
                self.confluence.update_page(
                    page_id=existing_page["id"], title=page_title, body=content
                )
                logger.info(f"Successfully updated Confluence page '{page_title}'")
            else:
                # Create new page
                self.confluence.create_page(
                    space=space_key,
                    title=page_title,
                    body=content,
                    parent_id=parent_page_id,
                    representation="storage",
                )
                logger.info(f"Successfully created Confluence page '{page_title}'")

            return True

        except Exception as e:
            logger.error(f"Failed to publish to Confluence: {e}")
            return False

    def publish_all(self, release_notes, data):
        """
        Publish release notes to all configured platforms.

        Args:
            release_notes (str): Release notes content (in markdown)
            data (dict): Configuration data containing publishing details

        Returns:
            dict: Results for each publishing platform
        """
        results = {"github": False, "slack": False, "confluence": False}

        # Publish to GitHub if configured
        if self.github and data.get("github"):
            github_config = data["github"]
            results["github"] = self.publish_to_github(
                repo_name=github_config.get("repo_name"),
                tag_name=github_config.get("tag_name"),
                release_notes=release_notes,
                name=github_config.get("name"),
                draft=github_config.get("draft", False),
                prerelease=github_config.get("prerelease", False),
            )

        # Publish to Slack if configured
        if self.slack_client and data.get("slack"):
            slack_config = data["slack"]
            results["slack"] = self.publish_to_slack(
                channel_id=slack_config.get("channel_id"),
                release_notes=release_notes,
                title=slack_config.get("title"),
            )

        # Publish to Confluence if configured
        if self.confluence and data.get("confluence"):
            confluence_config = data["confluence"]
            results["confluence"] = self.publish_to_confluence(
                space_key=confluence_config.get("space_key"),
                parent_page_id=confluence_config.get("parent_page_id"),
                release_notes=release_notes,
                title=confluence_config.get("title"),
            )

        return results
