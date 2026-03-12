# Configuration Management - Eliminate Hardcoded Values

## Task Overview

**Priority**: Tier 2 (Code Quality & Maintainability)  
**Status**: Configuration scattered, hardcoded values throughout  
**Estimated Effort**: Medium (centralized configuration system)  
**Breaking Changes**: Minimal (backward compatible with environment variables)  

## Current State Analysis

### What Exists ✓
- ✅ Environment variable support (MAGNETDB_API_SERVER, MAGNETDB_API_KEY)
- ✅ CLI arguments for server/port/key
- ✅ Basic configuration passing through function arguments

### What's Missing ❌
- ❌ **No centralized config** - Configuration scattered across modules
- ❌ **No config files** - Can't use config.yaml or .env files
- ❌ **No validation** - Invalid config values cause runtime errors
- ❌ **No defaults management** - Defaults hardcoded in multiple places
- ❌ **No configuration documentation** - Users don't know what's configurable
- ❌ **No config precedence** - Unclear which source takes priority
- ❌ **No type safety** - Config values are stringly-typed
- ❌ **Hardcoded timeouts** - Network timeouts hardcoded in code
- ❌ **Hardcoded paths** - File paths and URLs hardcoded
- ❌ **No profile support** - Can't switch between dev/staging/prod configs

### Current Configuration Approach

**Problems identified:**
```python
# In CLI and various modules - configuration scattered everywhere:
# 1. Hardcoded defaults in multiple places
server = os.getenv("MAGNETDB_API_SERVER", "magnetdb.example.com")  # Default repeated
port = int(os.getenv("MAGNETDB_API_PORT", "443"))  # Conversion scattered
timeout = 30  # Hardcoded in various places

# 2. No validation
api_key = os.getenv("MAGNETDB_API_KEY")  # Could be None, causes runtime error later

# 3. Configuration passed through 10+ function parameters
def create_magnet(session, web, headers, api_key, timeout, debug, ...):
    # Too many parameters!
    pass

# 4. Inconsistent configuration access
# Some modules use env vars, some use passed parameters, some have defaults

# 5. Hardcoded values throughout
verify_ssl = True  # Hardcoded - can't disable for development
retry_attempts = 3  # Hardcoded - can't configure
chunk_size = 8192  # Hardcoded in attachment.py
```

### Configuration Scattered Across Files

- `cli.py`: CLI argument defaults, environment variable access
- `utils.py`: Function defaults for timeouts, debug flags
- `attachment.py`: Hardcoded chunk sizes, file paths
- `hoop_stress.py`: Hardcoded computation parameters
- `flow_params.py`: Hardcoded sampling parameters
- Each module: Repeated environment variable access

---

## Implementation Plan

### Design Goals

1. **Single source of truth** - One config class, all modules use it
2. **Layered configuration** - Defaults < Config file < Environment vars < CLI args
3. **Type-safe config** - Use dataclasses with type hints
4. **Validated config** - Catch invalid values early
5. **Backward compatible** - Existing env vars continue to work
6. **Well documented** - Each config option documented
7. **Environment profiles** - Support dev/staging/prod profiles
8. **Security-aware** - Protect sensitive values (API keys, passwords)

### Configuration Precedence (lowest to highest)

```
1. Hardcoded defaults (in Config class)
2. System config file (/etc/magnetdb/config.yaml)
3. User config file (~/.config/magnetdb/config.yaml)
4. Project config file (./magnetdb.yaml or .magnetdb)
5. Environment variables (MAGNETDB_*)
6. Command-line arguments (--server, --api-key, etc.)
```

### Target Architecture

```
python_magnetapi/
├── config.py                      # NEW: Core configuration module
│   ├── Config (main config class)
│   ├── APIConfig (API settings)
│   ├── ComputationConfig (computation settings)
│   ├── FileConfig (file/path settings)
│   ├── LoggingConfig (logging settings)
│   └── load_config() (config loader)
├── config_schema.yaml             # NEW: Config schema/documentation
├── magnetdb.yaml.example          # NEW: Example config file
└── (existing modules updated to use Config)
```

---

## Phase 1: Core Configuration Infrastructure

### Step 1.1: Create Configuration Classes

Create `python_magnetapi/config.py`:

