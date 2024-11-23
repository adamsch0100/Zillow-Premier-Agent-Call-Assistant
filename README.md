# Real Estate Call Assistant

An AI-powered real-time assistant for real estate agents handling Zillow lead calls. The system provides instant script suggestions and objection handlers during live calls.

## Features

- Real-time call transcription
- Smart response suggestions
- Objection handling assistance
- Call sentiment analysis
- Performance tracking

## Getting Started

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
```

### Development Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/real-estate-assistant.git
cd real-estate-assistant
```

2. Set up virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Start the development server
```bash
python src/backend/app/main.py
```

5. In a new terminal, start the frontend
```bash
cd src/frontend
npm install
npm start
```

## Project Structure

```
real-estate-assistant/
├── docs/                 # Documentation
├── src/                  # Source code
│   ├── frontend/        # Frontend React application
│   └── backend/         # Backend Python application
└── tests/               # Test suites
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.