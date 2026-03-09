# Contributing to WebSSH

Thank you for your interest in contributing to WebSSH! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)
- [Code Review Process](#code-review-process)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background or identity.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what's best for the community
- Showing empathy towards others

**Unacceptable behavior includes:**
- Harassment, insults, or derogatory comments
- Publishing others' private information
- Trolling or deliberately disruptive behavior
- Other conduct inappropriate in a professional setting

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic knowledge of SSH protocol
- Familiarity with Tornado web framework
- Understanding of async/await patterns

### Development Tools

We recommend:
- **IDE**: VSCode, PyCharm, or similar
- **Linter**: pylint or flake8
- **Formatter**: black or autopep8
- **Type Checker**: mypy

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/webssh.git
cd webssh
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Unix/macOS:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-tornado
```

### 4. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=webssh --cov-report=html
```

### 5. Start Development Server

```bash
# Run with debug mode
python run.py --debug=true --port=8888
```

## How to Contribute

### Types of Contributions

1. **Bug Fixes**: Fix issues in existing code
2. **Features**: Add new functionality
3. **Documentation**: Improve or add documentation
4. **Tests**: Add or improve test coverage
5. **Performance**: Optimize existing code
6. **Security**: Enhance security measures

### Workflow

1. **Check existing issues**: Look for related issues or discussions
2. **Create an issue**: Describe what you want to do
3. **Get feedback**: Wait for maintainer response
4. **Create a branch**: Use descriptive branch names
5. **Make changes**: Follow coding standards
6. **Test thoroughly**: Add/update tests
7. **Submit PR**: Follow PR template
8. **Address feedback**: Respond to review comments

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

#### Formatting

```python
# Line length: 100 characters max
# Indentation: 4 spaces (no tabs)
# Imports: grouped and sorted

# Good
def connect_ssh(hostname: str, port: int, username: str) -> Worker:
    """Connect to SSH server and return worker."""
    pass

# Bad
def connect_ssh(hostname,port,username):
    pass
```

#### Naming Conventions

```python
# Classes: PascalCase
class SSHClient:
    pass

# Functions/methods: snake_case
def get_client_addr():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_CONNECTIONS = 20
BUF_SIZE = 32 * 1024

# Private: leading underscore
def _internal_method():
    pass
```

#### Type Hints

Always use type hints for new code:

```python
from typing import Dict, Optional, Tuple, List

def process_data(
    data: bytes, 
    encoding: str = 'utf-8'
) -> Optional[str]:
    """Process binary data and return string."""
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        return None
```

#### Docstrings

Use Google-style docstrings:

```python
def make_connection(hostname: str, port: int) -> bool:
    """Establish connection to remote host.
    
    Args:
        hostname: The hostname or IP address to connect to.
        port: The port number (1-65535).
    
    Returns:
        True if connection successful, False otherwise.
    
    Raises:
        ValueError: If port is invalid.
        ConnectionError: If connection fails.
    
    Example:
        >>> make_connection('example.com', 22)
        True
    """
    pass
```

### Code Organization

#### File Structure

```
webssh/
├── __init__.py          # Package initialization
├── _version.py          # Version information
├── main.py              # Entry point
├── handler.py           # HTTP/WebSocket handlers
├── worker.py            # SSH session workers
├── settings.py          # Configuration
├── policy.py            # Host key policies
├── utils.py             # Utility functions
├── static/              # Frontend assets
└── templates/           # HTML templates
```

#### Import Order

1. Standard library
2. Third-party packages
3. Local modules

```python
# Standard library
import logging
import time
from typing import Dict, Optional

# Third-party
import tornado.web
import paramiko

# Local
from webssh.utils import is_valid_hostname
from webssh.worker import Worker
```

### Error Handling

```python
# Good: Specific exceptions
try:
    result = dangerous_operation()
except ValueError as e:
    logging.error(f"Invalid value: {e}")
    raise
except ConnectionError as e:
    logging.error(f"Connection failed: {e}")
    return None

# Bad: Bare except
try:
    result = dangerous_operation()
except:
    pass
```

### Logging

```python
# Use appropriate log levels
logging.debug('Detailed information for debugging')
logging.info('General information about program flow')
logging.warning('Warning about potential issues')
logging.error('Error that needs attention')

# Include context
logging.info('Connection established to {}:{}'.format(host, port))
logging.error('Authentication failed for user: {}'.format(username))
```

## Testing

### Test Structure

```
tests/
├── __init__.py
├── test_handler.py      # Handler tests
├── test_worker.py       # Worker tests
├── test_utils.py        # Utility tests
├── test_integration.py  # Integration tests
└── data/                # Test fixtures
```

### Writing Tests

```python
import unittest
from unittest.mock import Mock, patch

class TestWorker(unittest.TestCase):
    """Test Worker class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.mock_chan = Mock()
    
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    def test_worker_creation(self):
        """Test that worker is created correctly."""
        worker = Worker(loop, self.mock_ssh, self.mock_chan, ('localhost', 22))
        self.assertIsNotNone(worker.id)
        self.assertFalse(worker.closed)
    
    def test_worker_close(self):
        """Test that worker closes properly."""
        worker = Worker(loop, self.mock_ssh, self.mock_chan, ('localhost', 22))
        worker.close(reason='test')
        self.assertTrue(worker.closed)
```

### Test Coverage

- Aim for at least 80% code coverage
- Test edge cases and error conditions
- Test both success and failure paths
- Include integration tests for critical flows

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_worker.py -v

# Run with coverage
pytest tests/ --cov=webssh --cov-report=html

# Run only integration tests
pytest tests/test_integration.py -v

# Run tests matching pattern
pytest -k "test_rate_limit" -v
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Type hints added for new functions
- [ ] Docstrings added/updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No linting errors
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### PR Title Format

Use conventional commit format:

```
feat: Add session recording feature
fix: Resolve memory leak in worker cleanup
docs: Update architecture documentation
test: Add integration tests for rate limiting
refactor: Simplify error handling in handler
perf: Optimize buffer management
security: Fix XSS vulnerability in error messages
```

### PR Description Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested the changes.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No new warnings

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks**: CI/CD must pass
2. **Code review**: At least one maintainer approval
3. **Testing**: Reviewers may request additional tests
4. **Documentation**: Ensure docs are updated
5. **Merge**: Maintainer will merge when approved

## Reporting Bugs

### Before Reporting

1. Check existing issues
2. Update to latest version
3. Reproduce the issue
4. Collect relevant information

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the issue.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g. Windows 10, Ubuntu 20.04]
- Python version: [e.g. 3.10.5]
- WebSSH version: [e.g. 1.6.2]
- Browser: [e.g. Chrome 100]

**Additional context**
Any other relevant information.

**Logs**
```
Paste relevant logs here
```
```

## Suggesting Enhancements

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Clear description of the problem.

**Describe the solution you'd like**
Clear description of desired feature.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Additional context**
Mockups, examples, or references.
```

### Enhancement Guidelines

- Align with project goals
- Consider security implications
- Maintain backward compatibility
- Include use cases
- Estimate implementation effort

## Code Review Process

### For Contributors

- Be patient and respectful
- Respond to feedback promptly
- Ask questions if unclear
- Update PR based on feedback
- Keep PR scope focused

### For Reviewers

- Be constructive and respectful
- Explain reasoning for feedback
- Distinguish between required and optional changes
- Approve when satisfied
- Thank contributors

## Security Issues

**Do not report security issues publicly.**

Instead:
1. Email security concerns to: [maintainer email]
2. Include detailed description
3. Wait for acknowledgment
4. Coordinate disclosure timeline

## Getting Help

- **Documentation**: Read the docs first
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions
- **Chat**: Join community chat (if available)

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Acknowledged in project documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to ask questions by:
- Opening an issue with the "question" label
- Starting a discussion on GitHub
- Reaching out to maintainers

Thank you for contributing to WebSSH! 🎉
