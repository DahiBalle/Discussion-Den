# Discussion Den

A modern, Reddit-inspired discussion platform built with Flask, designed for hackathons, demos, and college-level projects. Features a clean dark theme, persona system, and comprehensive community management.

![Discussion Den](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.0-lightgrey)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Required-blue)

## 🚀 Features

### Core Features
- **User Authentication**: Email/password registration and login
- **Google OAuth**: Optional Google Sign-In integration
- **Communities**: Create and manage discussion communities (like subreddits)
- **Posts**: Create text posts with optional images
- **Comments**: Nested comment system with 3-level depth
- **Voting System**: Reddit-style upvote/downvote functionality
- **Save Posts**: Bookmark posts for later viewing
- **Search**: Full-text search across posts, communities, and users

### Advanced Features
- **Persona System**: Users can create multiple personas/identities
- **Identity Switching**: Switch between user and persona identities
- **Post Management**: Edit and delete your own posts
- **Comment Management**: Edit and delete your own comments
- **Rate Limiting**: API protection against spam and abuse
- **Responsive Design**: Mobile-friendly Bootstrap 5 interface

### Security Features
- **CSRF Protection**: All forms protected against CSRF attacks
- **Input Validation**: Comprehensive server-side validation
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **XSS Protection**: Template escaping prevents cross-site scripting
- **Rate Limiting**: API endpoints protected against abuse
- **Secure Sessions**: Flask-Login session management

## 🛠️ Tech Stack

### Backend
- **Python 3.8+**
- **Flask 3.0.0** - Web framework
- **SQLAlchemy** - ORM and database management
- **PostgreSQL** - Primary database (required)
- **Flask-Login** - User session management
- **Flask-WTF** - Form handling and CSRF protection
- **Authlib** - Google OAuth integration
- **Flask-Limiter** - Rate limiting

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Custom styling with CSS variables
- **Bootstrap 5.3.0** - Responsive framework
- **Vanilla JavaScript** - Minimal client-side scripting
- **Font Awesome** - Icons

### Architecture
- **Application Factory Pattern** - Clean, testable Flask app structure
- **Blueprint-based Routing** - Modular route organization
- **3-Tier Architecture** - Separation of presentation, business, and data layers

## 📁 Project Structure

```
Discussion-Den/
├── app.py                 # Application factory and CLI commands
├── models.py              # SQLAlchemy database models
├── forms.py               # WTForms form definitions
├── extensions.py          # Flask extensions initialization
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── routes/               # Blueprint modules
│   ├── auth.py          # Authentication routes
│   ├── feed.py          # Main feed display
│   ├── post.py          # Post creation and management
│   ├── comment.py       # Comment handling
│   ├── community.py     # Community management
│   ├── profile.py       # User profiles
│   ├── persona.py       # Persona management
│   ├── search.py        # Search functionality
│   ├── api.py           # REST API endpoints
│   └── utils.py         # Shared utilities
├── templates/           # Jinja2 templates
│   ├── base.html        # Base layout template
│   ├── feed.html        # Main feed page
│   ├── post_detail.html # Post detail page
│   ├── edit_post.html   # Post editing form
│   ├── auth/            # Authentication templates
│   ├── search/          # Search results templates
│   └── includes/        # Reusable template components
├── static/
│   ├── css/style.css    # Main stylesheet (1300+ lines)
│   └── js/              # Client-side JavaScript
└── Documentation/       # Setup and security guides
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- PostgreSQL database
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Discussion-Den
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and configure:
   - `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET`: Optional Google OAuth credentials

5. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb discussion_den
   
   # Initialize database tables
   python -c "from app import create_app; from extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

6. **Run the application**
   ```bash
   python -m flask run
   ```

Visit `http://localhost:5000` to access Discussion Den!

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask secret key for sessions and CSRF |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `FLASK_ENV` | No | Environment (development/production) |
| `FLASK_DEBUG` | No | Enable debug mode (True/False) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | OAuth callback URL |

### Database Configuration

Discussion Den requires PostgreSQL. Example connection strings:

```bash
# Local development
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/discussion_den

# Production (with connection pooling)
DATABASE_URL=postgresql+psycopg2://username:password@host:5432/database?sslmode=require
```

### Google OAuth Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Identity API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URIs:
   - Development: `http://localhost:5000/auth/google/callback`
   - Production: `https://yourdomain.com/auth/google/callback`
6. Copy Client ID and Client Secret to your `.env` file

## 🎨 UI/UX Design

