# WebSSH Architecture Documentation

## Overview

WebSSH is a web-based SSH client that allows users to connect to SSH servers through their web browser. The application acts as a bridge between HTTP/WebSocket connections from browsers and SSH connections to remote servers.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser (Client)                        │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   HTML     │  │  JavaScript  │  │   xterm.js Terminal  │   │
│  │  (forms)   │  │  (main.js)   │  │    (WebSocket)       │   │
│  └────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/HTTPS
                              │ WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Tornado Web Server                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    main.py (Entry Point)                  │  │
│  │  - Application initialization                             │  │
│  │  - Event loop management                                  │  │
│  │  - Periodic tasks (rate limit cleanup, session timeout)   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴────────────────────────────┐    │
│  │                    Request Handlers                      │    │
│  │  ┌────────────────┐  ┌──────────────┐  ┌────────────┐ │    │
│  │  │ IndexHandler   │  │ WsockHandler │  │ NotFound   │ │    │
│  │  │   (/, POST)    │  │   (/ws)      │  │  Handler   │ │    │
│  │  │                │  │              │  │            │ │    │
│  │  │ - Form handle  │  │ - WebSocket  │  │ - 404      │ │    │
│  │  │ - SSH connect  │  │ - I/O relay  │  │   errors   │ │    │
│  │  │ - Validation   │  │ - Messages   │  │            │ │    │
│  │  └────────────────┘  └──────────────┘  └────────────┘ │    │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴────────────────────────────┐    │
│  │                  Core Components                         │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │    │
│  │  │  Worker     │  │ RateLimiter │  │   Settings    │  │    │
│  │  │             │  │             │  │               │  │    │
│  │  │ - SSH I/O   │  │ - IP track  │  │ - Config      │  │    │
│  │  │ - Terminal  │  │ - Timeouts  │  │ - Options     │  │    │
│  │  │ - Lifecycle │  │ - Cleanup   │  │ - Policies    │  │    │
│  │  └─────────────┘  └─────────────┘  └───────────────┘  │    │
│  │                                                          │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │    │
│  │  │   Utils     │  │   Policy    │  │   SSHClient   │  │    │
│  │  │             │  │             │  │               │  │    │
│  │  │ - Validate  │  │ - Host keys │  │ - Custom auth │  │    │
│  │  │ - Encoding  │  │ - Verify    │  │ - 2FA support │  │    │
│  │  │ - IP parse  │  │ - AutoAdd   │  │ - Key mgmt    │  │    │
│  │  └─────────────┘  └─────────────┘  └───────────────┘  │    │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SSH Protocol (Paramiko)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SSH Server (Remote)                        │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   sshd     │  │     Shell    │  │   User Session       │   │
│  └────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Entry Point (`main.py`)

**Responsibility:** Application bootstrap and lifecycle management

**Key Functions:**
- `main()`: Entry point, initializes the application
- `make_app()`: Creates Tornado application with handlers
- `make_handlers()`: Registers URL routes and handlers
- `app_listen()`: Starts HTTP/HTTPS servers

**Periodic Tasks:**
- Rate limiter cleanup (every `ratelimit_window` seconds)
- Session timeout check (every 60 seconds)

### 2. Request Handlers (`handler.py`)

#### IndexHandler
- **Route:** `/` (GET, POST)
- **Purpose:** Serve login page and handle SSH connection requests
- **Flow:**
  1. GET: Render HTML form
  2. POST: Validate credentials → Connect SSH → Create Worker → Return worker ID

**Security Checks:**
- Rate limiting (per IP)
- Connection limits (per IP)
- Origin validation (CORS)
- Input validation

#### WsockHandler
- **Route:** `/ws` (WebSocket)
- **Purpose:** Relay terminal I/O between browser and SSH
- **Flow:**
  1. Validate worker ID
  2. Attach to Worker
  3. Relay messages bidirectionally
  4. Handle resize events

