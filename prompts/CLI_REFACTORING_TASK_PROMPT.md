# CLI Module Refactoring

## Task Overview

**Priority**: Tier 2 (Code Quality & Maintainability)  
**Status**: Not Started  
**Current Size**: 684 lines (single monolithic function)  
**Estimated Effort**: Large (major structural refactoring)  
**Breaking Changes**: No (CLI interface remains identical)  

## Current State Analysis

### Problems Identified

1. ❌ **Monolithic main() function** - 684 lines, all logic in one function
2. ❌ **Mixed concerns** - Argument parsing, validation, business logic, error handling, output all mixed
3. ❌ **Code duplication** - Similar patterns repeated for each command (get ids, validate name, handle errors)
4. ❌ **Hard to test** - No way to test individual command handlers
5. ❌ **Poor readability** - Long if/elif chains, deeply nested blocks
6. ❌ **No separation of concerns** - HTTP setup, argument parsing, command execution all in one function
7. ❌ **Difficult to extend** - Adding new commands requires modifying the massive main() function
8. ❌ **No error context** - Generic RuntimeError scattered throughout

### Current Structure

```
cli.py (684 lines)
├── main()
    ├── Argument parser setup (lines 21-234)
    │   ├── Global args (server, port, debug, https)
    │   ├── list subcommand args
    │   ├── view subcommand args
    │   ├── create subcommand args
    │   ├── delete subcommand args
    │   ├── setup subcommand args
    │   ├── run subcommand args
    │   └── compute subcommand args
    │
    ├── HTTP setup (lines 235-251)
    │   ├── Build web URL
    │   ├── Configure headers
    │   └── Setup session/verify
    │
    └── Command execution (lines 252-682)
        ├── if args.command == "list": (lines 268-273)
        ├── if args.command == "view": (lines 274-291)
        ├── if args.command == "create": (lines 292-330)
        ├── if args.command == "delete": (lines 331-348)
        ├── if args.command == "setup": (lines 349-505)
        ├── if args.command == "run": (lines 506-577)
        ├── if args.command == "compute": (lines 578-678)
        └── if args.command == "post": (lines 679-680)
```

### Commands Implemented

1. **list** - List objects of a given type
2. **view** - View details of a specific object
3. **create** - Create new object from JSON/file
4. **delete** - Delete object by name
5. **setup** - Setup simulation for magnet/site
6. **run** - Run simulation
7. **compute** - Compute derived quantities (inductances, flow_params, hoop_stress)
8. **process** (post) - Not implemented

### Code Duplication Examples

**Pattern 1: Get object list and validate name**
```python
# Repeated ~8 times throughout the code
ids = utils.get_list(s, web, headers=headers, mtype=otype, debug=args.debug)
if args.name in ids:
    # do something
else:
    raise RuntimeError(f"cannot found {args.name} in {args.mtype.upper()}")
```

**Pattern 2: Setup HTTP session**
```python
# Done inline at start of command execution
with requests.Session() as s:
    # verify setup logic
    # command execution
```

**Pattern 3: Type checking for commands**
```python
# Repeated for many subcommands
if otype not in ["magnet", "site"]:
    raise RuntimeError(f"unexpected type {args.mtype} in {args.command} subcommand")
```

---

## Implementation Plan

### Design Goals

1. **Separation of Concerns** - Split parsing, validation, execution, output
2. **Testability** - Each command handler independently testable
3. **Maintainability** - Easy to add new commands or modify existing ones
4. **No Breaking Changes** - CLI interface remains identical
5. **Type Safety** - Add type hints throughout
6. **Error Handling** - Use custom exceptions (after exception framework is complete)
7. **DRY Principle** - Eliminate code duplication

### Target Architecture