### Design System
- **Modern Dark Theme**: Reddit-inspired color palette
- **Responsive Layout**: Mobile-first Bootstrap 5 design
- **Typography**: System font stack for optimal readability
- **Color Palette**:
  - Primary: `#0b1416` (dark background)
  - Accent: `#ff4500` (Reddit orange)
  - User Badge: `#4fbcff` (blue)
  - Persona Badge: `#7c3aed` (purple)

### Layout Structure
- **Navigation Bar**: Sticky header with search, user menu, persona switcher
- **Three-Column Layout**: Offcanvas sidebar, main content, right panel
- **Responsive Breakpoints**: Adapts to desktop, tablet, and mobile screens

### Key Components
- **Post Cards**: Clean, card-based post display
- **Comment Threading**: Visual indentation for nested comments
- **Action Buttons**: Vote, save, edit, delete functionality
- **Identity Badges**: Visual distinction between users and personas

## 🔒 Security

### Implemented Security Measures
- **CSRF Protection**: All forms protected with CSRF tokens
- **Password Hashing**: Werkzeug secure password hashing
- **Input Validation**: Server-side validation with WTForms
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **XSS Protection**: Jinja2 template escaping
- **Rate Limiting**: API endpoints protected against abuse
- **Session Security**: Secure cookie configuration

### Security Best Practices
- Never commit `.env` files to version control
- Use strong, unique secret keys for each environment
- Enable HTTPS in production
- Regularly update dependencies
- Monitor for security vulnerabilities

## 📊 Database Schema

### Core Models
- **User**: User accounts with authentication
- **Persona**: Alternative identities for users
- **Community**: Discussion communities (like subreddits)
- **Post**: User-generated posts with voting
- **Comment**: Nested comments on posts
- **Vote**: User votes on posts
- **SavedPost**: User bookmarks

### Key Relationships
- Users can have multiple Personas
- Posts belong to Communities
- Comments can have parent Comments (nested)
- Votes and SavedPosts link to either Users or Personas

## 🚀 Deployment

### Production Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Set `FLASK_DEBUG=False`
- [ ] Use strong, unique `SECRET_KEY`
- [ ] Configure production database
- [ ] Enable HTTPS
- [ ] Set up proper logging
- [ ] Configure reverse proxy (nginx)
- [ ] Set up database backups
- [ ] Monitor application performance

### Deployment Options
- **Heroku**: Easy deployment with PostgreSQL add-on
- **DigitalOcean App Platform**: Simple container deployment
- **AWS/GCP**: Full control with EC2/Compute Engine
- **Docker**: Containerized deployment

## 🧪 Testing

### Manual Testing Checklist
- [ ] User registration and login
- [ ] Google OAuth login (if configured)
- [ ] Post creation and editing
- [ ] Comment creation and nesting
- [ ] Voting functionality
- [ ] Save/unsave posts
- [ ] Community creation
- [ ] Persona creation and switching
- [ ] Search functionality
- [ ] Mobile responsiveness

### API Testing
Test API endpoints with tools like Postman or curl:
```bash
# Test voting
curl -X POST http://localhost:5000/api/post/1/vote \
  -H "Content-Type: application/json" \
  -d '{"vote": 1}'

# Test search
curl "http://localhost:5000/search?q=python&type=posts"
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for complex functions
- Keep functions focused and small
- Write defensive code with error handling

## 📈 Performance

### Optimization Features
- **Eager Loading**: Prevents N+1 query problems
- **Pagination**: Limits memory usage with page limits
- **Database Indexes**: Optimized queries on frequently accessed fields
- **Rate Limiting**: Prevents API abuse and server overload

### Performance Metrics
- **Page Load Time**: Sub-second for typical queries
- **Database Queries**: Optimized with eager loading
- **Memory Usage**: Controlled with pagination limits
- **API Response Time**: Fast JSON responses

## 🐛 Troubleshooting

### Common Issues

**Database Connection Errors**
- Check PostgreSQL is running
- Verify `DATABASE_URL` in `.env`
- Ensure database exists

**Google OAuth Errors**
- Check client ID and secret are correct
- Verify redirect URI matches Google Console
- Ensure Google Identity API is enabled

**Import Errors**
- Activate virtual environment
- Install requirements: `pip install -r requirements.txt`
- Check Python version (3.8+ required)

**CSS/JS Not Loading**
- Check static file paths
- Clear browser cache
- Verify Flask static folder configuration

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Reddit**: UI/UX inspiration
- **Flask Community**: Excellent documentation and examples
- **Bootstrap Team**: Responsive framework
- **Font Awesome**: Beautiful icons

## 📞 Support

For questions, issues, or contributions:
- Create an issue on GitHub
- Check existing documentation
- Review the troubleshooting section

---

**Discussion Den** - Built with ❤️ for the developer community