# Soulify (EmpathAI)

Soulify is an AI-powered mental wellness platform that provides empathetic conversation, mood tracking, journaling, and interactive activities to support mental health.

## Features

- **AI Empathetic Conversation**: Chat with an AI assistant trained to provide supportive and empathetic responses
- **Journal**: Document your thoughts, feelings, and experiences with mood tracking
- **Facial Emotion Detection**: Analyze facial expressions to help identify emotions
- **Interactive Activities**: Engage with games and exercises designed to improve mental wellness
- **User Authentication**: Secure login and signup to keep your data private

## Getting Started

### Prerequisites

- Python 3.8+
- Flask
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/soulify.git
   cd soulify
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   FLASK_SECRET_KEY=your_random_secret_key
   ```

4. Initialize the database:
   ```
   flask shell
   ```
   Then in the Flask shell:
   ```python
   from EmpathAI import db
   db.create_all()
   exit()
   ```

5. Run the application:
   ```
   python EmpathAI.py
   ```

## Project Structure

- `EmpathAI.py`: Main application file with Flask routes and API definitions
- `static/`: CSS, JavaScript, and other static assets
- `templates/`: HTML templates for the web interface
- `instance/`: Contains the SQLite database (created at runtime)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `FLASK_SECRET_KEY` | Secret key for Flask sessions |
| `PRODUCTION` | Set to 'true' for production mode |
| `PORT` | Port to run the application on (default: 5000) |
| `SERVER_NAME` | Server hostname (production mode) |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for providing the GPT models
- Flask and SQLAlchemy for the web framework 