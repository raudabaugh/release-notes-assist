"""
GitHub Collector module for Release Notes & Documentation Assistant.
Collects merged PRs, commit messages, and issue updates from GitHub repositories.
"""

import os
import logging
from datetime import datetime, timedelta
from dateutil import parser
from github import Github, GithubException

logger = logging.getLogger(__name__)


class GitHubCollector:
    def __init__(
        self, token=None, organization=None, repository=None, collect_issues=True
    ):
        """
        Initialize GitHub collector.

        Args:
            token (str): GitHub API token
            organization (str, optional): GitHub organization name
            repository (str, optional): GitHub repository name
            collect_issues (bool, optional): Whether to collect issue data, defaults to True
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required.")

        self.github = Github(self.token)
        self.organization = organization
        self.repository = repository
        self.collect_issues = collect_issues

    def get_repositories(self):
        """Get repositories to collect data from."""
        repos = []

        if self.repository and self.organization:
            try:
                repos.append(
                    self.github.get_repo(f"{self.organization}/{self.repository}")
                )
            except GithubException as e:
                logger.error(
                    f"Failed to get repository {self.organization}/{self.repository}: {e}"
                )
        elif self.organization:
            try:
                org = self.github.get_organization(self.organization)
                repos.extend(list(org.get_repos()))
            except GithubException as e:
                logger.error(
                    f"Failed to get repositories for organization {self.organization}: {e}"
                )

        return repos

    def get_merged_prs(self, since_days=7, repository=None, timeout=300):
        """
        Get merged pull requests since a specific date.

        Args:
            since_days (int): Number of days to look back
            repository (Repository, optional): GitHub repository object
            timeout (int): Maximum seconds to spend on this operation

        Returns:
            list: List of merged pull requests
        """
        since_date = datetime.now() - timedelta(days=since_days)
        merged_prs = []

        repositories = [repository] if repository else self.get_repositories()

        start_time = datetime.now()
        pr_count = 0

        for repo in repositories:
            try:
                print(
                    f"Fetching PRs from {repo.full_name} (this may take a while for large repos)..."
                )

                # Use the search API to get merged PRs more efficiently
                # This is much faster for large repos than iterating through all PRs
                query = f"repo:{repo.full_name} is:pr is:merged merged:>={since_date.strftime('%Y-%m-%d')}"
                pulls = self.github.search_issues(query)

                total_prs = pulls.totalCount
                print(
                    f"Found {total_prs} merged PRs since {since_date.strftime('%Y-%m-%d')}"
                )

                for i, issue in enumerate(pulls):
                    # Check for timeout
                    if (datetime.now() - start_time).total_seconds() > timeout:
                        print(
                            f"Timeout reached after {timeout} seconds. Collected {pr_count} PRs so far."
                        )
                        return merged_prs

                    # Show progress periodically
                    if i % 10 == 0:
                        print(f"Processing PR {i+1}/{total_prs}...")

                    # Convert issue to PR to get PR-specific data
                    pr_number = issue.number
                    pr = repo.get_pull(pr_number)

                    # Skip PRs that don't match our criteria to be extra safe
                    if not pr.merged or not pr.merged_at or pr.merged_at < since_date:
                        continue

                    pr_count += 1
                    merged_prs.append(
                        {
                            "id": pr.number,
                            "title": pr.title,
                            "body": pr.body,
                            "url": pr.html_url,
                            "merged_at": pr.merged_at,
                            "user": pr.user.login,
                            "labels": [label.name for label in pr.labels],
                            "repository": repo.full_name,
                        }
                    )

            except Exception as e:
                logger.error(
                    f"Failed to get merged PRs for repository {repo.full_name}: {e}"
                )
                print(f"Error fetching PRs from {repo.full_name}: {e}")

        print(
            f"Successfully collected {pr_count} merged PRs in {(datetime.now() - start_time).total_seconds():.1f} seconds"
        )
        return merged_prs

    def get_recent_commits(self, since_days=7, repository=None, timeout=300):
        """
        Get recent commits since a specific date.

        Args:
            since_days (int): Number of days to look back
            repository (Repository, optional): GitHub repository object
            timeout (int): Maximum seconds to spend on this operation

        Returns:
            list: List of commits
        """
        since_date = datetime.now() - timedelta(days=since_days)
        commits = []

        repositories = [repository] if repository else self.get_repositories()

        start_time = datetime.now()
        commit_count = 0

        for repo in repositories:
            try:
                print(f"Fetching commits from {repo.full_name}...")

                # Get commit count to show progress
                repo_commits = repo.get_commits(since=since_date)

                for i, commit in enumerate(repo_commits):
                    # Check for timeout
                    if (datetime.now() - start_time).total_seconds() > timeout:
                        print(
                            f"Timeout reached after {timeout} seconds. Collected {commit_count} commits so far."
                        )
                        return commits

                    # Show progress every 50 commits
                    if i % 50 == 0:
                        print(f"Processing commit {i+1}...")

                    commit_count += 1
                    commits.append(
                        {
                            "sha": commit.sha,
                            "message": commit.commit.message,
                            "url": commit.html_url,
                            "date": commit.commit.author.date,
                            "author": commit.commit.author.name,
                            "repository": repo.full_name,
                        }
                    )

            except Exception as e:
                logger.error(
                    f"Failed to get commits for repository {repo.full_name}: {e}"
                )
                print(f"Error fetching commits from {repo.full_name}: {e}")

        print(
            f"Successfully collected {commit_count} commits in {(datetime.now() - start_time).total_seconds():.1f} seconds"
        )
        return commits

    def get_updated_issues(self, since_days=7, repository=None, timeout=300):
        """
        Get recently updated issues.

        Args:
            since_days (int): Number of days to look back
            repository (Repository, optional): GitHub repository object
            timeout (int): Maximum seconds to spend on this operation

        Returns:
            list: List of updated issues
        """
        # Early return if issue collection is disabled
        if not self.collect_issues:
            print("Issue collection is disabled, skipping.")
            return []

        since_date = datetime.now() - timedelta(days=since_days)
        issues = []

        repositories = [repository] if repository else self.get_repositories()

        start_time = datetime.now()
        issue_count = 0

        for repo in repositories:
            try:
                print(f"Fetching issues from {repo.full_name}...")

                # Use search API for better performance on large repos
                query = f"repo:{repo.full_name} is:issue updated:>={since_date.strftime('%Y-%m-%d')}"
                updated_issues = self.github.search_issues(query)

                total_issues = updated_issues.totalCount
                print(
                    f"Found {total_issues} updated issues since {since_date.strftime('%Y-%m-%d')}"
                )

                for i, issue in enumerate(updated_issues):
                    # Check for timeout
                    if (datetime.now() - start_time).total_seconds() > timeout:
                        print(
                            f"Timeout reached after {timeout} seconds. Collected {issue_count} issues so far."
                        )
                        return issues

                    # Show progress periodically
                    if i % 20 == 0:
                        print(f"Processing issue {i+1}/{total_issues}...")

                    # Skip pull requests (they are also considered issues in the GitHub API)
                    if hasattr(issue, "pull_request") and issue.pull_request:
                        continue

                    issue_count += 1
                    issues.append(
                        {
                            "id": issue.number,
                            "title": issue.title,
                            "body": issue.body,
                            "url": issue.html_url,
                            "state": issue.state,
                            "created_at": issue.created_at,
                            "updated_at": issue.updated_at,
                            "closed_at": issue.closed_at,
                            "user": issue.user.login,
                            "labels": [label.name for label in issue.labels],
                            "repository": repo.full_name,
                        }
                    )

            except Exception as e:
                logger.error(
                    f"Failed to get issues for repository {repo.full_name}: {e}"
                )
                print(f"Error fetching issues from {repo.full_name}: {e}")

        print(
            f"Successfully collected {issue_count} issues in {(datetime.now() - start_time).total_seconds():.1f} seconds"
        )
        return issues

    def collect_data(self, since_days=7, timeout=300):
        """
        Collect all data from GitHub repositories.

        Args:
            since_days (int): Number of days to look back
            timeout (int): Maximum seconds to spend on each collection type

        Returns:
            dict: Dictionary containing all collected data
        """
        print(f"Collecting GitHub data for the past {since_days} days...")

        data = {
            "collected_at": datetime.now().isoformat(),
            "collection_period_days": since_days,
        }

        # Collect PRs with timeout
        print("\nCollecting merged pull requests...")
        data["merged_prs"] = self.get_merged_prs(since_days, timeout=timeout)

        # Collect commits with timeout
        print("\nCollecting recent commits...")
        data["commits"] = self.get_recent_commits(since_days, timeout=timeout)

        # Collect issues with timeout if enabled
        print("\nCollecting updated issues...")
        if self.collect_issues:
            data["issues"] = self.get_updated_issues(since_days, timeout=timeout)
        else:
            data["issues"] = []
            print("Issue data collection is disabled")

        # Summary
        print(f"\nCollection complete!")
        print(f"- Pull Requests: {len(data['merged_prs'])}")
        print(f"- Commits: {len(data['commits'])}")
        print(f"- Issues: {len(data['issues'])}")

        return data