#### MixinHandler
- **Purpose:** Base class with common security logic
- **Features:**
  - Origin checking
  - IP address resolution (X-Forwarded-For support)
  - HTTPS redirect logic
  - Custom headers

### 3. Worker (`worker.py`)

**Responsibility:** Manage individual SSH session I/O

**Key Properties:**
- `ssh`: Paramiko SSH client
- `chan`: SSH channel (pty)
- `handler`: WebSocket handler reference
- `data_to_dst`: Output buffer for SSH
- `last_activity`: Timestamp for timeout tracking

**Lifecycle:**
1. Created when SSH connection succeeds
2. Registered with IOLoop for event handling
3. Relays data: Browser ↔ WebSocket ↔ Worker ↔ SSH ↔ Server
4. Cleaned up when closed (connection lost, timeout, error)

**Event Handling:**
- `on_read()`: SSH → WebSocket (server output to browser)
- `on_write()`: WebSocket → SSH (browser input to server)

### 4. Rate Limiter (`handler.py`)

**Purpose:** Prevent brute force attacks

**Mechanism:**
- Tracks connection attempts per IP with timestamps
- Enforces limit: `ratelimit` attempts per `ratelimit_window` seconds
- Automatic cleanup of expired entries
- Returns HTTP 429 when limit exceeded

**Configuration:**
- `--ratelimit`: Max attempts (default: 10)
- `--ratelimit_window`: Time window in seconds (default: 60)

### 5. Settings (`settings.py`)

**Purpose:** Configuration management using Tornado options

**Categories:**
- Network: address, port, SSL settings
- Security: policy, origin, XSRF, rate limiting
- Session: timeout, max connections, delays
- SSH: encoding, connection timeout
- UI: fonts, debugging

### 6. Security Components

#### Host Key Policy (`policy.py`)
- **AutoAddPolicy**: Thread-safe implementation
- **RejectPolicy**: Requires known hosts
- **WarningPolicy**: Logs unknown hosts but accepts

#### Origin Policy
- **same**: Exact hostname and port match
- **primary**: Primary domain match
- **custom**: Whitelist of domains
- **wildcard** (*): Any origin (debug only)

#### Error Sanitization
- Production mode: Generic error messages
- Debug mode: Detailed error information
- Prevents information leakage

## Data Flow

### Connection Establishment

```
1. User submits form (hostname, username, password/key)
   ↓
2. IndexHandler.post()
   ↓
3. Rate limit check (RateLimiter)
   ↓
4. Input validation (hostname, port, credentials)
   ↓
5. SSH connection (ThreadPoolExecutor)
   ↓
6. Create Worker (IOLoop registration)
   ↓
7. Return worker ID to browser
   ↓
8. Browser opens WebSocket to /ws?id={worker_id}
   ↓
9. WsockHandler attaches to Worker
   ↓
10. Terminal ready, bidirectional I/O active
```

### Terminal I/O Flow

```
Browser Input:
  User types → JavaScript → WebSocket → WsockHandler → Worker → SSH → Server

Server Output:
  Server → SSH → Worker → WsockHandler → WebSocket → JavaScript → xterm.js → Display
```

### Session Termination

```
Triggers:
  - User closes browser
  - Network error
  - SSH connection drops
  - Session timeout (idle > session_timeout)
  - Worker recycled (no handler attached)

Flow:
  1. Worker.close(reason)
  2. Remove from IOLoop
  3. Close WebSocket
  4. Close SSH connection
  5. Clean up from clients dict
```

## Threading Model

### Main Thread (IOLoop)
- Handles all I/O operations
- WebSocket connections
- Worker event callbacks
- Periodic tasks

### ThreadPoolExecutor
- SSH connection establishment
- Blocking operations (SSH handshake, authentication)
- Returns Worker to main thread via Future

**Concurrency:**
- Max workers: `cpu_count() * 5`
- Non-blocking I/O for established connections
- Worker callbacks run in main thread

## State Management

### Global State

