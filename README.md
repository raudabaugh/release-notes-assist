# Release Notes & Documentation Assistant

Automatically generate human-friendly release notes and documentation updates from GitHub activity using GPT-4o. Streamline your release process and keep your documentation up-to-date with minimal effort.

## Features

- **Automated Data Collection**: Collect merged PRs, commit messages, and issue updates from GitHub repositories.
- **AI-Powered Content Generation**: Use GPT-4o to transform technical change logs into human-friendly release notes and documentation suggestions.
- **Multi-Channel Publishing**: Automatically publish to GitHub Releases, Confluence, and Slack.
- **Flexible Scheduling**: Configure as a GitHub Action or run as a cron job on your own infrastructure.
- **Customizable Output**: Configure the format, content, and structure of your release notes.

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/release-notes-assist.git
   cd release-notes-assist
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment variables (see Configuration section below).

## Configuration

### Environment Variables

The application requires the following environment variables:

- `GITHUB_TOKEN`: Your GitHub personal access token with repo scope
- `OPENAI_API_KEY`: Your OpenAI API key for GPT-4o access

Optional environment variables for publishing:

- `SLACK_TOKEN`: Slack API token for posting to channels
- `CONFLUENCE_URL`: Base URL of your Confluence instance
- `CONFLUENCE_USERNAME`: Confluence username
- `CONFLUENCE_TOKEN`: Confluence API token

You can set these in a `.env` file or directly in your environment:

```bash
export GITHUB_TOKEN=your_github_token
export OPENAI_API_KEY=your_openai_api_key
```

### Configuration File

The application is configured through a JSON file located at `config/config.json`. Edit this file to customize the behavior:

```json
{
  "github": {
    "organization": "your-organization",
    "repository": "your-repository"
  },
  "output": {
    "format": "markdown",
    "doc_type": "technical"
  },
  "generate_doc_updates": true,
  "publish": {
    "enabled": true,
    "github": {
      "repo_name": "your-organization/your-repository",
      "tag_name": "vX.Y.Z",
      "name": "Release vX.Y.Z",
      "draft": false,
      "prerelease": false
    },
    "slack": {
      "channel_id": "your-slack-channel-id",
      "title": "📝 New Release Notes"
    },
    "confluence": {
      "space_key": "your-confluence-space-key",
      "parent_page_id": "your-parent-page-id",
      "title": "Release Notes"
    }
  },
  "schedule": {
    "frequency": "weekly",
    "day": "friday",
    "at_time": "15:00",
    "look_back_days": 7
  }
}
```

## Usage

### Running Manually

Generate release notes for the past 7 days:

```bash
python -m src.main
```

Customize the time period and version:

```bash
python -m src.main --since-days 14 --version "v1.2.3"
```

Specify a different configuration file:

```bash
python -m src.main --config path/to/your/config.json
```

### Running as a Scheduled Job

Run the assistant in scheduled mode, which will execute according to the schedule in your config.json:

```bash
python -m src.main --schedule
```

### GitHub Actions Workflow

This project includes a GitHub Actions workflow file that can automatically generate release notes on a schedule or when manually triggered. To use it:

1. Push this repository to your GitHub account
2. Set up the required secrets in your GitHub repository settings
3. Enable the workflow in the Actions tab

You can also manually trigger the workflow from the Actions tab, specifying custom parameters like the number of days to look back and the version number.

## Demo

To demonstrate the tool with a sample sprint cycle:

1. Configure the tool to monitor a specific repository
2. Run the command to generate release notes for the past 7 days:
   ```bash
   python -m src.main --since-days 7
   ```
3. Review the generated release notes in the `output` directory
4. Adjust configuration as needed and rerun

## Example Output

The generated release notes are saved to the `output` directory, formatted as specified in your configuration (markdown by default). They typically include:

- Summary of changes
- New features
- Bug fixes
- Documentation updates
- Other changes

Each section includes links to the relevant PRs, issues, and commits.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.