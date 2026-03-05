# Qualtrics Generative Survey

A locally-hosted web app that uses Claude AI to convert natural-language survey questions into Qualtrics API payloads and submit them directly to your survey. Built with Flask.

## Features

- **AI-Powered Question Generation** -- Describe your question in plain English and Claude generates the correct Qualtrics API JSON
- **Batch Support** -- Parse and submit multiple questions at once (separate with `---`)
- **Survey Overview** -- Browse your survey's blocks and questions in a tree view
- **Block Management** -- Create, delete, and reorder blocks
- **Question Management** -- Reorder questions, move between blocks, rename internal variable names, toggle force response, and delete
- **JavaScript Editor** -- View, edit, and AI-generate custom Qualtrics question JavaScript
- **Supported Question Types** -- Multiple Choice (MC), Text Entry (TE), Descriptive Text (DB), Slider, and more

## Prerequisites

- Python 3.8+
- A [Qualtrics](https://www.qualtrics.com/) account with API access
- An [Anthropic](https://console.anthropic.com/) API key

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/renjiet/qualtrics-generative-survey.git
   cd qualtrics-generative-survey
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**

   ```bash
   python app.py
   ```

5. **Open in your browser**

   Navigate to [http://localhost:5000](http://localhost:5000)

## Configuration

All credentials are entered in the browser and stored in `localStorage` -- nothing is saved on the server.

You'll need:

| Credential | Where to find it |
|---|---|
| **Qualtrics API Token** | Qualtrics > Account Settings > Qualtrics IDs |
| **Data Center** | Select from the dropdown (e.g., `syd1` for Sydney AU) |
| **Survey ID** | Qualtrics > Account Settings > Qualtrics IDs (starts with `SV_`) |
| **Anthropic API Key** | [console.anthropic.com](https://console.anthropic.com/) > API Keys |

## Usage

1. **Connect** -- Enter your credentials and click "Connect" to load your survey
2. **Select a block** -- Choose a target block from the dropdown or create a new one
3. **Write your questions** -- Describe them in natural language in the textarea, e.g.:

   ```
   Q1. What is your gender?
   - Male
   - Female
   - Non-binary
   - Prefer not to say
   ---
   Q2. What is your age? (text entry, single line)
   ---
   Q3. On a scale of 1-10, how satisfied are you? (slider)
   ```

4. **Parse** -- Click "Parse with Claude" to generate JSON payloads
5. **Review & Submit** -- Edit the JSON if needed, then submit individually or all at once

## Project Structure

```
qualtrics-generative-survey/
  app.py                       # Flask backend (routes + Qualtrics/Claude API logic)
  templates/
    index.html                 # Single-page frontend
  requirements.txt             # Python dependencies
  QUALTRICS_API_REFERENCE.md   # API reference documentation
```

## License

MIT