```python
"""Centralized configuration management for python_magnetapi.

Configuration precedence (lowest to highest):
1. Hardcoded defaults
2. System config file (/etc/magnetdb/config.yaml)
3. User config file (~/.config/magnetdb/config.yaml)
4. Project config file (./magnetdb.yaml or .magnetdb)
5. Environment variables (MAGNETDB_*)
6. Command-line arguments (passed to load_config)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
from urllib.parse import urlparse


# ============================================================================
# Configuration Dataclasses
# ============================================================================

@dataclass
class APIConfig:
    """API connection configuration."""
    
    # Connection settings
    server: str = "magnetdb.lncmi.cnrs.fr"
    port: int = 443
    api_key: Optional[str] = None
    base_path: str = "/api"
    
    # Network settings
    timeout: int = 30
    verify_ssl: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Request settings
    max_concurrent: int = 10
    rate_limit: Optional[int] = None  # requests per second
    
    def __post_init__(self):
        """Validate configuration."""
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}. Must be 1-65535")
        
        if self.timeout < 0:
            raise ValueError(f"Invalid timeout: {self.timeout}. Must be >= 0")
        
        if self.retry_attempts < 0:
            raise ValueError(f"Invalid retry_attempts: {self.retry_attempts}")
    
    @property
    def web(self) -> str:
        """Construct full web URL."""
        protocol = "https" if self.port == 443 else "http"
        if (protocol == "https" and self.port == 443) or \
           (protocol == "http" and self.port == 80):
            return f"{protocol}://{self.server}"
        return f"{protocol}://{self.server}:{self.port}"
    
    @property
    def headers(self) -> Dict[str, str]:
        """Construct request headers."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = self.api_key
        return headers


@dataclass
class ComputationConfig:
    """Computation module configuration."""
    
    # Hoop stress computation
    hoop_stress_parallel: bool = True
    hoop_stress_workers: Optional[int] = None  # None = auto
    hoop_stress_chunk_size: int = 100
    
    # Flow parameters
    flow_params_samples: int = 10
    flow_params_tolerance: float = 1e-6
    
    # Inductance computation
    inductance_method: str = "analytical"  # analytical, numerical
    inductance_precision: float = 1e-9
    
    # General computation
    numpy_threads: Optional[int] = None  # None = auto
    cache_results: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.hoop_stress_workers is not None and self.hoop_stress_workers < 1:
            raise ValueError("hoop_stress_workers must be >= 1")
        
        if self.flow_params_samples < 1:
            raise ValueError("flow_params_samples must be >= 1")
        
        if self.inductance_method not in ("analytical", "numerical"):
            raise ValueError(f"Invalid inductance_method: {self.inductance_method}")


@dataclass
class FileConfig:
    """File and path configuration."""
    
    # Upload/download settings
    chunk_size: int = 8192  # bytes
    max_file_size: int = 100 * 1024 * 1024  # 100 MB
    
    # Temporary files
    temp_dir: Optional[Path] = None  # None = system temp
    cleanup_temp: bool = True
    
    # Output settings
    output_format: str = "json"  # json, yaml, csv
    pretty_print: bool = True
    
    # Data directories
    data_dir: Optional[Path] = None
    cache_dir: Optional[Path] = None
    
    def __post_init__(self):
        """Validate and normalize paths."""
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        
        if self.max_file_size < 1:
            raise ValueError("max_file_size must be >= 1")
        
        if self.output_format not in ("json", "yaml", "csv"):
            raise ValueError(f"Invalid output_format: {self.output_format}")
        
        # Expand paths
        if self.temp_dir:
            self.temp_dir = Path(self.temp_dir).expanduser().resolve()
        if self.data_dir:
            self.data_dir = Path(self.data_dir).expanduser().resolve()
        if self.cache_dir:
            self.cache_dir = Path(self.cache_dir).expanduser().resolve()


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Output targets
    console: bool = True
    file: Optional[Path] = None
    syslog: bool = False
    
    # Filtering
    debug_modules: List[str] = field(default_factory=list)
    quiet_modules: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate configuration."""
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid level: {self.level}. Must be one of {valid_levels}")
        
        self.level = self.level.upper()
        
        if self.file:
            self.file = Path(self.file).expanduser().resolve()


@dataclass
class Config:
    """Main configuration class."""
    
    api: APIConfig = field(default_factory=APIConfig)
    computation: ComputationConfig = field(default_factory=ComputationConfig)
    files: FileConfig = field(default_factory=FileConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Global settings
    debug: bool = False
    profile: str = "default"  # default, dev, staging, prod
    
    def __post_init__(self):
        """Apply profile-specific settings."""
        if self.profile == "dev":
            self.debug = True
            self.api.verify_ssl = False
            self.logging.level = "DEBUG"
        elif self.profile == "staging":
            self.api.server = "staging-magnetdb.lncmi.cnrs.fr"
        # prod uses defaults
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for serialization)."""
        return asdict(self)
    
    def validate(self) -> List[str]:
        """Validate entire configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.api.api_key:
            errors.append("API key is required (set MAGNETDB_API_KEY or provide in config)")
        
        if not self.api.server:
            errors.append("API server is required")
        
        # Additional cross-field validation
        if self.files.cache_dir and not self.computation.cache_results:
            errors.append("cache_dir set but cache_results is False")
        
        return errors


# ============================================================================
# Configuration Loading
# ============================================================================

def load_config_file(filepath: Path) -> Dict[str, Any]:
    """Load configuration from YAML file.
    
    Args:
        filepath: Path to config file
        
    Returns:
        Configuration dictionary
    """
    if not filepath.exists():
        return {}
    
    with open(filepath, "r") as f:
        data = yaml.safe_load(f)
        return data or {}


def load_env_config() -> Dict[str, Any]:
    """Load configuration from environment variables.
    
    Environment variables use MAGNETDB_ prefix:
    - MAGNETDB_API_SERVER
    - MAGNETDB_API_PORT
    - MAGNETDB_API_KEY
    - MAGNETDB_DEBUG
    - etc.
    
    Returns:
        Configuration dictionary
    """
    config: Dict[str, Any] = {}
    
    # API configuration
    if os.getenv("MAGNETDB_API_SERVER"):
        config.setdefault("api", {})["server"] = os.getenv("MAGNETDB_API_SERVER")
    
    if os.getenv("MAGNETDB_API_PORT"):
        config.setdefault("api", {})["port"] = int(os.getenv("MAGNETDB_API_PORT"))
    
    if os.getenv("MAGNETDB_API_KEY"):
        config.setdefault("api", {})["api_key"] = os.getenv("MAGNETDB_API_KEY")
    
    if os.getenv("MAGNETDB_TIMEOUT"):
        config.setdefault("api", {})["timeout"] = int(os.getenv("MAGNETDB_TIMEOUT"))
    
    if os.getenv("MAGNETDB_VERIFY_SSL"):
        value = os.getenv("MAGNETDB_VERIFY_SSL").lower()
        config.setdefault("api", {})["verify_ssl"] = value in ("true", "1", "yes")
    
    # Computation configuration
    if os.getenv("MAGNETDB_PARALLEL"):
        value = os.getenv("MAGNETDB_PARALLEL").lower()
        config.setdefault("computation", {})["hoop_stress_parallel"] = value in ("true", "1", "yes")
    
    # Logging configuration
    if os.getenv("MAGNETDB_LOG_LEVEL"):
        config.setdefault("logging", {})["level"] = os.getenv("MAGNETDB_LOG_LEVEL")
    
    # Global settings
    if os.getenv("MAGNETDB_DEBUG"):
        value = os.getenv("MAGNETDB_DEBUG").lower()
        config["debug"] = value in ("true", "1", "yes")
    
    if os.getenv("MAGNETDB_PROFILE"):
        config["profile"] = os.getenv("MAGNETDB_PROFILE")
    
    return config


def merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two configuration dictionaries (deep merge).
    
    Args:
        base: Base configuration
        override: Configuration to merge in (takes precedence)
        
    Returns:
        Merged configuration
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    
    return result


def load_config(
    config_file: Optional[Path] = None,
    profile: Optional[str] = None,
    **overrides
) -> Config:
    """Load configuration from multiple sources.
    
    Configuration precedence (lowest to highest):
    1. Hardcoded defaults (in Config class)
    2. System config file (/etc/magnetdb/config.yaml)
    3. User config file (~/.config/magnetdb/config.yaml)
    4. Project config file (./magnetdb.yaml or .magnetdb)
    5. Specified config file (config_file parameter)
    6. Environment variables (MAGNETDB_*)
    7. Function overrides (**overrides)
    
    Args:
        config_file: Optional config file path (overrides search)
        profile: Configuration profile (dev/staging/prod)
        **overrides: Direct configuration overrides
        
    Returns:
        Loaded and validated configuration
        
    Example:
        >>> cfg = load_config(profile="dev", api={"timeout": 60})
        >>> cfg = load_config(config_file=Path("my-config.yaml"))
    """
    config_data: Dict[str, Any] = {}
    
    # 1. Start with defaults (implicit in dataclass defaults)
    
    # 2. Load system config
    system_config = Path("/etc/magnetdb/config.yaml")
    if system_config.exists():
        config_data = merge_config(config_data, load_config_file(system_config))
    
    # 3. Load user config
    user_config = Path.home() / ".config" / "magnetdb" / "config.yaml"
    if user_config.exists():
        config_data = merge_config(config_data, load_config_file(user_config))
    
    # 4. Load project config
    for project_config in [Path("magnetdb.yaml"), Path(".magnetdb")]:
        if project_config.exists():
            config_data = merge_config(config_data, load_config_file(project_config))
            break
    
    # 5. Load specified config file
    if config_file and config_file.exists():
        config_data = merge_config(config_data, load_config_file(config_file))
    
    # 6. Load environment variables
    config_data = merge_config(config_data, load_env_config())
    
    # 7. Apply direct overrides
    if profile:
        config_data["profile"] = profile
    
    if overrides:
        config_data = merge_config(config_data, overrides)
    
    # Create Config object
    cfg = Config(
        api=APIConfig(**config_data.get("api", {})),
        computation=ComputationConfig(**config_data.get("computation", {})),
        files=FileConfig(**config_data.get("files", {})),
        logging=LoggingConfig(**config_data.get("logging", {})),
        debug=config_data.get("debug", False),
        profile=config_data.get("profile", "default"),
    )
    
    # Validate
    errors = cfg.validate()
    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return cfg


def save_config(config: Config, filepath: Path) -> None:
    """Save configuration to YAML file.
    
    Args:
        config: Configuration to save
        filepath: Output file path
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)


# ============================================================================
# Global configuration instance (optional, for convenience)
# ============================================================================

_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get or initialize global configuration instance.
    
    Returns:
        Global configuration
        
    Raises:
        RuntimeError: If config not initialized
    """
    global _global_config
    
    if _global_config is None:
        # Auto-initialize from environment on first access
        _global_config = load_config()
    
    return _global_config


def set_config(config: Config) -> None:
    """Set global configuration instance.
    
    Args:
        config: Configuration to set as global
    """
    global _global_config
    _global_config = config
```