```
python_magnetapi/
├── cli.py                    # Main entry point (50-100 lines)
├── cli/
│   ├── __init__.py          # Export public API
│   ├── parser.py            # Argument parser configuration (150 lines)
│   ├── context.py           # CLI context and configuration (50 lines)
│   ├── base.py              # Base command handler class (100 lines)
│   └── commands/
│       ├── __init__.py      # Command registry
│       ├── list.py          # ListCommand handler (~50 lines)
│       ├── view.py          # ViewCommand handler (~50 lines)
│       ├── create.py        # CreateCommand handler (~80 lines)
│       ├── delete.py        # DeleteCommand handler (~50 lines)
│       ├── setup.py         # SetupCommand handler (~150 lines)
│       ├── run.py           # RunCommand handler (~80 lines)
│       ├── compute.py       # ComputeCommand handler (~150 lines)
│       └── process.py       # ProcessCommand handler (~30 lines)
```

---

## Phase 1: Foundation and Infrastructure

### Step 1.1: Create CLI Context Class

Create `python_magnetapi/cli/context.py`:

```python
"""CLI context and configuration."""

from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class CLIContext:
    """Context passed to all command handlers.
    
    Attributes:
        server: API server hostname
        port: API port number
        api_key: API authentication key
        debug: Debug mode flag
        https: Use HTTPS flag
        session: Requests session (initialized later)
        headers: HTTP headers for API requests
        web: Full API URL (computed)
    """
    
    server: str
    port: int
    api_key: str
    debug: bool = False
    https: bool = False
    session: Optional[requests.Session] = None
    
    @property
    def headers(self) -> dict:
        """HTTP headers for API authentication."""
        return {"Authorization": self.api_key}
    
    @property
    def web(self) -> str:
        """Full API base URL."""
        protocol = "https" if self.https else "http"
        return f"{protocol}://{self.server}:{self.port}"
    
    @property
    def verify_ssl(self) -> bool:
        """Whether to verify SSL certificates."""
        return not self.https  # Don't verify if using custom HTTPS
    
    def __enter__(self):
        """Context manager entry - create session."""
        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        if self.session:
            self.session.close()
```

### Step 1.2: Create Base Command Handler

Create `python_magnetapi/cli/base.py`:

```python
"""Base command handler class."""

from abc import ABC, abstractmethod
import argparse
from typing import Optional, List, Dict
from rich.console import Console

from .context import CLIContext
from .. import utils


class BaseCommand(ABC):
    """Base class for all CLI command handlers.
    
    Subclasses should implement:
        - name: Command name
        - help: Command help text
        - configure_parser(): Add command-specific arguments
        - execute(): Execute command logic
    """
    
    name: str = ""
    help: str = ""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize command handler.
        
        Args:
            console: Rich console for output (created if not provided)
        """
        self.console = console or Console()
    
    @abstractmethod
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure argument parser for this command.
        
        Args:
            parser: Subparser for this command
        """
        pass
    
    @abstractmethod
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute the command.
        
        Args:
            args: Parsed command-line arguments
            context: CLI context with session and configuration
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        pass
    
    # Helper methods for common operations
    
    def get_object_list(
        self,
        context: CLIContext,
        mtype: str
    ) -> Dict[str, int]:
        """Get list of objects by type.
        
        Args:
            context: CLI context
            mtype: Resource type (material, part, magnet, etc.)
            
        Returns:
            Dictionary mapping names to IDs
        """
        return utils.get_list(
            context.session,
            context.web,
            headers=context.headers,
            mtype=mtype,
            debug=context.debug
        )
    
    def get_object_by_name(
        self,
        context: CLIContext,
        mtype: str,
        name: str
    ) -> Optional[dict]:
        """Get object by name.
        
        Args:
            context: CLI context
            mtype: Resource type
            name: Object name
            
        Returns:
            Object data dictionary, or None if not found
            
        Raises:
            NotFoundError: If object doesn't exist
        """
        ids = self.get_object_list(context, mtype)
        
        if name not in ids:
            raise NotFoundError(
                f"{mtype} '{name}' not found",
                resource_type=mtype,
                resource_name=name,
                available=list(ids.keys())
            )
        
        return utils.get_object(
            context.session,
            context.web,
            context.headers,
            ids[name],
            mtype,
            debug=context.debug
        )
    
    def validate_resource_type(
        self,
        mtype: str,
        allowed_types: List[str],
        command_name: Optional[str] = None
    ) -> None:
        """Validate that resource type is allowed for this command.
        
        Args:
            mtype: Resource type to validate
            allowed_types: List of allowed types
            command_name: Command name for error message
            
        Raises:
            InvalidDataError: If type is not allowed
        """
        if mtype not in allowed_types:
            cmd = command_name or self.name
            raise InvalidDataError(
                f"Command '{cmd}' does not support resource type '{mtype}'",
                field="mtype",
                value=mtype,
                allowed=allowed_types
            )
```

