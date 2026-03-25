# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Security Features
- **Rate Limiting**: Implemented IP-based rate limiting to prevent brute force attacks
  - Configurable via `--ratelimit` (default: 10 attempts)
  - Time window configurable via `--ratelimit_window` (default: 60 seconds)
  - Automatic cleanup of expired rate limit entries
  - Returns HTTP 429 when limit exceeded
  - Record both successful and failed connection attempts

- **Session Timeout**: Added automatic timeout for idle sessions
  - Configurable via `--session_timeout` (default: 1800 seconds = 30 minutes)
  - Set to 0 to disable timeout
  - Tracks last activity timestamp on all I/O operations
  - Periodic checks every 60 seconds for timed-out sessions
  - Gracefully closes idle connections

- **Error Message Sanitization**: Production mode now sanitizes error messages
  - Generic error messages in production to prevent information disclosure
  - Detailed error messages still available in debug mode
  - Categories: authentication, connection, host key verification
  - Prevents stack trace exposure to end users

#### Type Safety
- **Type Hints**: Added comprehensive type hints throughout codebase
  - All functions in `main.py` fully typed
  - All functions and methods in `worker.py` fully typed
  - Using Python 3.8+ typing module: `Dict`, `Optional`, `Tuple`, `List`
  - Improves IDE autocomplete and static analysis
  - Better code documentation through types

#### Testing
- **Integration Tests**: Added comprehensive integration test suite in `test_integration.py`
  - `TestRateLimiting`: Rate limit enforcement and cleanup
  - `TestSessionTimeout`: Worker activity tracking
  - `TestConnectionLimits`: Max connections per client
  - `TestErrorHandling`: Error sanitization for prod/debug modes
  - `TestApplicationEndpoints`: Basic endpoint functionality
  - `TestWorkerManagement`: Worker lifecycle and cleanup
  - `TestBinaryDataHandling`: Binary data handling validation
  - Uses Tornado's AsyncHTTPTestCase for async testing
  - Proper setup/teardown for test isolation

#### Documentation
- **Architecture Documentation**: Added comprehensive `ARCHITECTURE.md`
  - System architecture diagram and component details
  - Data flow diagrams for connection and I/O
  - Threading model explanation
  - State management documentation
  - Security layers overview
  - Performance considerations
  - Configuration best practices
  - Extension points for customization

- **Contributing Guidelines**: Added detailed `CONTRIBUTING.md`
  - Code of conduct
  - Development setup instructions
  - Coding standards and style guide
  - Testing guidelines
  - Pull request process
  - Bug reporting template
  - Feature request template
  - Code review guidelines

### Changed

#### Dependencies
- **Updated Paramiko**: `3.0.0` → `>=3.4.0` for security fixes and improvements
- **Updated Tornado**: `6.2.0` → `>=6.4.0` for security fixes and improvements

#### Configuration
- **Default Port**: Changed from `88` to `8888`
  - Prevents conflicts with Kerberos (port 88)
  - More standard for web applications
  - Less likely to require special permissions

#### Code Quality
- **Removed Python 2 Compatibility**: Cleaned up legacy code
  - Removed `try/except ImportError` blocks for Python 2 fallbacks
  - Direct imports of `urllib.parse.urlparse`
  - Direct imports of `json.decoder.JSONDecodeError`
  - Removed `UnicodeType` compatibility, using `str` directly
  - Removed all `u''` string prefixes (unnecessary in Python 3)
  - Code is cleaner and more maintainable

#### Error Messages
- **Improved User-Facing Error Messages**: Made errors more helpful and actionable
  - Authentication errors: Clear explanation of what went wrong
  - Connection errors: Specific guidance on troubleshooting
  - Validation errors: Explicit requirements and examples
  - Configuration errors: Detailed path information and suggestions
  - Private key errors: Format requirements and passphrase hints
  - All error messages now include actionable guidance

#### Docker
- **Updated Dockerfile Labels**: 
  - Maintainer: Now shows actual author information
  - Version: Updated from placeholder to `1.6.2`

### Fixed

- **Binary Data Handling**: Fixed potential crash in `worker.py`
  - `on_write()` now correctly handles both string and binary data
  - Intelligently detects data type before joining
  - Uses `b''.join()` for bytes and `''.join()` for strings
  - Prevents TypeError when terminal sends binary data

- **UnicodeType Reference**: Fixed remaining Python 2 compatibility issue
  - Replaced `UnicodeType` with `str` in WebSocket message handler
  - Resolves NameError that occurred during WebSocket connections

### Security

- **Rate Limiting Protection**: Mitigates brute force attacks
  - Tracks connection attempts per IP address
  - Configurable limits and time windows
  - Automatic cleanup prevents memory exhaustion