### Step 1.2: Create Example Configuration File

Create `magnetdb.yaml.example`:

```yaml
# Python-MagnetAPI Configuration Example
# Copy this file to:
#   - /etc/magnetdb/config.yaml (system-wide)
#   - ~/.config/magnetdb/config.yaml (user-specific)
#   - ./magnetdb.yaml (project-specific)
#
# Or specify explicitly: python -m python_magnetapi --config config.yaml

# API Connection Settings
api:
  server: "magnetdb.lncmi.cnrs.fr"
  port: 443
  api_key: "your-api-key-here"  # Or use MAGNETDB_API_KEY env var
  base_path: "/api"
  
  # Network settings
  timeout: 30  # seconds
  verify_ssl: true
  retry_attempts: 3
  retry_delay: 1.0  # seconds
  
  # Concurrency settings
  max_concurrent: 10
  rate_limit: null  # null = no limit, or specify requests/second

# Computation Settings
computation:
  # Hoop stress computation
  hoop_stress_parallel: true
  hoop_stress_workers: null  # null = auto-detect CPU count
  hoop_stress_chunk_size: 100
  
  # Flow parameters
  flow_params_samples: 10
  flow_params_tolerance: 1e-6
  
  # Inductance computation
  inductance_method: "analytical"  # analytical or numerical
  inductance_precision: 1e-9
  
  # General
  numpy_threads: null  # null = auto
  cache_results: true

# File and Path Settings
files:
  chunk_size: 8192  # bytes
  max_file_size: 104857600  # 100 MB
  
  temp_dir: null  # null = system temp
  cleanup_temp: true
  
  output_format: "json"  # json, yaml, csv
  pretty_print: true
  
  data_dir: null
  cache_dir: "~/.cache/magnetdb"

# Logging Settings
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  console: true
  file: null  # null = no file logging, or specify path
  syslog: false
  
  debug_modules: []  # List of modules to debug
  quiet_modules: []  # List of modules to silence

# Global Settings
debug: false
profile: "default"  # default, dev, staging, prod

# Profile-specific configurations
# Uncomment and modify as needed:

# profiles:
#   dev:
#     debug: true
#     api:
#       server: "localhost"
#       port: 8000
#       verify_ssl: false
#     logging:
#       level: "DEBUG"
#   
#   staging:
#     api:
#       server: "staging-magnetdb.lncmi.cnrs.fr"
#       port: 443
#   
#   prod:
#     api:
#       server: "magnetdb.lncmi.cnrs.fr"
#       port: 443
#       verify_ssl: true
#     computation:
#       hoop_stress_parallel: true
#       cache_results: true
```