### Step 1.3: Create Command Registry

Create `python_magnetapi/cli/commands/__init__.py`:

```python
"""Command registry and imports."""

from typing import Dict, Type
from ..base import BaseCommand

# Import all command handlers
from .list import ListCommand
from .view import ViewCommand
from .create import CreateCommand
from .delete import DeleteCommand
from .setup import SetupCommand
from .run import RunCommand
from .compute import ComputeCommand
from .process import ProcessCommand


# Command registry
COMMANDS: Dict[str, Type[BaseCommand]] = {
    "list": ListCommand,
    "view": ViewCommand,
    "create": CreateCommand,
    "delete": DeleteCommand,
    "setup": SetupCommand,
    "run": RunCommand,
    "compute": ComputeCommand,
    "process": ProcessCommand,
}


def get_command(name: str) -> Type[BaseCommand]:
    """Get command class by name.
    
    Args:
        name: Command name
        
    Returns:
        Command class
        
    Raises:
        KeyError: If command not found
    """
    return COMMANDS[name]
```

---

## Phase 2: Implement Command Handlers

### Step 2.1: ListCommand Handler

Create `python_magnetapi/cli/commands/list.py`:

```python
"""List command handler."""

import argparse
from typing import Optional
from rich.table import Table

from ..base import BaseCommand
from ..context import CLIContext


class ListCommand(BaseCommand):
    """List objects of a given type."""
    
    name = "list"
    help = "List objects in MagnetDB"
    
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure list command arguments."""
        parser.add_argument(
            "--mtype",
            help="Object type to list",
            type=str,
            choices=[
                "material",
                "part",
                "magnet",
                "site",
                "record",
                "server",
                "simulation",
            ],
            default="magnet",
        )
    
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute list command.
        
        Args:
            args: Parsed arguments
            context: CLI context
            
        Returns:
            Exit code (0 for success)
        """
        # Get object list
        ids = self.get_object_list(context, args.mtype)
        
        # Display results
        self.console.print(
            f"\n[bold]{args.mtype.upper()}:[/bold] found {len(ids)} items\n"
        )
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="green")
        
        for name, id in sorted(ids.items()):
            table.add_row(name, str(id))
        
        self.console.print(table)
        
        return 0
```

### Step 2.2: ViewCommand Handler

Create `python_magnetapi/cli/commands/view.py`:

```python
"""View command handler."""

import argparse
import json
from rich.syntax import Syntax

from ..base import BaseCommand
from ..context import CLIContext


class ViewCommand(BaseCommand):
    """View details of a specific object."""
    
    name = "view"
    help = "View object details"
    
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure view command arguments."""
        parser.add_argument(
            "--mtype",
            help="Object type to view",
            type=str,
            choices=[
                "material",
                "part",
                "magnet",
                "site",
                "record",
                "server",
                "simulation",
            ],
            default="magnet",
        )
        parser.add_argument(
            "--name",
            help="Object name",
            type=str,
            required=True,
        )
    
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute view command.
        
        Args:
            args: Parsed arguments
            context: CLI context
            
        Returns:
            Exit code (0 for success)
        """
        # Get object by name
        obj = self.get_object_by_name(context, args.mtype, args.name)
        
        # Display as formatted JSON
        json_str = json.dumps(obj, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        
        self.console.print(f"\n[bold]{args.mtype.upper()}:[/bold] {args.name}\n")
        self.console.print(syntax)
        
        return 0
```

