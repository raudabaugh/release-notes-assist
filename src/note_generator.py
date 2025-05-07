"""
Note Generator module for Release Notes & Documentation Assistant.
Uses GPT-4o to generate human-friendly release notes from GitHub data.
"""

import os
import logging
import json
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class NoteGenerator:
    def __init__(
        self,
        api_key=None,
        model="gpt-4o",
        azure_endpoint=None,
        azure_deployment=None,
        azure_api_version=None,
    ):
        """
        Initialize the note generator.

        Args:
            api_key (str, optional): Azure OpenAI API key
            model (str, optional): OpenAI model to use, defaults to "gpt-4o"
            azure_endpoint (str, optional): Azure OpenAI endpoint URL
            azure_deployment (str, optional): Azure OpenAI deployment name
            azure_api_version (str, optional): Azure OpenAI API version
        """
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Azure OpenAI API key is required.")

        self.azure_endpoint = azure_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        if not self.azure_endpoint:
            raise ValueError("Azure OpenAI endpoint is required.")

        self.azure_deployment = (
            azure_deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT") or model
        )
        self.azure_api_version = (
            azure_api_version
            or os.environ.get("AZURE_OPENAI_API_VERSION")
            or "2023-05-15"
        )

        self.model = self.azure_deployment  # Use deployment name as the model name
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.azure_api_version,
            azure_endpoint=self.azure_endpoint,
        )

    def _create_release_notes_prompt(
        self, github_data, format_type="markdown", version=None
    ):
        """
        Create a prompt for GPT-4o to generate release notes.

        Args:
            github_data (dict): GitHub data including PRs, commits, and issues
            format_type (str): Output format type (markdown, html)
            version (str, optional): Version number for the release

        Returns:
            str: Formatted prompt for GPT-4o
        """
        merged_prs_text = ""
        for pr in github_data.get("merged_prs", []):
            merged_prs_text += f"- PR #{pr['id']}: {pr['title']} ({pr['url']})\n"
            if pr.get("body"):
                merged_prs_text += f"  Description: {pr['body']}\n"
            merged_prs_text += f"  Labels: {', '.join(pr['labels'])}\n"
            merged_prs_text += f"  Author: {pr['user']}\n\n"

        commits_text = ""
        for commit in github_data.get("commits", []):
            commits_text += (
                f"- Commit {commit['sha'][:7]}: {commit['message']} ({commit['url']})\n"
            )
            commits_text += f"  Author: {commit['author']}\n\n"

        issues_text = ""
        for issue in github_data.get("issues", []):
            status = "closed" if issue["state"] == "closed" else "updated"
            issues_text += f"- Issue #{issue['id']} ({status}): {issue['title']} ({issue['url']})\n"
            if issue.get("body"):
                issues_text += f"  Description: {issue['body']}\n"
            issues_text += f"  Labels: {', '.join(issue['labels'])}\n\n"

        version_text = f"Version: {version}\n" if version else ""
        period_text = (
            f"Collection period: {github_data.get('collection_period_days', 7)} days"
        )

        prompt = f"""
You are a technical writer creating release notes for a software project. 
Please generate comprehensive release notes based on the following GitHub data.
{version_text}
{period_text}

## Merged Pull Requests:
{merged_prs_text if merged_prs_text else "No pull requests merged in this period."}

## Commits:
{commits_text if commits_text else "No commits in this period."}

## Issues:
{issues_text if issues_text else "No issues updated in this period."}

Please organize the release notes into the following sections:
1. Summary (brief overview of the changes)
2. New Features
3. Bug Fixes
4. Documentation Updates
5. Other Changes

Format the release notes in {format_type} format and make them user-friendly.
Include links to PRs, issues, and commits where relevant.
Focus on the impact to users rather than technical implementation details.
"""
        print("Prompt length: %d characters", len(prompt))
        return prompt

    def _create_documentation_update_prompt(self, github_data, doc_type="technical"):
        """
        Create a prompt for GPT-4o to generate documentation updates.

        Args:
            github_data (dict): GitHub data including PRs, commits, and issues
            doc_type (str): Type of documentation (technical, user, api)

        Returns:
            str: Formatted prompt for GPT-4o
        """
        # Here we focus on extracting documentation-relevant changes
        doc_related_prs = []
        for pr in github_data.get("merged_prs", []):
            # Check for documentation-related labels or keywords in title/body
            is_doc_related = any(
                label.lower() in ["documentation", "docs", "readme"]
                for label in pr["labels"]
            )
            is_doc_related = (
                is_doc_related
                or "doc" in pr["title"].lower()
                or "readme" in pr["title"].lower()
            )

            if pr.get("body") and is_doc_related == False:
                is_doc_related = (
                    "doc" in pr["body"].lower() or "readme" in pr["body"].lower()
                )

            if is_doc_related:
                doc_related_prs.append(pr)

        # Also extract feature PRs that might need documentation
        feature_prs = []
        for pr in github_data.get("merged_prs", []):
            # Check for feature-related labels or keywords
            is_feature = any(
                label.lower() in ["feature", "enhancement", "new"]
                for label in pr["labels"]
            )
            is_feature = (
                is_feature
                or "feature" in pr["title"].lower()
                or "add" in pr["title"].lower()
            )

            if is_feature and pr not in doc_related_prs:
                feature_prs.append(pr)

        # Format the prompt
        doc_prs_text = ""
        for pr in doc_related_prs:
            doc_prs_text += f"- PR #{pr['id']}: {pr['title']} ({pr['url']})\n"
            if pr.get("body"):
                doc_prs_text += f"  Description: {pr['body']}\n"
            doc_prs_text += f"  Labels: {', '.join(pr['labels'])}\n\n"

        feature_prs_text = ""
        for pr in feature_prs:
            feature_prs_text += f"- PR #{pr['id']}: {pr['title']} ({pr['url']})\n"
            if pr.get("body"):
                feature_prs_text += f"  Description: {pr['body']}\n"
            feature_prs_text += f"  Labels: {', '.join(pr['labels'])}\n\n"

        prompt = f"""
You are a technical writer updating documentation for a software project.
Please suggest documentation updates based on the following GitHub data.

## Documentation-Related Pull Requests:
{doc_prs_text if doc_prs_text else "No documentation-specific pull requests in this period."}

## New Features That Might Need Documentation:
{feature_prs_text if feature_prs_text else "No new features added in this period."}

Please provide the following:
1. Summary of documentation changes needed
2. Specific sections that should be updated or created
3. Sample content for each section (in markdown format)

Focus on {doc_type} documentation specifically.
"""
        return prompt

    def generate_release_notes(self, github_data, format_type="markdown", version=None):
        """
        Generate release notes using GPT-4o.

        Args:
            github_data (dict): GitHub data including PRs, commits, and issues
            format_type (str): Output format type (markdown, html)
            version (str, optional): Version number for the release

        Returns:
            str: Generated release notes
        """
        prompt = self._create_release_notes_prompt(github_data, format_type, version)

        try:
            response = self.client.chat.completions.create(
                model=self.model,  # Just use model, not deployment_id
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional technical writer creating clear, concise release notes.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating release notes: {e}")
            return f"Error generating release notes: {e}"

    def generate_documentation_update(self, github_data, doc_type="technical"):
        """
        Generate documentation update suggestions using GPT-4o.

        Args:
            github_data (dict): GitHub data including PRs, commits, and issues
            doc_type (str): Type of documentation (technical, user, api)

        Returns:
            str: Generated documentation update suggestions
        """
        prompt = self._create_documentation_update_prompt(github_data, doc_type)

        try:
            response = self.client.chat.completions.create(
                model=self.model,  # Just use model, not deployment_id
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional technical writer creating clear, comprehensive documentation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating documentation update: {e}")
            return f"Error generating documentation update: {e}"