### Step 1.3: Create Configuration Schema Documentation

Create `python_magnetapi/config_schema.yaml`:

```yaml
# Configuration Schema Documentation
# This file documents all available configuration options

api:
  description: "API connection and network settings"
  
  server:
    type: string
    required: false
    default: "magnetdb.lncmi.cnrs.fr"
    description: "API server hostname or IP address"
    env: "MAGNETDB_API_SERVER"
  
  port:
    type: integer
    required: false
    default: 443
    description: "API server port"
    env: "MAGNETDB_API_PORT"
    validation: "1-65535"
  
  api_key:
    type: string
    required: true
    default: null
    description: "API authentication key"
    env: "MAGNETDB_API_KEY"
    sensitive: true
  
  timeout:
    type: integer
    required: false
    default: 30
    description: "Request timeout in seconds"
    env: "MAGNETDB_TIMEOUT"
  
  verify_ssl:
    type: boolean
    required: false
    default: true
    description: "Verify SSL certificates"
    env: "MAGNETDB_VERIFY_SSL"
  
  retry_attempts:
    type: integer
    required: false
    default: 3
    description: "Number of retry attempts for failed requests"
  
  retry_delay:
    type: float
    required: false
    default: 1.0
    description: "Delay between retry attempts in seconds"

computation:
  description: "Computation module settings"
  
  hoop_stress_parallel:
    type: boolean
    required: false
    default: true
    description: "Enable parallel computation for hoop stress"
    env: "MAGNETDB_PARALLEL"
  
  hoop_stress_workers:
    type: integer
    required: false
    default: null
    description: "Number of parallel workers (null = auto-detect)"
  
  flow_params_samples:
    type: integer
    required: false
    default: 10
    description: "Number of samples for flow parameter computation"

files:
  description: "File handling settings"
  
  chunk_size:
    type: integer
    required: false
    default: 8192
    description: "Chunk size in bytes for file upload/download"
  
  max_file_size:
    type: integer
    required: false
    default: 104857600
    description: "Maximum file size in bytes (default: 100 MB)"
  
  output_format:
    type: string
    required: false
    default: "json"
    description: "Default output format"
    validation: "json|yaml|csv"

logging:
  description: "Logging configuration"
  
  level:
    type: string
    required: false
    default: "INFO"
    description: "Logging level"
    env: "MAGNETDB_LOG_LEVEL"
    validation: "DEBUG|INFO|WARNING|ERROR|CRITICAL"
  
  console:
    type: boolean
    required: false
    default: true
    description: "Enable console logging"
  
  file:
    type: string
    required: false
    default: null
    description: "Log file path (null = no file logging)"

debug:
  type: boolean
  required: false
  default: false
  description: "Enable debug mode"
  env: "MAGNETDB_DEBUG"

profile:
  type: string
  required: false
  default: "default"
  description: "Configuration profile to use"
  env: "MAGNETDB_PROFILE"
  validation: "default|dev|staging|prod"
```