### Step 2.3: CreateCommand Handler

Create `python_magnetapi/cli/commands/create.py`:

```python
"""Create command handler."""

import argparse
import json
from typing import Dict, Any

from ..base import BaseCommand
from ..context import CLIContext
from ... import part, magnet, site, record, material


class CreateCommand(BaseCommand):
    """Create new object from JSON data or file."""
    
    name = "create"
    help = "Create new object"
    
    # Map resource types to creation functions
    CREATORS = {
        "material": material.create,
        "part": part.create,
        "magnet": magnet.create,
        "site": site.create,
        "record": record.create,
    }
    
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure create command arguments."""
        parser.add_argument(
            "--mtype",
            help="Object type to create",
            type=str,
            choices=[
                "material",
                "part",
                "magnet",
                "site",
                "record",
                "server",
                "simulation",
            ],
            default="magnet",
        )
        
        # Mutually exclusive data sources
        data_group = parser.add_mutually_exclusive_group(required=True)
        data_group.add_argument(
            "--data",
            help="JSON data",
            type=json.loads,
        )
        data_group.add_argument(
            "--file",
            help="JSON file path",
            type=str,
        )
    
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute create command.
        
        Args:
            args: Parsed arguments
            context: CLI context
            
        Returns:
            Exit code (0 for success)
        """
        # Load data from file or command line
        data: Dict[str, Any] = {}
        if args.file:
            with open(args.file, "r") as f:
                data = json.load(f)
        else:
            data = args.data
        
        # Validate resource type
        if args.mtype not in self.CREATORS:
            self.console.print(
                f"[yellow]Warning:[/yellow] No specialized creator for {args.mtype}, "
                f"using generic creation"
            )
            # Use generic utils.create_object
            from ... import utils
            obj_id = utils.create_object(
                context.session,
                context.web,
                context.headers,
                mtype=args.mtype,
                data=data,
                debug=context.debug,
            )
        else:
            # Use specialized creator
            creator = self.CREATORS[args.mtype]
            obj_id = creator(
                context.session,
                context.web,
                context.headers,
                data=data,
                debug=context.debug,
            )
        
        # Display success
        self.console.print(
            f"\n[green]✓[/green] Created {args.mtype} with ID: [bold]{obj_id}[/bold]"
        )
        
        return 0
```

### Step 2.4: DeleteCommand Handler

Create `python_magnetapi/cli/commands/delete.py`:

```python
"""Delete command handler."""

import argparse

from ..base import BaseCommand
from ..context import CLIContext
from ... import utils


class DeleteCommand(BaseCommand):
    """Delete object by name."""
    
    name = "delete"
    help = "Delete object"
    
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure delete command arguments."""
        parser.add_argument(
            "--mtype",
            help="Object type to delete",
            type=str,
            choices=[
                "material",
                "part",
                "magnet",
                "site",
                "record",
                "server",
                "simulation",
            ],
            default="magnet",
        )
        parser.add_argument(
            "--name",
            help="Object name",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--force",
            help="Skip confirmation",
            action="store_true",
        )
    
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute delete command.
        
        Args:
            args: Parsed arguments
            context: CLI context
            
        Returns:
            Exit code (0 for success)
        """
        # Get object ID
        ids = self.get_object_list(context, args.mtype)
        
        if args.name not in ids:
            self.console.print(
                f"[red]Error:[/red] {args.mtype} '{args.name}' not found"
            )
            return 1
        
        obj_id = ids[args.name]
        
        # Confirmation prompt (unless --force)
        if not args.force:
            response = self.console.input(
                f"[yellow]Delete {args.mtype} '{args.name}' (ID: {obj_id})? [y/N]:[/yellow] "
            )
            if response.lower() not in ["y", "yes"]:
                self.console.print("[dim]Cancelled[/dim]")
                return 0
        
        # Delete object
        utils.del_object(
            context.session,
            context.web,
            context.headers,
            obj_id,
            args.mtype,
            debug=context.debug,
        )
        
        self.console.print(
            f"[green]✓[/green] Deleted {args.mtype} '{args.name}' (ID: {obj_id})"
        )
        
        return 0
```

