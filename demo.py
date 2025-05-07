#!/usr/bin/env python
"""
Demo script for the Release Notes & Documentation Assistant.
This script demonstrates the workflow using sample data.
"""
import os
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from src.note_generator import NoteGenerator
from src.github_collector import GitHubCollector

# Load environment variables from .env file
load_dotenv()


def load_config(config_path="config/config.json"):
    """
    Load configuration from a JSON file.

    Args:
        config_path (str): Path to the configuration file

    Returns:
        dict: Configuration data
    """
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(
            f"Configuration file not found at {config_path}, using default configuration"
        )
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON in configuration file {config_path}")
        return {}


def main():
    """Run a demonstration of release notes generation."""
    parser = argparse.ArgumentParser(
        description="Release Notes & Documentation Assistant Demo"
    )
    parser.add_argument(
        "--sample-data",
        default="tests/test_data/sample_github_data.json",
        help="Path to sample GitHub data JSON file",
    )
    parser.add_argument(
        "--output-dir", default="demo_output", help="Directory to save output files"
    )
    parser.add_argument(
        "--collect-issues",
        action="store_true",
        help="Whether to collect issue data (overrides config setting)",
    )
    parser.add_argument(
        "--no-collect-issues",
        action="store_false",
        dest="collect_issues",
        help="Disable issue data collection (overrides config setting)",
    )
    parser.add_argument(
        "--use-live-data",
        action="store_true",
        help="Use live GitHub data instead of sample data",
    )
    parser.add_argument(
        "--config", default="config/config.json", help="Path to configuration file"
    )
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    print(
        f"Starting Release Notes & Documentation Assistant demo at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # Load configuration
    config = load_config(args.config)
    print(f"Loaded configuration from {args.config}")

    # Load data
    github_data = {}
    if args.use_live_data:
        print("Collecting live data from GitHub...")

        # Get GitHub settings from config
        github_token = os.environ.get("GITHUB_TOKEN")
        github_org = config.get("github", {}).get("organization")
        github_repo = config.get("github", {}).get("repository")

        # Check if collect_issues was explicitly set in arguments
        if args.collect_issues is None:
            # If not set in arguments, use the config setting
            collect_issues = config.get("github", {}).get("collect_issues", True)
        else:
            # Use the command line argument setting
            collect_issues = args.collect_issues

        if not github_token:
            print(
                "ERROR: No GitHub token found. Set the GITHUB_TOKEN environment variable."
            )
            print("Falling back to sample data...")
            args.use_live_data = False
        elif not github_org and not github_repo:
            print("WARNING: Neither organization nor repository specified in config.")
            print(
                "Specify at least one in config.json to collect data from specific repositories."
            )
            print(
                "Will attempt to collect data from repositories accessible to your token."
            )
        else:
            print(
                f"Using GitHub token: {github_token[:4]}...{github_token[-4:] if len(github_token) > 8 else ''}"
            )
            if github_org:
                print(f"Organization: {github_org}")
            if github_repo:
                print(f"Repository: {github_repo}")
            print(f"Collecting issues: {'Yes' if collect_issues else 'No'}")

            try:
                since_days = config.get("schedule", {}).get("look_back_days", 7)
                print(
                    f"Looking for activity in the last {since_days} days (from config)..."
                )

                github_collector = GitHubCollector(
                    token=github_token,
                    organization=github_org,
                    repository=github_repo,
                    collect_issues=collect_issues,
                )

                # Get repositories first to verify access
                repos = github_collector.get_repositories()
                if not repos:
                    print(
                        "ERROR: No repositories found or accessible with the current token."
                    )
                    print(
                        "Check your GitHub token permissions and organization/repository names in config.json."
                    )
                    print("Falling back to sample data...")
                    args.use_live_data = False
                else:
                    print(
                        f"Found {len(repos)} accessible repositories: {', '.join([repo.full_name for repo in repos])}"
                    )

                    # Collect data
                    github_data = github_collector.collect_data(since_days=since_days)

                    pr_count = len(github_data.get("merged_prs", []))
                    commit_count = len(github_data.get("commits", []))
                    issue_count = len(github_data.get("issues", []))

                    print(
                        f"Collected {pr_count} PRs, {commit_count} commits, and {issue_count} issues"
                    )

                    if pr_count == 0 and commit_count == 0 and issue_count == 0:
                        print("No recent activity found. This could be because:")
                        print(
                            f"1. There has been no activity in the last {since_days} days"
                        )
                        print("2. The token doesn't have sufficient permissions")
                        print(
                            "3. The organization or repository names are incorrect in config.json"
                        )

                        # Ask if user wants to proceed with sample data instead
                        response = input(
                            "Would you like to use sample data instead? (y/n): "
                        )
                        if response.lower() in ["y", "yes"]:
                            args.use_live_data = False  # Fall back to sample data
                        else:
                            # Proceed with empty data
                            print("Proceeding with empty data set...")
            except Exception as e:
                print(f"Error collecting GitHub data: {e}")
                print("Falling back to sample data...")
                args.use_live_data = False  # Fall back to sample data

    if not args.use_live_data:
        print(f"Loading sample data from {args.sample_data}")
        try:
            with open(args.sample_data, "r") as f:
                github_data = json.load(f)

            # If issue collection is disabled in args or config, clear the issues array
            collect_issues = (
                args.collect_issues
                if args.collect_issues is not None
                else config.get("github", {}).get("collect_issues", True)
            )
            if not collect_issues:
                print(
                    "Issue data collection is disabled, removing issues from sample data"
                )
                github_data["issues"] = []
        except Exception as e:
            print(f"Error loading sample data: {e}")
            return

    # Initialize note generator
    print("Initializing GPT-4o note generator...")
    try:
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        if azure_endpoint:
            note_generator = NoteGenerator(
                api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                azure_endpoint=azure_endpoint,
                azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
                azure_api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
            )
            print("Using Azure OpenAI for note generation")
        else:
            note_generator = NoteGenerator(api_key=os.environ.get("OPENAI_API_KEY"))
            print("Using OpenAI for note generation")
    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure you have set the appropriate API key environment variables.")
        return

    # Generate release notes
    version = config.get("publish", {}).get("github", {}).get("tag_name", "v1.0.0")
    format_type = config.get("output", {}).get("format", "markdown")
    print(
        f"Generating release notes from GitHub activity (version: {version}, format: {format_type})..."
    )
    release_notes = note_generator.generate_release_notes(
        github_data=github_data, format_type=format_type, version=version
    )

    # Generate documentation update suggestions
    doc_type = config.get("output", {}).get("doc_type", "technical")
    if config.get("generate_doc_updates", True):
        print(f"Generating documentation update suggestions (type: {doc_type})...")
        doc_updates = note_generator.generate_documentation_update(
            github_data=github_data, doc_type=doc_type
        )
    else:
        print("Documentation updates generation is disabled in config")
        doc_updates = None

    # Save the generated content
    release_notes_path = os.path.join(
        args.output_dir, f"release_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    with open(release_notes_path, "w") as f:
        f.write(release_notes)
    print(f"Release notes saved to: {release_notes_path}")

    if doc_updates:
        doc_updates_path = os.path.join(
            args.output_dir,
            f"doc_updates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        )
        with open(doc_updates_path, "w") as f:
            f.write(doc_updates)
        print(f"Documentation update suggestions saved to: {doc_updates_path}")

    print(
        "\nDemo complete! These files show how the assistant can automatically generate:"
    )
    print("1. Human-friendly release notes from technical GitHub activity")
    print("2. Suggestions for documentation updates based on recent changes")
    print("\nIn a real deployment, these would be automatically published to:")
    print("- GitHub Releases page")
    print("- Confluence documentation")
    print("- Slack channels for team visibility")


if __name__ == "__main__":
    main()