---

## Phase 2: Integrate Configuration into Existing Code

### Step 2.1: Update utils.py to Use Config

**Before:**
```python
def get_list(session, web, headers, mtype, debug=False):
    """Get list with hardcoded behavior."""
    # Configuration scattered and hardcoded
    timeout = 30  # Hardcoded!
    response = session.get(url, headers=headers, timeout=timeout)
```

**After:**
```python
from python_magnetapi.config import Config

def get_list(
    session,
    web: str,
    headers: Dict[str, str],
    mtype: str,
    config: Optional[Config] = None,
    debug: Optional[bool] = None
):
    """Get list using centralized configuration.
    
    Args:
        session: Requests session
        web: Base web URL
        headers: Request headers
        mtype: Resource type
        config: Configuration object (uses global if None)
        debug: Debug override (uses config.debug if None)
    """
    from python_magnetapi.config import get_config
    
    if config is None:
        config = get_config()
    
    if debug is None:
        debug = config.debug
    
    # Use configuration values
    timeout = config.api.timeout
    
    try:
        response = session.get(
            url,
            headers=headers,
            timeout=timeout,
            verify=config.api.verify_ssl
        )
        # ... rest of implementation
    except Exception as e:
        if debug:
            print(f"Request failed: {e}")
        raise
```