```python
# Rate limiter
rate_limiter.attempts: Dict[str, List[Tuple[float, bool]]]
  # {ip: [(timestamp, success), ...]}

# Active sessions
clients: Dict[str, Dict[str, Worker]]
  # {ip: {worker_id: Worker}}
```

### Worker State

```python
worker.closed: bool           # Lifecycle flag
worker.mode: IOLoop constant  # READ or WRITE
worker.data_to_dst: List      # Output buffer
worker.last_activity: float   # For timeout tracking
worker.handler: WsockHandler  # WebSocket reference
```

## Security Layers

### Layer 1: Network
- HTTPS support
- Configurable listen addresses
- Trusted downstream proxies

### Layer 2: Application
- Rate limiting (brute force protection)
- Connection limits (resource protection)
- Origin validation (CSRF protection)
- XSRF tokens

### Layer 3: Session
- Session timeouts (idle detection)
- Worker recycling (orphaned connections)
- Host key verification

### Layer 4: Protocol
- SSH authentication (password, key, 2FA)
- Encrypted channels
- Host key policies

## Performance Considerations

### Scalability
- Async I/O (Tornado)
- Connection pooling (per IP)
- Buffer management (32 KB default)
- Periodic cleanup tasks

### Resource Limits
- Max connections per IP: `maxconn` (default: 20)
- Rate limit window: Prevents resource exhaustion
- Session timeouts: Automatic cleanup
- Buffer size: Prevents memory issues

## Error Handling

### Connection Errors
- DNS resolution failures
- Network timeouts
- Authentication failures
- Host key mismatches

### Runtime Errors
- WebSocket disconnects
- SSH channel errors
- IOLoop errors
- Resource exhaustion

### Strategy
- Try-except blocks at I/O boundaries
- Graceful degradation
- Detailed logging
- User-friendly error messages (prod mode)

## Monitoring and Logging

### Log Levels
- INFO: Connection events, lifecycle
- WARNING: Rate limits, timeouts
- ERROR: Connection failures, exceptions
- DEBUG: I/O data, detailed flow

### Metrics to Monitor
- Active connections per IP
- Rate limit violations
- Session timeouts
- Connection failures
- Worker recycling events

## Configuration Best Practices

### Production
```bash
wssh --address=0.0.0.0 \
     --port=8888 \
     --certfile=/path/to/cert.crt \
     --keyfile=/path/to/cert.key \
     --policy=reject \
     --hostfile=/etc/webssh/known_hosts \
     --origin=yourdomain.com \
     --xsrf=true \
     --ratelimit=5 \
     --session_timeout=1800 \
     --maxconn=10 \
     --log-file-prefix=/var/log/webssh.log
```

### Development
```bash
wssh --debug=true \
     --port=8888 \
     --policy=warning \
     --origin=* \
     --xsrf=false
```

## Extension Points

### Custom Handlers
Add new routes in `make_handlers()`

### Custom Policies
Subclass `paramiko.client.MissingHostKeyPolicy`

### Custom Authentication
Extend `SSHClient._auth()` method

### Custom Security
Modify `MixinHandler.check_request()`

## Dependencies

### Core
- **Tornado** (>=6.4.0): Async web framework
- **Paramiko** (>=3.4.0): SSH protocol implementation

### Frontend
- **xterm.js**: Terminal emulator
- **jQuery**: DOM manipulation
- **Bootstrap**: UI framework

## Future Improvements

1. **Multi-server support**: Connect to multiple servers simultaneously
2. **Session recording**: Record and replay terminal sessions
3. **LDAP/OAuth integration**: Enterprise authentication
4. **Audit logging**: Compliance and security auditing
5. **Cluster support**: Load balancing across multiple instances
6. **Redis session storage**: Distributed session management

## References

- [Tornado Documentation](https://www.tornadoweb.org/)
- [Paramiko Documentation](http://docs.paramiko.org/)
- [xterm.js Documentation](https://xtermjs.org/)
- [SSH Protocol RFC](https://tools.ietf.org/html/rfc4253)
