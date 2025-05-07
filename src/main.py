"""
Main entry point for the Release Notes & Documentation Assistant.
This module orchestrates the collection of GitHub data, generation of release notes,
and publishing to various platforms.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
import schedule
import time

from src.github_collector import GitHubCollector
from src.note_generator import NoteGenerator
from src.publisher import Publisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"release_notes_{datetime.now().strftime('%Y%m%d')}.log"),
    ],
)
logger = logging.getLogger(__name__)


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
        logger.warning(
            f"Configuration file not found at {config_path}, using default configuration"
        )
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in configuration file {config_path}")
        return {}


def save_data(data, output_path=None):
    """
    Save data to a JSON file.

    Args:
        data (dict): Data to save
        output_path (str, optional): Path to save the data

    Returns:
        str: Path where the data was saved
    """
    if not output_path:
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir, f"github_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    try:
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved data to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        return None


def generate_and_publish(config, since_days=7, version=None):
    """
    Generate release notes and publish them.

    Args:
        config (dict): Configuration data
        since_days (int): Number of days to look back for GitHub data
        version (str, optional): Version number for the release

    Returns:
        bool: Success status
    """
    try:
        # 1. Collect GitHub data
        github_collector = GitHubCollector(
            token=os.environ.get("GITHUB_TOKEN"),
            organization=config.get("github", {}).get("organization"),
            repository=config.get("github", {}).get("repository"),
            collect_issues=config.get("github", {}).get("collect_issues", True),
        )
        github_data = github_collector.collect_data(since_days=since_days)

        # Save collected data
        data_path = save_data(github_data)

        # 2. Generate release notes
        note_generator = NoteGenerator(api_key=os.environ.get("OPENAI_API_KEY"))
        release_notes = note_generator.generate_release_notes(
            github_data=github_data,
            format_type=config.get("output", {}).get("format", "markdown"),
            version=version,
        )

        doc_updates = None
        if config.get("generate_doc_updates", False):
            doc_updates = note_generator.generate_documentation_update(
                github_data=github_data,
                doc_type=config.get("output", {}).get("doc_type", "technical"),
            )

        # Save generated release notes
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        release_notes_path = os.path.join(
            output_dir, f"release_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )

        with open(release_notes_path, "w") as f:
            f.write(release_notes)
            if doc_updates:
                f.write("\n\n## Documentation Update Suggestions\n\n")
                f.write(doc_updates)

        logger.info(f"Saved release notes to {release_notes_path}")

        # 3. Publish release notes
        if config.get("publish", {}).get("enabled", False):
            publisher = Publisher(
                github_token=os.environ.get("GITHUB_TOKEN"),
                slack_token=os.environ.get("SLACK_TOKEN"),
                confluence_url=os.environ.get("CONFLUENCE_URL"),
                confluence_username=os.environ.get("CONFLUENCE_USERNAME"),
                confluence_token=os.environ.get("CONFLUENCE_TOKEN"),
            )

            publish_data = {
                "github": config.get("publish", {}).get("github", {}),
                "slack": config.get("publish", {}).get("slack", {}),
                "confluence": config.get("publish", {}).get("confluence", {}),
            }

            # Update tag_name with version if provided
            if version and "github" in publish_data:
                publish_data["github"]["tag_name"] = version

            results = publisher.publish_all(release_notes, publish_data)

            logger.info(f"Publishing results: {results}")

            return all(results.values())

        return True

    except Exception as e:
        logger.error(f"Error in generate_and_publish: {e}", exc_info=True)
        return False


def run_scheduled_job(config):
    """
    Run a scheduled job to generate and publish release notes.

    Args:
        config (dict): Configuration data
    """
    logger.info("Running scheduled release notes generation job")

    schedule_config = config.get("schedule", {})
    since_days = schedule_config.get("look_back_days", 7)

    generate_and_publish(config, since_days)


def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(
        description="Release Notes & Documentation Assistant"
    )
    parser.add_argument(
        "--config", default="config/config.json", help="Path to configuration file"
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=7,
        help="Number of days to look back for GitHub data",
    )
    parser.add_argument("--version", help="Version number for the release")
    parser.add_argument("--schedule", action="store_true", help="Run in scheduled mode")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Check if required environment variables are set
    required_vars = ["GITHUB_TOKEN", "OPENAI_API_KEY"]
    for var in required_vars:
        if not os.environ.get(var):
            logger.error(
                f"Environment variable {var} is not set. Please set it before running the program."
            )
            sys.exit(1)

    # Run in scheduled mode or one-time mode
    if args.schedule:
        schedule_config = config.get("schedule", {})
        frequency = schedule_config.get("frequency", "daily")
        at_time = schedule_config.get("at_time", "00:00")

        logger.info(
            f"Starting scheduled mode with frequency '{frequency}' at {at_time}"
        )

        if frequency == "daily":
            schedule.every().day.at(at_time).do(run_scheduled_job, config=config)
        elif frequency == "weekly":
            day = schedule_config.get("day", "monday")
            getattr(schedule.every(), day).at(at_time).do(
                run_scheduled_job, config=config
            )

        while True:
            schedule.run_pending()
            time.sleep(60)  # Sleep for a minute
    else:
        # Run once
        success = generate_and_publish(config, args.since_days, args.version)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