### Step 2.2: Update CLI to Use Config

**Update `cli.py` to load configuration:**

```python
from python_magnetapi.config import load_config, Config

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="MagnetDB API Client")
    
    # Add config file argument
    parser.add_argument(
        "--config",
        type=Path,
        help="Configuration file path"
    )
    
    # Add profile argument
    parser.add_argument(
        "--profile",
        choices=["default", "dev", "staging", "prod"],
        help="Configuration profile"
    )
    
    # Keep existing arguments for backward compatibility
    parser.add_argument("--server", help="API server")
    parser.add_argument("--port", type=int, help="API port")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    
    args = parser.parse_args()
    
    # Load configuration
    overrides = {}
    if args.server or args.port or args.api_key:
        overrides["api"] = {}
        if args.server:
            overrides["api"]["server"] = args.server
        if args.port:
            overrides["api"]["port"] = args.port
        if args.api_key:
            overrides["api"]["api_key"] = args.api_key
    
    if args.debug:
        overrides["debug"] = True
    
    try:
        config = load_config(
            config_file=args.config,
            profile=args.profile,
            **overrides
        )
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    
    # Initialize session with config
    from python_magnetapi.config import set_config
    set_config(config)
    
    session = requests.Session()
    
    # Execute command with config
    # ... rest of CLI logic
```

### Step 2.3: Update Domain Modules

**Pattern for updating modules:**

```python
# At top of file
from python_magnetapi.config import Config, get_config
from typing import Optional

# Update function signatures
def create(
    session,
    web: str,
    headers: Dict[str, str],
    data: Dict,
    config: Optional[Config] = None,
    debug: Optional[bool] = None
):
    """Create object using configuration.
    
    Args:
        ...
        config: Configuration (uses global if None)
        debug: Debug override (uses config.debug if None)
    """
    if config is None:
        config = get_config()
    
    if debug is None:
        debug = config.debug
    
    # Use config values instead of hardcoded
    timeout = config.api.timeout
    verify = config.api.verify_ssl
    
    # ... implementation
```

---

## Phase 3: Configuration CLI Commands

### Step 3.1: Add Config Subcommands

Add to CLI:

```python
# magnetapi config show - Show current configuration
# magnetapi config get api.timeout - Get specific value
# magnetapi config set api.timeout 60 - Set value (in project config)
# magnetapi config validate - Validate configuration
# magnetapi config init - Initialize config file

def cmd_config_show(args, config: Config):
    """Show current configuration."""
    import yaml
    print(yaml.dump(config.to_dict(), default_flow_style=False))
    return 0

def cmd_config_get(args, config: Config):
    """Get specific configuration value."""
    keys = args.key.split(".")
    value = config.to_dict()
    
    try:
        for key in keys:
            value = value[key]
        print(value)
        return 0
    except KeyError:
        print(f"Configuration key not found: {args.key}", file=sys.stderr)
        return 1

def cmd_config_set(args, config: Config):
    """Set configuration value in project config."""
    project_config = Path("magnetdb.yaml")
    
    # Load existing or create new
    if project_config.exists():
        with open(project_config) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    
    # Set value
    keys = args.key.split(".")
    current = data
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = args.value
    
    # Save
    with open(project_config, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    
    print(f"Set {args.key} = {args.value} in {project_config}")
    return 0

def cmd_config_init(args):
    """Initialize configuration file from template."""
    template = Path(__file__).parent / "magnetdb.yaml.example"
    target = Path(args.output or "magnetdb.yaml")
    
    if target.exists() and not args.force:
        print(f"Config file already exists: {target}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        return 1
    
    # Copy template
    import shutil
    shutil.copy(template, target)
    print(f"Created configuration file: {target}")
    print(f"Edit the file and set your API key.")
    return 0
```

---

## Phase 4: Testing and Documentation

### Step 4.1: Configuration Tests

Create `tests/unit/test_config.py`:

```python
"""Tests for configuration management."""

import pytest
import os
from pathlib import Path
from python_magnetapi.config import (
    Config,
    APIConfig,
    load_config,
    load_env_config,
    merge_config,
)


@pytest.mark.unit
class TestAPIConfig:
    """Test API configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        cfg = APIConfig()
        assert cfg.server == "magnetdb.lncmi.cnrs.fr"
        assert cfg.port == 443
        assert cfg.timeout == 30
    
    def test_web_property(self):
        """Test web URL construction."""
        cfg = APIConfig(server="test.local", port=443)
        assert cfg.web == "https://test.local"
        
        cfg = APIConfig(server="test.local", port=8080)
        assert cfg.web == "http://test.local:8080"
    
    def test_headers_property(self):
        """Test headers construction."""
        cfg = APIConfig(api_key="test-key-123")
        assert cfg.headers == {"Authorization": "test-key-123"}
        
        cfg = APIConfig(api_key=None)
        assert cfg.headers == {}
    
    def test_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError, match="Invalid port"):
            APIConfig(port=99999)
        
        with pytest.raises(ValueError, match="Invalid timeout"):
            APIConfig(timeout=-1)


@pytest.mark.unit
class TestConfigLoading:
    """Test configuration loading."""
    
    def test_load_env_config(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("MAGNETDB_API_SERVER", "test.local")
        monkeypatch.setenv("MAGNETDB_API_PORT", "8080")
        monkeypatch.setenv("MAGNETDB_API_KEY", "test-key")
        monkeypatch.setenv("MAGNETDB_DEBUG", "true")
        
        env_config = load_env_config()
        
        assert env_config["api"]["server"] == "test.local"
        assert env_config["api"]["port"] == 8080
        assert env_config["api"]["api_key"] == "test-key"
        assert env_config["debug"] is True
    
    def test_merge_config(self):
        """Test configuration merging."""
        base = {"api": {"server": "base", "port": 443}, "debug": False}
        override = {"api": {"server": "override"}, "debug": True}
        
        merged = merge_config(base, override)
        
        assert merged["api"]["server"] == "override"
        assert merged["api"]["port"] == 443  # Preserved from base
        assert merged["debug"] is True
    
    def test_config_precedence(self, tmp_path, monkeypatch):
        """Test configuration precedence."""
        # Create config file
        config_file = tmp_path / "test.yaml"
        config_file.write_text("api:\n  timeout: 60\n")
        
        # Set environment variable
        monkeypatch.setenv("MAGNETDB_TIMEOUT", "90")
        
        # Load with override
        cfg = load_config(
            config_file=config_file,
            api={"timeout": 120}  # Highest precedence
        )
        
        # Override should win
        assert cfg.api.timeout == 120
```

### Step 4.2: Configuration Documentation

Create `docs/configuration.md` (update existing):

```markdown
# Configuration Management

## Overview

Python-MagnetAPI uses a layered configuration system that supports:
- Config files (YAML)
- Environment variables
- Command-line arguments
- Programmatic configuration

## Configuration Precedence

Configuration is loaded from multiple sources with the following precedence (lowest to highest):

1. **Hardcoded defaults** - Built-in default values
2. **System config** - `/etc/magnetdb/config.yaml`
3. **User config** - `~/.config/magnetdb/config.yaml`
4. **Project config** - `./magnetdb.yaml` or `./.magnetdb`
5. **Environment variables** - `MAGNETDB_*`
6. **Command-line arguments** - `--server`, `--api-key`, etc.

## Quick Start

### Environment Variables

```bash
# Minimum required
export MAGNETDB_API_KEY="your-api-key"

# Optional
export MAGNETDB_API_SERVER="magnetdb.lncmi.cnrs.fr"
export MAGNETDB_API_PORT="443"
export MAGNETDB_DEBUG="true"
```

### Config File

Create `magnetdb.yaml` in your project:

```yaml
api:
  server: "magnetdb.lncmi.cnrs.fr"
  api_key: "your-api-key"
  