### Step 2.5: SetupCommand Handler

Create `python_magnetapi/cli/commands/setup.py`:

```python
"""Setup command handler."""

import argparse
from typing import List

from ..base import BaseCommand
from ..context import CLIContext


class SetupCommand(BaseCommand):
    """Setup simulation for magnet or site."""
    
    name = "setup"
    help = "Setup simulation"
    
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure setup command arguments."""
        parser.add_argument(
            "--mtype",
            help="Object type",
            type=str,
            choices=["magnet", "site"],
            default="magnet",
        )
        parser.add_argument(
            "--name",
            help="Object name",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--current",
            help="Requested current (default: 31kA)",
            nargs="+",
            metavar="Current",
            type=float,
            default=[31.0e3],
        )
        parser.add_argument(
            "--geometry",
            help="Geometry type",
            type=str,
            choices=["Axi", "3D"],
            default="Axi",
        )
        parser.add_argument(
            "--static",
            help="Enable static mode",
            action="store_true",
        )
        parser.add_argument(
            "--nonlinear",
            help="Enable nonlinear mode",
            action="store_true",
        )
        parser.add_argument(
            "--method",
            help="Method",
            type=str,
            default="cfpdes",
        )
        parser.add_argument(
            "--model",
            help="Model",
            type=str,
            default="thmagel_hcurl",
        )
        parser.add_argument(
            "--cooling",
            help="Cooling mode",
            type=str,
            choices=["mean", "meanH", "grad", "gradH", "gradHZ"],
            default="meanH",
        )
        parser.add_argument(
            "--wd",
            help="Working directory",
            type=str,
            default=".",
        )
    
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute setup command.
        
        Args:
            args: Parsed arguments
            context: CLI context
            
        Returns:
            Exit code (0 for success)
        """
        # Validate resource type
        self.validate_resource_type(args.mtype, ["magnet", "site"])
        
        # Get object
        obj = self.get_object_by_name(context, args.mtype, args.name)
        
        # Import appropriate setup module
        if args.mtype == "magnet":
            from ... import magnet
            simulation_id = magnet.setup(
                context.session,
                context.web,
                context.headers,
                obj["id"],
                currents=args.current,
                geometry=args.geometry,
                static=args.static,
                nonlinear=args.nonlinear,
                method=args.method,
                model=args.model,
                cooling=args.cooling,
                workdir=args.wd,
                debug=context.debug,
            )
        else:  # site
            from ... import site
            simulation_id = site.setup(
                context.session,
                context.web,
                context.headers,
                obj["id"],
                currents=args.current,
                geometry=args.geometry,
                static=args.static,
                nonlinear=args.nonlinear,
                method=args.method,
                model=args.model,
                cooling=args.cooling,
                workdir=args.wd,
                debug=context.debug,
            )
        
        self.console.print(
            f"\n[green]✓[/green] Setup complete for {args.mtype} '{args.name}'"
        )
        self.console.print(f"  Simulation ID: [bold]{simulation_id}[/bold]")
        self.console.print(f"  Working directory: {args.wd}")
        
        return 0
```

### Step 2.6: ComputeCommand Handler

Create `python_magnetapi/cli/commands/compute.py`:

```python
"""Compute command handler."""

import argparse

from ..base import BaseCommand
from ..context import CLIContext


class ComputeCommand(BaseCommand):
    """Compute derived quantities."""
    
    name = "compute"
    help = "Compute inductances, flow parameters, or hoop stress"
    
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure compute command arguments."""
        parser.add_argument(
            "--mtype",
            help="Object type",
            type=str,
            choices=["part", "magnet", "site", "record"],
            default="magnet",
        )
        parser.add_argument(
            "--name",
            help="Object name",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--inductances",
            help="Compute self and mutual inductances",
            action="store_true",
        )
        parser.add_argument(
            "--flow_params",
            help="Compute flow parameters",
            action="store_true",
        )
        parser.add_argument(
            "--hoop_stress",
            help="Compute hoop stress history",
            action="store_true",
        )
        parser.add_argument(
            "--samples",
            help="Number of samples",
            type=int,
            default=20,
        )
    
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute compute command.
        
        Args:
            args: Parsed arguments
            context: CLI context
            
        Returns:
            Exit code (0 for success)
        """
        # Get object
        obj = self.get_object_by_name(context, args.mtype, args.name)
        obj_id = obj["id"]
        
        # Compute inductances
        if args.inductances:
            self._compute_inductances(args, context, obj_id)
        
        # Compute flow parameters
        if args.flow_params:
            self._compute_flow_params(args, context, obj_id)
        
        # Compute hoop stress
        if args.hoop_stress:
            self._compute_hoop_stress(args, context, obj_id)
        
        # If no computation requested, show help
        if not (args.inductances or args.flow_params or args.hoop_stress):
            self.console.print(
                "[yellow]No computation requested. Use --inductances, "
                "--flow_params, or --hoop_stress[/yellow]"
            )
            return 1
        
        return 0
    
    def _compute_inductances(
        self,
        args: argparse.Namespace,
        context: CLIContext,
        obj_id: int
    ) -> None:
        """Compute inductances."""
        from ... import inductances
        
        self.console.print(f"\n[bold]Computing inductances...[/bold]")
        
        inductances.compute(
            context.session,
            context.web,
            context.headers,
            oid=obj_id,
            mtype=args.mtype,
            debug=context.debug,
        )
        
        self.console.print("[green]✓[/green] Inductances computed")
    
    def _compute_flow_params(
        self,
        args: argparse.Namespace,
        context: CLIContext,
        obj_id: int
    ) -> None:
        """Compute flow parameters."""
        # Validate type
        if args.mtype != "magnet":
            raise InvalidDataError(
                "Flow parameters can only be computed for magnets",
                field="mtype",
                value=args.mtype,
                expected="magnet"
            )
        
        from ... import flow_params
        
        self.console.print(f"\n[bold]Computing flow parameters...[/bold]")
        
        flow_params.compute(
            context.session,
            context.web,
            context.headers,
            oid=obj_id,
            samples=args.samples,
            debug=context.debug,
        )
        
        self.console.print("[green]✓[/green] Flow parameters computed")
    
    def _compute_hoop_stress(
        self,
        args: argparse.Namespace,
        context: CLIContext,
        obj_id: int
    ) -> None:
        """Compute hoop stress."""
        # Validate type
        if args.mtype != "part":
            raise InvalidDataError(
                "Hoop stress can only be computed for parts",
                field="mtype",
                value=args.mtype,
                expected="part"
            )
        
        from ... import hoop_stress
        
        self.console.print(f"\n[bold]Computing hoop stress...[/bold]")
        
        hoop_stress.compute(
            context.session,
            context.web,
            context.headers,
            mtype=args.mtype,
            oid=obj_id,
            debug=context.debug,
        )
        
        self.console.print("[green]✓[/green] Hoop stress computed")
```

---

## Phase 3: Create Main CLI Entry Point

### Step 3.1: Create Parser Configuration

Create `python_magnetapi/cli/parser.py`:

```python
"""Argument parser configuration."""

import argparse
import os
from typing import Dict, Type

from .base import BaseCommand
from .commands import COMMANDS


def create_parser(commands: Dict[str, Type[BaseCommand]]) -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Args:
        commands: Dictionary of command name to command class
        
    Returns:
        Configured ArgumentParser
    """
    # Main parser
    parser = argparse.ArgumentParser(
        prog="python_magnetapi",
        description="CLI for interacting with MagnetDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Global arguments
    parser.add_argument(
        "--server",
        help="API server hostname",
        type=str,
        default=os.getenv("MAGNETDB_API_SERVER", "api.magnetdb-dev.local"),
    )
    parser.add_argument(
        "--port",
        help="API server port",
        type=int,
        default=8000,
    )
    parser.add_argument(
        "--debug",
        help="Enable debug mode",
        action="store_true",
    )
    parser.add_argument(
        "--https",
        help="Use HTTPS",
        action="store_true",
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Available commands",
        required=True,
    )
    
    # Configure each command's parser
    for cmd_name, cmd_class in commands.items():
        cmd_instance = cmd_class()
        cmd_parser = subparsers.add_parser(
            cmd_name,
            help=cmd_instance.help,
        )
        cmd_instance.configure_parser(cmd_parser)
    
    return parser
```