- **Session Management**: Improved security posture
  - Automatic timeout of idle sessions
  - Prevents abandoned session accumulation
  - Reduces attack surface

- **Information Disclosure Prevention**: 
  - Production mode hides sensitive error details
  - Stack traces not exposed to end users
  - Generic error messages prevent reconnaissance

## [1.6.2] - 2024-03-09

### Project State Before Improvements

#### Features
- SSH password authentication
- SSH public-key authentication (DSA, RSA, ECDSA, Ed25519)
- Encrypted key support
- Two-Factor Authentication (TOTP)
- Fullscreen terminal
- Terminal window resizing
- Auto-detect SSH server encoding
- Modern browser support (Chrome, Firefox, Safari, Edge, Opera)

#### Configuration Options
- Listen address and port
- SSL/HTTPS support
- Host key policies (reject, autoadd, warning)
- Origin policies (same, primary, custom, wildcard)
- WebSocket ping interval
- SSH connection timeout
- Maximum connections per client
- Custom fonts
- Character encoding override

#### Known Issues (Addressed in Unreleased)
- Outdated dependencies (paramiko 3.0.0, tornado 6.2.0)
- No rate limiting (vulnerable to brute force)
- Unusual default port (88 instead of 8888)
- Python 2 compatibility code remnants
- Verbose error messages in production
- No session timeout mechanism
- Binary data handling bug in worker
- Missing type hints
- Placeholder Docker labels
- Limited integration tests
- Basic error messages
- No architecture documentation
- No contributing guidelines

## Version History

- **[Unreleased]**: Current development version with all improvements
- **[1.6.2]**: Previous stable release (baseline for improvements)

## Migration Guide

### Upgrading to Unreleased Version

#### Breaking Changes
None. All changes are backward compatible.

#### New Configuration Options

```bash
# Rate limiting (recommended for production)
wssh --ratelimit=10              # Max attempts per IP (default: 10)
wssh --ratelimit_window=60       # Time window in seconds (default: 60)

# Session timeout (recommended for production)
wssh --session_timeout=1800      # Idle timeout in seconds (default: 1800)
                                 # Set to 0 to disable

# Port change (automatic)
# Old: Default port was 88
# New: Default port is 8888
# No action needed unless you explicitly set --port=88
```

#### Updated Dependencies

```bash
# Update your environment
pip install --upgrade paramiko tornado

# Or reinstall from requirements.txt
pip install -r requirements.txt --upgrade
```

#### Testing Your Upgrade

```bash
# Run the test suite
python -m pytest tests/ -v

# Run integration tests specifically
python -m pytest tests/test_integration.py -v

# Start the application
python run.py
```

#### Production Recommendations

```bash
# Recommended production configuration
wssh \
  --address=0.0.0.0 \
  --port=8888 \
  --certfile=/path/to/cert.crt \
  --keyfile=/path/to/cert.key \
  --policy=reject \
  --hostfile=/etc/webssh/known_hosts \
  --origin=yourdomain.com \
  --xsrf=true \
  --ratelimit=5 \
  --ratelimit_window=60 \
  --session_timeout=1800 \
  --maxconn=10 \
  --log-file-prefix=/var/log/webssh.log
```

## Acknowledgments

### Contributors
- Original author: Shengdun Hua
- Security improvements and modernization: Various contributors

### Dependencies
- [Tornado](https://www.tornadoweb.org/) - Async web framework
- [Paramiko](http://docs.paramiko.org/) - SSH protocol implementation
- [xterm.js](https://xtermjs.org/) - Terminal emulator

## Future Roadmap

### Planned Features
- [ ] Multi-server support (simultaneous connections)
- [ ] Session recording and playback
- [ ] LDAP/OAuth integration
- [ ] Audit logging for compliance
- [ ] Cluster support with load balancing
- [ ] Redis session storage for distributed deployments
- [ ] File transfer support (SFTP)
- [ ] Terminal themes and customization
- [ ] Connection history and favorites

### Under Consideration
- [ ] Web-based SFTP client interface
- [ ] SSH tunnel management
- [ ] Keyboard shortcuts customization
- [ ] Mobile device optimization
- [ ] Container orchestration support

## Support

### Getting Help
- **Documentation**: See README.md and ARCHITECTURE.md
- **Issues**: [GitHub Issues](https://github.com/huashengdun/webssh/issues)
- **Discussions**: [GitHub Discussions](https://github.com/huashengdun/webssh/discussions)

### Reporting Issues
- Security issues: Report privately to maintainers
- Bug reports: Use GitHub Issues with bug template
- Feature requests: Use GitHub Issues with feature template

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: This changelog documents significant improvements made to enhance security, code quality, and maintainability of the WebSSH project. All changes maintain backward compatibility while providing substantial improvements to the security posture and developer experience.