debug: false
```

Initialize from template:

```bash
magnetapi config init
# Edit magnetdb.yaml with your settings
```

## Configuration Options

See [Configuration Schema](config_schema.yaml) for all available options.

### API Settings

- `api.server` - API server hostname
- `api.port` - API server port
- `api.api_key` - Authentication key (**required**)
- `api.timeout` - Request timeout in seconds
- `api.verify_ssl` - Verify SSL certificates

### Computation Settings

- `computation.hoop_stress_parallel` - Enable parallel computation
- `computation.flow_params_samples` - Number of computation samples

### File Settings

- `files.chunk_size` - Upload/download chunk size
- `files.output_format` - Default output format (json/yaml/csv)

### Logging Settings

- `logging.level` - Log level (DEBUG/INFO/WARNING/ERROR)
- `logging.file` - Log file path

## Profiles

Use profiles for different environments:

```bash
# Development (localhost, no SSL verification)
magnetapi --profile dev list magnet

# Staging
magnetapi --profile staging list magnet

# Production (default)
magnetapi list magnet
```

## CLI Configuration Commands

```bash
# Show current configuration
magnetapi config show

# Get specific value
magnetapi config get api.timeout

# Set value (saves to ./magnetdb.yaml)
magnetapi config set api.timeout 60

# Validate configuration
magnetapi config validate

# Initialize config file
magnetapi config init
```

## Programmatic Usage

```python
from python_magnetapi.config import load_config

# Load from defaults + environment
config = load_config()

# Load with specific file
config = load_config(config_file="my-config.yaml")

# Load with overrides
config = load_config(
    profile="dev",
    api={"timeout": 60}
)

# Access configuration
print(config.api.web)
print(config.api.timeout)

# Use in API calls
from python_magnetapi import utils
result = utils.get_list(session, config.api.web, config.api.headers, "magnet", config=config)
```
```

---

## Success Criteria

✅ **Implementation Complete When:**
1. Core config.py module with dataclasses created
2. All existing hardcoded values moved to config
3. Configuration loading from files/env/CLI implemented
4. Config validation with helpful error messages
5. Example config file (magnetdb.yaml.example) provided
6. Configuration documentation updated
7. CLI config commands implemented (show/get/set/init)
8. All modules updated to use Config
9. Tests for configuration loading and validation
10. Backward compatibility maintained (env vars still work)

✅ **Quality Metrics:**
- Zero hardcoded configuration values in code
- All config options documented
- Config validation catches errors early
- Tests cover all config loading paths
- Clear precedence order documented

---

## Migration Guide

For users to update their code:

```python
# OLD - Hardcoded and scattered
server = os.getenv("MAGNETDB_API_SERVER", "default")
port = int(os.getenv("MAGNETDB_API_PORT", "443"))
timeout = 30  # Hardcoded!

session = requests.Session()
web = f"https://{server}:{port}"
headers = {"Authorization": os.getenv("MAGNETDB_API_KEY")}

result = utils.get_list(session, web, headers, "magnet", debug=True)

# NEW - Centralized configuration
from python_magnetapi.config import load_config

config = load_config()  # Loads from all sources automatically

session = requests.Session()
result = utils.get_list(
    session,
    config.api.web,
    config.api.headers,
    "magnet",
    config=config
)
```

---

## Implementation Timeline

**Week 1: Core Infrastructure**
- Create config.py with all dataclasses
- Implement load_config with precedence
- Create example config file
- Write configuration tests

**Week 2: Integration**
- Update utils.py to use Config
- Update all domain modules (part, magnet, site, etc.)
- Update CLI to load configuration
- Maintain backward compatibility

**Week 3: CLI Commands**
- Implement config show/get/set/init commands
- Add config validation
- Update CLI help text

**Week 4: Documentation & Testing**
- Update configuration documentation
- Add migration guide
- Write integration tests
- Test all configuration loading paths

---

## Notes for Implementation

1. **Backward Compatibility** - Ensure existing env vars continue to work
2. **Security** - Never log or print sensitive values (API keys)
3. **Validation** - Validate early to catch errors before API calls
4. **Type Safety** - Use dataclasses with type hints
5. **Documentation** - Document every configuration option
6. **Testing** - Test all precedence layers and merging logic
7. **CLI Integration** - Update CLI to load and use config

## Dependencies

**Should be done after:**
- Type Hints (for better config type safety)

**Recommended before:**
- Test Suite Enhancement (makes testing easier with config)

**Required packages:**
- PyYAML (for YAML config files)

---

## Document Version

**Version**: 1.0  
**Created**: 2026-03-12  
**Task**: Configuration Management - Eliminate Hardcoded Values  
**Priority**: Tier 2 (Code Quality & Maintainability)  
**Status**: Ready for implementation