### Step 3.2: Refactor Main CLI Entry Point

Update `python_magnetapi/cli.py`:

```python
#! /usr/bin/python3

"""CLI for interacting with MagnetDB."""

import os
import sys
from rich.console import Console

from .cli.parser import create_parser
from .cli.context import CLIContext
from .cli.commands import COMMANDS
from .exceptions import MagnetAPIException, AuthenticationError


def main(argv=None) -> int:
    """Main CLI entry point.
    
    Args:
        argv: Command-line arguments (for testing)
        
    Returns:
        Exit code (0 for success)
    """
    console = Console()
    
    try:
        # Parse arguments
        parser = create_parser(COMMANDS)
        args = parser.parse_args(argv)
        
        if args.debug:
            console.print(f"[dim]Arguments: {args}[/dim]")
        
        # Validate API key
        api_key = os.getenv("MAGNETDB_API_KEY")
        if not api_key:
            console.print(
                "[red]Error:[/red] MAGNETDB_API_KEY environment variable not set"
            )
            return 2
        
        # Create CLI context
        context = CLIContext(
            server=args.server,
            port=args.port,
            api_key=api_key,
            debug=args.debug,
            https=args.https,
        )
        
        # Get command handler
        command_class = COMMANDS[args.command]
        command = command_class(console=console)
        
        # Execute command with context
        with context:
            return command.execute(args, context)
    
    except AuthenticationError as e:
        console.print(f"[red]Authentication Error:[/red] {e.message}", style="bold")
        if e.context:
            console.print(f"[dim]{e.context}[/dim]")
        console.print("\n[yellow]Tip:[/yellow] Check your MAGNETDB_API_KEY environment variable")
        return 2
    
    except MagnetAPIException as e:
        console.print(f"[red]Error:[/red] {e.message}", style="bold")
        if e.context and args.debug:
            console.print(f"[dim]Context: {e.context}[/dim]")
        return 1
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        return 130
    
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="bold")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 99


if __name__ == "__main__":
    sys.exit(main())
```

---

## Phase 4: Testing and Migration

### Step 4.1: Create Command Handler Tests

Create `tests/cli/test_list_command.py`:

```python
"""Tests for list command."""

import pytest
from unittest.mock import Mock, patch
from python_magnetapi.cli.commands.list import ListCommand
from python_magnetapi.cli.context import CLIContext


def test_list_command_execution():
    """Test list command executes correctly."""
    # Mock context
    context = Mock(spec=CLIContext)
    context.session = Mock()
    context.web = "http://test"
    context.headers = {"Authorization": "test"}
    context.debug = False
    
    # Mock utils.get_list
    with patch("python_magnetapi.utils.get_list") as mock_get_list:
        mock_get_list.return_value = {
            "M10": 1,
            "M11": 2,
        }
        
        # Create command and execute
        cmd = ListCommand()
        args = Mock()
        args.mtype = "magnet"
        
        exit_code = cmd.execute(args, context)
        
        # Verify
        assert exit_code == 0
        mock_get_list.assert_called_once()


def test_list_command_parser_configuration():
    """Test list command parser configuration."""
    import argparse
    
    parser = argparse.ArgumentParser()
    cmd = ListCommand()
    cmd.configure_parser(parser)
    
    # Should have mtype argument
    args = parser.parse_args(["--mtype", "part"])
    assert args.mtype == "part"
```

### Step 4.2: Create Integration Tests

Create `tests/cli/test_cli_integration.py`:

```python
"""Integration tests for CLI."""

import pytest
from unittest.mock import patch, Mock
from python_magnetapi.cli import main


def test_cli_list_command():
    """Test CLI list command end-to-end."""
    with patch("python_magnetapi.utils.get_list") as mock_list:
        mock_list.return_value = {"M10": 1}
        
        exit_code = main(["--server", "test", "list", "--mtype", "magnet"])
        
        assert exit_code == 0


def test_cli_missing_api_key():
    """Test CLI fails gracefully without API key."""
    import os
    
    # Temporarily remove API key
    old_key = os.environ.pop("MAGNETDB_API_KEY", None)
    
    try:
        exit_code = main(["list"])
        assert exit_code == 2  # Authentication error
    finally:
        if old_key:
            os.environ["MAGNETDB_API_KEY"] = old_key
```

### Step 4.3: Migration Strategy

**Backwards Compatibility Testing:**

1. Create test suite that calls old CLI interface
2. Ensure all commands produce same output
3. Test error cases match old behavior
4. Verify exit codes are consistent

**Gradual Migration:**

1. Keep old cli.py as cli_old.py temporarily
2. Run both implementations side-by-side in tests
3. Compare outputs for all commands
4. Once verified, remove old implementation

**User Communication:**

1. Update README with any CLI improvements
2. Note that CLI interface is unchanged
3. Mention any new features (better error messages, colored output)

---

## Success Criteria

✅ **Implementation Complete When:**
1. cli.py reduced from 684 to <100 lines
2. All command handlers in separate modules
3. Each command handler independently testable
4. Base command class provides common functionality
5. CLI context manages session and configuration
6. Command registry allows easy extension
7. All existing commands work identically
8. Test coverage ≥ 80% for command handlers
9. Rich console output with colors and formatting
10. Better error messages with actionable hints

✅ **Code Quality Metrics:**
- Main cli.py: <100 lines
- Each command handler: <150 lines
- Cyclomatic complexity per function: <10
- Zero code duplication (DRY principle)
- All functions have type hints
- All functions have docstrings

✅ **Testing Coverage:**
- Unit tests for each command handler
- Integration tests for full CLI execution
- Test all error cases
- Test argument parsing
- Test help messages

---

## Benefits of Refactoring

### Maintainability
- Easy to find and modify command logic
- Clear separation of concerns
- Easy to add new commands (just create new handler)

### Testability
- Each command independently testable
- Mock-friendly architecture
- Easy to test error cases

### Readability
- Small, focused modules
- Clear naming conventions
- Type hints throughout

### Extensibility
- Plugin-style architecture
- Command registry makes adding commands trivial
- Base class provides common functionality

### User Experience
- Better error messages with Rich formatting
- Colored output for better readability
- Consistent help messages

---

## Implementation Timeline

**Week 1: Foundation**
- Create CLI infrastructure (context, base, parser)
- Create command registry
- Set up testing framework

**Week 2: Core Commands**
- Implement list, view, create, delete commands
- Write unit tests
- Test backwards compatibility

**Week 3: Advanced Commands**
- Implement setup, run, compute commands
- Write unit tests
- Integration testing

**Week 4: Polish & Migration**
- Code review and cleanup
- Complete documentation
- Remove old CLI code
- Update README and docs

---

## Notes for Implementation

1. **Start with infrastructure** - Get context, base, and parser working first
2. **One command at a time** - Implement and test each command handler individually
3. **Test backwards compatibility** - Ensure CLI interface doesn't change
4. **Use Rich for output** - Leverage tables, syntax highlighting, colors
5. **Keep it simple** - Don't over-engineer, focus on clarity
6. **Document as you go** - Update docstrings and docs continuously

## Dependencies

**Should be done after:**
- Error Handling Framework (for proper exception handling)
- Type Hints (for type safety)

**Can be done in parallel with:**
- Logging Framework (commands can add logging calls)

---

## Document Version

**Version**: 1.0  
**Created**: 2026-03-12  
**Task**: CLI Module Refactoring  
**Priority**: Tier 2 (Code Quality & Maintainability)  
**Status**: Ready for implementation  
**Dependencies**: Error Handling Framework (recommended)
