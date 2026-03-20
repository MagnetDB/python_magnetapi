# Test Suite Enhancement and Fixture Population

## Task Overview

**Priority**: Tier 2 (Code Quality & Maintainability)  
**Status**: Minimal testing (210 lines, integration tests only)  
**Estimated Effort**: Large (comprehensive test suite from scratch)  
**Breaking Changes**: No (tests only)  

## Current State Analysis

### What Exists ✓
- ✅ Basic test file: `test_list.py` (210 lines)
- ✅ Test data files: 12 fixture files (.dat, .json, .yaml)
- ✅ Two test classes: `TestList`, `TestCrud`
- ✅ Integration tests (hit real API)
- ✅ Basic pytest configuration in pyproject.toml

### What's Missing ❌
- ❌ **No unit tests** - All tests are integration tests
- ❌ **No mocking** - Tests depend on real API server
- ❌ **No conftest.py** - Fixture organization missing
- ❌ **No test factories** - Fixture data created manually
- ❌ **No parametrized tests** - Lots of code duplication
- ❌ **Low coverage** - Only basic list/create/delete tested
- ❌ **No test database setup** - Manual database required
- ❌ **No CI/CD tests** - Can't run without external API
- ❌ **No test documentation** - No guide for running tests
- ❌ **No performance tests** - No benchmarks

### Current Test Structure

```
tests/
├── test_list.py (210 lines)
│   ├── TestList - Integration tests for list operations
│   └── TestCrud - Integration tests for CRUD operations
├── Fixture data (12 files)
│   ├── *.dat - Legacy format fixture data
│   ├── *.json - JSON fixture data
│   └── *.yaml - YAML fixture data
├── conftest.py.old - Inactive fixture configuration
└── __init__.py (empty)
```

### Issues with Current Tests

1. **Integration-only** - Can't run without API server
2. **No isolation** - Tests create/delete real data
3. **Order-dependent** - Tests must run in specific order
4. **Slow** - Network calls for every test
5. **Brittle** - Break if API structure changes
6. **Hard to debug** - No clear separation of concerns
7. **No mocking** - Can't test error cases easily

---

## Implementation Plan

### Design Goals

1. **Two-tier testing** - Unit tests (mocked) + Integration tests (real DB)
2. **Fast unit tests** - Run without external services (<5 seconds)
3. **Reliable integration tests** - Docker-compose test environment
4. **Fixture factories** - Generate test data programmatically
5. **High coverage** - Target ≥80% code coverage
6. **Parametrized tests** - Reduce code duplication
7. **CI/CD ready** - Run in GitHub Actions
8. **Well documented** - Clear setup and usage instructions

### Target Architecture

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── fixtures/
│   ├── __init__.py
│   ├── factories.py              # Test data factories
│   ├── mock_responses.py         # Mock API responses
│   └── sample_data.py            # Sample test data
├── unit/                         # Unit tests (mocked, fast)
│   ├── __init__.py
│   ├── test_utils.py             # Test utils.py with mocking
│   ├── test_part.py              # Test part.py with mocking
│   ├── test_magnet.py            # Test magnet.py with mocking
│   ├── test_site.py              # Test site.py with mocking
│   ├── test_material.py          # Test material.py with mocking
│   ├── test_geometry.py          # Test geometry.py with mocking
│   ├── test_flow_params.py       # Test flow_params.py
│   ├── test_hoop_stress.py       # Test hoop_stress.py
│   └── test_inductances.py       # Test inductances.py
├── integration/                  # Integration tests (real DB)
│   ├── __init__.py
│   ├── test_api_crud.py          # Test full CRUD operations
│   ├── test_api_list.py          # Test list operations
│   ├── test_simulation.py        # Test simulation workflows
│   └── test_computation.py       # Test computation workflows
├── cli/                          # CLI tests
│   ├── __init__.py
│   ├── test_commands.py          # Test CLI commands
│   └── test_cli_integration.py   # Test full CLI workflows
├── data/                         # Test data files
│   ├── materials/                # Material test data
│   ├── parts/                    # Part test data
│   ├── magnets/                  # Magnet test data
│   └── sites/                    # Site test data
├── docker-compose.test.yml       # Test database setup
└── README.md                     # Test documentation
```

---

## Phase 1: Test Infrastructure Setup

### Step 1.1: Create conftest.py with Fixtures

Create `tests/conftest.py`:

```python
"""Pytest configuration and shared fixtures."""

import os
import pytest
from unittest.mock import Mock, MagicMock
import requests
import json
from pathlib import Path


# ============================================================================
# Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "unit: Unit tests with mocking (fast)",
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests with real database (slow)",
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow tests (skip by default)",
    )


# ============================================================================
# Mock Fixtures (for unit tests)
# ============================================================================

@pytest.fixture
def mock_session():
    """Mock requests.Session for unit tests."""
    session = MagicMock(spec=requests.Session)
    session.verify = True
    return session


@pytest.fixture
def mock_response():
    """Factory fixture for mock responses."""
    def _make_response(status_code=200, json_data=None, text="OK"):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.text = text
        response.url = "http://test-api/endpoint"
        return response
    return _make_response


@pytest.fixture
def api_config():
    """API configuration for tests."""
    return {
        "server": "test-api.local",
        "port": 8000,
        "api_key": "test-key-123",
        "headers": {"Authorization": "test-key-123"},
        "web": "http://test-api.local:8000",
    }


@pytest.fixture
def mock_api_success(mock_session, mock_response, api_config):
    """Mock successful API responses."""
    mock_session.get.return_value = mock_response(
        status_code=200,
        json_data={"id": 1, "name": "test"}
    )
    mock_session.post.return_value = mock_response(
        status_code=200,
        json_data={"id": 1}
    )
    mock_session.put.return_value = mock_response(status_code=200)
    mock_session.delete.return_value = mock_response(status_code=200)
    
    return {
        "session": mock_session,
        "config": api_config,
    }


# ============================================================================
# Real Database Fixtures (for integration tests)
# ============================================================================

@pytest.fixture(scope="session")
def test_db_config():
    """Configuration for test database.
    
    Reads from environment or uses defaults for docker-compose setup.
    """
    return {
        "server": os.getenv("TEST_MAGNETDB_API_SERVER", "localhost"),
        "port": int(os.getenv("TEST_MAGNETDB_API_PORT", "8001")),
        "api_key": os.getenv("TEST_MAGNETDB_API_KEY", "test-key"),
        "timeout": 30,
    }


@pytest.fixture(scope="session")
def test_db_session(test_db_config):
    """Real session for integration tests.
    
    Creates a session that connects to test database.
    Only use with @pytest.mark.integration tests.
    """
    import time
    
    # Wait for database to be ready (in case of docker-compose)
    max_retries = 10
    for i in range(max_retries):
        try:
            session = requests.Session()
            web = f"http://{test_db_config['server']}:{test_db_config['port']}"
            headers = {"Authorization": test_db_config['api_key']}
            
            # Test connection
            response = session.get(f"{web}/api/health", headers=headers, timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            if i == max_retries - 1:
                pytest.skip("Test database not available")
            time.sleep(2)
    
    yield {
        "session": session,
        "config": test_db_config,
        "headers": headers,
        "web": web,
    }
    
    session.close()


@pytest.fixture
def clean_test_db(test_db_session):
    """Clean test database before/after test.
    
    Use with integration tests that create data.
    Automatically cleans up test objects by prefix.
    """
    test_prefix = "test_"
    created_objects = []
    
    def register_object(mtype: str, obj_id: int):
        """Register object for cleanup."""
        created_objects.append((mtype, obj_id))
    
    # Provide registration function
    yield register_object
    
    # Cleanup after test
    from python_magnetapi import utils
    for mtype, obj_id in reversed(created_objects):
        try:
            utils.del_object(
                test_db_session["session"],
                test_db_session["web"],
                test_db_session["headers"],
                obj_id,
                mtype,
                debug=False,
            )
        except Exception as e:
            print(f"Cleanup failed for {mtype} {obj_id}: {e}")


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def load_test_data(test_data_dir):
    """Factory to load test data files."""
    def _load(category: str, filename: str):
        """Load JSON test data file.
        
        Args:
            category: Subdirectory (materials, parts, etc.)
            filename: File name
            
        Returns:
            Parsed JSON data
        """
        filepath = test_data_dir / category / filename
        with open(filepath, "r") as f:
            return json.load(f)
    return _load


# ============================================================================
# Parametrization Helpers
# ============================================================================

RESOURCE_TYPES = ["material", "part", "magnet", "site", "record", "simulation"]


@pytest.fixture(params=RESOURCE_TYPES)
def resource_type(request):
    """Parametrize over all resource types."""
    return request.param
```

### Step 1.2: Create Test Data Factories

Create `tests/fixtures/factories.py`:

```python
"""Test data factories using factory pattern."""

from typing import Dict, Any, Optional
from datetime import datetime
import random


class MaterialFactory:
    """Factory for creating test material data."""
    
    @staticmethod
    def create(
        name: Optional[str] = None,
        nuance: str = "test-nuance",
        **kwargs
    ) -> Dict[str, Any]:
        """Create material test data.
        
        Args:
            name: Material name (auto-generated if not provided)
            nuance: Material nuance
            **kwargs: Additional fields
            
        Returns:
            Material data dictionary
        """
        if name is None:
            name = f"test_material_{random.randint(1000, 9999)}"
        
        data = {
            "name": name,
            "nuance": nuance,
            "type": "conductor",
            "properties": {
                "rho": 1.8e-8,
                "E": 120e9,
                "nu": 0.3,
                "alpha": 3.9e-3,
            }
        }
        data.update(kwargs)
        return data
    
    @staticmethod
    def batch(count: int = 3) -> list:
        """Create multiple materials."""
        return [MaterialFactory.create() for _ in range(count)]


class PartFactory:
    """Factory for creating test part data."""
    
    @staticmethod
    def create(
        name: Optional[str] = None,
        material_id: Optional[int] = None,
        part_type: str = "helix",
        **kwargs
    ) -> Dict[str, Any]:
        """Create part test data.
        
        Args:
            name: Part name (auto-generated if not provided)
            material_id: Material ID
            part_type: Part type (helix, ring, etc.)
            **kwargs: Additional fields
            
        Returns:
            Part data dictionary
        """
        if name is None:
            name = f"test_part_{random.randint(1000, 9999)}"
        
        data = {
            "name": name,
            "type": part_type,
            "status": "in_stock",
        }
        
        if material_id is not None:
            data["material_id"] = material_id
        
        data.update(kwargs)
        return data
    
    @staticmethod
    def batch(count: int = 3, material_id: Optional[int] = None) -> list:
        """Create multiple parts."""
        return [
            PartFactory.create(material_id=material_id)
            for _ in range(count)
        ]


class MagnetFactory:
    """Factory for creating test magnet data."""
    
    @staticmethod
    def create(
        name: Optional[str] = None,
        be: str = "Bitter",
        part_ids: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create magnet test data.
        
        Args:
            name: Magnet name (auto-generated if not provided)
            be: Magnet BE type
            part_ids: List of part IDs
            **kwargs: Additional fields
            
        Returns:
            Magnet data dictionary
        """
        if name is None:
            name = f"test_magnet_{random.randint(1000, 9999)}"
        
        data = {
            "name": name,
            "be": be,
        }
        
        if part_ids is not None:
            data["parts"] = part_ids
        
        data.update(kwargs)
        return data


class SiteFactory:
    """Factory for creating test site data."""
    
    @staticmethod
    def create(
        name: Optional[str] = None,
        magnet_ids: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create site test data.
        
        Args:
            name: Site name (auto-generated if not provided)
            magnet_ids: List of magnet IDs
            **kwargs: Additional fields
            
        Returns:
            Site data dictionary
        """
        if name is None:
            name = f"test_site_{random.randint(1000, 9999)}"
        
        data = {
            "name": name,
            "status": "in_stock",
        }
        
        if magnet_ids is not None:
            data["magnets"] = magnet_ids
        
        data.update(kwargs)
        return data


class RecordFactory:
    """Factory for creating test record data."""
    
    @staticmethod
    def create(
        name: Optional[str] = None,
        site_id: Optional[int] = None,
        date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create record test data.
        
        Args:
            name: Record name (auto-generated if not provided)
            site_id: Site ID
            date: Record date
            **kwargs: Additional fields
            
        Returns:
            Record data dictionary
        """
        if name is None:
            name = f"test_record_{random.randint(1000, 9999)}"
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data = {
            "name": name,
            "date": date,
            "data": {
                "current": 31000,
                "voltage": 220,
                "temperature": 25.0,
            }
        }
        
        if site_id is not None:
            data["site_id"] = site_id
        
        data.update(kwargs)
        return data


# Export all factories
__all__ = [
    "MaterialFactory",
    "PartFactory",
    "MagnetFactory",
    "SiteFactory",
    "RecordFactory",
]
```

### Step 1.3: Create Mock Response Library

Create `tests/fixtures/mock_responses.py`:

```python
"""Mock API responses for unit testing."""

from typing import Dict, Any, List


class MockResponses:
    """Collection of mock API responses."""
    
    # Successful responses
    
    @staticmethod
    def list_success(items: List[Dict], page: int = 1, total: int = None) -> Dict:
        """Mock successful list response."""
        if total is None:
            total = len(items)
        
        return {
            "current_page": page,
            "last_page": (total + 9) // 10,  # 10 items per page
            "total": total,
            "items": items,
        }
    
    @staticmethod
    def get_success(resource_type: str = "magnet", **fields) -> Dict:
        """Mock successful get response."""
        defaults = {
            "id": 1,
            "name": f"test_{resource_type}",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        defaults.update(fields)
        return defaults
    
    @staticmethod
    def create_success(resource_id: int = 1) -> Dict:
        """Mock successful create response."""
        return {"id": resource_id}
    
    @staticmethod
    def update_success() -> Dict:
        """Mock successful update response."""
        return {"message": "Updated successfully"}
    
    @staticmethod
    def delete_success() -> Dict:
        """Mock successful delete response."""
        return {"message": "Deleted successfully"}
    
    # Error responses
    
    @staticmethod
    def error_not_found(resource_type: str = "resource", resource_id: int = 1) -> Dict:
        """Mock 404 not found response."""
        return {
            "detail": f"{resource_type} with id {resource_id} not found",
            "status_code": 404,
        }
    
    @staticmethod
    def error_unauthorized() -> Dict:
        """Mock 401 unauthorized response."""
        return {
            "detail": "Unauthorized. Invalid API key.",
            "status_code": 401,
        }
    
    @staticmethod
    def error_forbidden() -> Dict:
        """Mock 403 forbidden response."""
        return {
            "detail": "Forbidden. Insufficient permissions.",
            "status_code": 403,
        }
    
    @staticmethod
    def error_validation(field: str = "name", message: str = "Required field") -> Dict:
        """Mock 422 validation error response."""
        return {
            "detail": [
                {
                    "loc": ["body", field],
                    "msg": message,
                    "type": "value_error",
                }
            ],
            "status_code": 422,
        }
    
    @staticmethod
    def error_server() -> Dict:
        """Mock 500 server error response."""
        return {
            "detail": "Internal server error",
            "status_code": 500,
        }
    
    # Sample data
    
    @staticmethod
    def sample_material() -> Dict:
        """Sample material data."""
        return {
            "id": 1,
            "name": "CuAg0.1",
            "nuance": "test",
            "type": "conductor",
            "properties": {
                "rho": 1.8e-8,
                "E": 120e9,
                "nu": 0.3,
            }
        }
    
    @staticmethod
    def sample_part() -> Dict:
        """Sample part data."""
        return {
            "id": 1,
            "name": "H1",
            "type": "helix",
            "material_id": 1,
            "status": "in_stock",
        }
    
    @staticmethod
    def sample_magnet() -> Dict:
        """Sample magnet data."""
        return {
            "id": 1,
            "name": "M10",
            "be": "Bitter",
            "parts": [1, 2, 3],
        }
    
    @staticmethod
    def sample_site() -> Dict:
        """Sample site data."""
        return {
            "id": 1,
            "name": "M9_M10",
            "magnets": [1],
            "status": "in_stock",
        }
```

---

## Phase 2: Unit Tests with Mocking

### Step 2.1: Unit Tests for utils.py

Create `tests/unit/test_utils.py`:

```python
"""Unit tests for utils.py with mocking."""

import pytest
from unittest.mock import Mock, patch, call
from python_magnetapi import utils
from tests.fixtures.mock_responses import MockResponses


@pytest.mark.unit
class TestGetList:
    """Test get_list function."""
    
    def test_get_list_single_page(self, mock_session, api_config, mock_response):
        """Test get_list with single page of results."""
        # Setup mock response
        items = [
            {"id": 1, "name": "M10"},
            {"id": 2, "name": "M11"},
        ]
        mock_session.get.return_value = mock_response(
            status_code=200,
            json_data=MockResponses.list_success(items)
        )
        
        # Execute
        result = utils.get_list(
            mock_session,
            api_config["web"],
            api_config["headers"],
            "magnet"
        )
        
        # Verify
        assert result == {"M10": 1, "M11": 2}
        mock_session.get.assert_called_once()
    
    def test_get_list_multiple_pages(self, mock_session, api_config, mock_response):
        """Test get_list paginating through multiple pages."""
        # Setup mock responses for 2 pages
        page1_items = [{"id": i, "name": f"M{i}"} for i in range(1, 11)]
        page2_items = [{"id": i, "name": f"M{i}"} for i in range(11, 15)]
        
        mock_session.get.side_effect = [
            mock_response(200, MockResponses.list_success(page1_items, page=1, total=14)),
            mock_response(200, MockResponses.list_success(page2_items, page=2, total=14)),
        ]
        
        # Execute
        result = utils.get_list(
            mock_session,
            api_config["web"],
            api_config["headers"],
            "magnet"
        )
        
        # Verify
        assert len(result) == 14
        assert mock_session.get.call_count == 2
    
    def test_get_list_auth_error(self, mock_session, api_config, mock_response):
        """Test get_list handles authentication error."""
        mock_session.get.return_value = mock_response(
            status_code=401,
            json_data=MockResponses.error_unauthorized()
        )
        
        # Should handle error gracefully (current implementation prints)
        result = utils.get_list(
            mock_session,
            api_config["web"],
            api_config["headers"],
            "magnet"
        )
        
        # With error handling framework, this would raise AuthenticationError
        # For now, check it returns empty dict or handles error
        assert result == {}


@pytest.mark.unit
class TestGetObject:
    """Test get_object function."""
    
    def test_get_object_success(self, mock_session, api_config, mock_response):
        """Test get_object retrieves object successfully."""
        expected = MockResponses.sample_magnet()
        mock_session.get.return_value = mock_response(200, expected)
        
        result = utils.get_object(
            mock_session,
            api_config["web"],
            api_config["headers"],
            1,
            "magnet"
        )
        
        assert result == expected
        mock_session.get.assert_called_with(
            f"{api_config['web']}/api/magnets/1",
            headers=api_config["headers"]
        )
    
    def test_get_object_not_found(self, mock_session, api_config, mock_response):
        """Test get_object handles not found."""
        mock_session.get.return_value = mock_response(
            404,
            MockResponses.error_not_found("magnet", 999)
        )
        
        result = utils.get_object(
            mock_session,
            api_config["web"],
            api_config["headers"],
            999,
            "magnet"
        )
        
        # Currently returns None, with error framework would raise NotFoundError
        assert result is None


@pytest.mark.unit
class TestCreateObject:
    """Test create_object function."""
    
    def test_create_object_success(self, mock_session, api_config, mock_response):
        """Test create_object creates successfully."""
        mock_session.post.return_value = mock_response(
            200,
            MockResponses.create_success(42)
        )
        
        data = {"name": "test_magnet", "be": "Bitter"}
        result = utils.create_object(
            mock_session,
            api_config["web"],
            api_config["headers"],
            "magnet",
            data
        )
        
        assert result == 42
        mock_session.post.assert_called_once()
    
    def test_create_object_validation_error(self, mock_session, api_config, mock_response):
        """Test create_object handles validation error."""
        mock_session.post.return_value = mock_response(
            422,
            MockResponses.error_validation("name", "Field required")
        )
        
        data = {"be": "Bitter"}  # Missing name
        result = utils.create_object(
            mock_session,
            api_config["web"],
            api_config["headers"],
            "magnet",
            data
        )
        
        # With error framework, would raise ValidationError
        assert result is None


@pytest.mark.unit
@pytest.mark.parametrize("mtype", ["material", "part", "magnet", "site", "record"])
def test_get_list_all_types(mock_session, api_config, mock_response, mtype):
    """Test get_list works for all resource types."""
    items = [{"id": 1, "name": f"test_{mtype}"}]
    mock_session.get.return_value = mock_response(
        200,
        MockResponses.list_success(items)
    )
    
    result = utils.get_list(
        mock_session,
        api_config["web"],
        api_config["headers"],
        mtype
    )
    
    assert f"test_{mtype}" in result
```

### Step 2.2: Unit Tests for Domain Modules

Create `tests/unit/test_part.py`:

```python
"""Unit tests for part.py with mocking."""

import pytest
from unittest.mock import patch
from python_magnetapi import part
from tests.fixtures.factories import PartFactory, MaterialFactory
from tests.fixtures.mock_responses import MockResponses


@pytest.mark.unit
class TestPartCreate:
    """Test part creation."""
    
    @patch('python_magnetapi.part.utils.create_object')
    @patch('python_magnetapi.part.utils.get_list')
    def test_create_with_material_name(
        self,
        mock_get_list,
        mock_create,
        mock_session,
        api_config
    ):
        """Test creating part with material name (string)."""
        # Setup mocks
        mock_get_list.return_value = {"test_material": 5}
        mock_create.return_value = 42
        
        # Create part with material name
        data = PartFactory.create(material="test_material")
        
        result = part.create(
            mock_session,
            api_config["web"],
            api_config["headers"],
            data
        )
        
        # Verify material was looked up and part was created
        assert result == 42
        mock_get_list.assert_called_with(
            mock_session,
            api_config["web"],
            headers=api_config["headers"],
            mtype="material",
            debug=False
        )
    
    @patch('python_magnetapi.part.utils.create_object')
    def test_create_with_material_id(
        self,
        mock_create,
        mock_session,
        api_config
    ):
        """Test creating part with material ID (int)."""
        mock_create.return_value = 42
        
        data = PartFactory.create(material_id=5)
        
        result = part.create(
            mock_session,
            api_config["web"],
            api_config["headers"],
            data
        )
        
        assert result == 42
    
    @patch('python_magnetapi.part.geometry.create')
    @patch('python_magnetapi.part.utils.create_object')
    def test_create_with_geometry(
        self,
        mock_create_part,
        mock_create_geometry,
        mock_session,
        api_config
    ):
        """Test creating part with geometry."""
        mock_create_part.return_value = 42
        mock_create_geometry.return_value = 100
        
        data = PartFactory.create(
            material_id=5,
            geometry=[{"file": "geometry.json"}]
        )
        
        result = part.create(
            mock_session,
            api_config["web"],
            api_config["headers"],
            data
        )
        
        # Verify both part and geometry were created
        assert result == 42
        mock_create_part.assert_called_once()
        mock_create_geometry.assert_called_once()
```

---

## Phase 3: Integration Tests with Real Database

### Step 3.1: Docker Compose Test Database

Create `tests/docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  test-db:
    image: postgres:15
    environment:
      POSTGRES_DB: magnetdb_test
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    ports:
      - "5433:5432"
    volumes:
      - test-db-data:/var/lib/postgresql/data
      - ./test-db-init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_user"]
      interval: 5s
      timeout: 5s
      retries: 5
  
  test-api:
    image: magnetdb/api:latest  # Replace with actual MagnetDB API image
    environment:
      DATABASE_URL: postgresql://test_user:test_password@test-db:5432/magnetdb_test
      API_KEY: test-integration-key-12345
      LOG_LEVEL: DEBUG
    ports:
      - "8001:8000"
    depends_on:
      test-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  test-db-data:
```

### Step 3.2: Integration Test for CRUD Operations

Create `tests/integration/test_api_crud.py`:

```python
"""Integration tests for CRUD operations against real test database."""

import pytest
from tests.fixtures.factories import (
    MaterialFactory,
    PartFactory,
    MagnetFactory,
    SiteFactory,
)
from python_magnetapi import utils, material, part, magnet, site


@pytest.mark.integration
class TestMaterialCRUD:
    """Integration tests for material CRUD."""
    
    def test_create_list_get_delete_material(self, test_db_session, clean_test_db):
        """Test full material lifecycle."""
        session = test_db_session["session"]
        web = test_db_session["web"]
        headers = test_db_session["headers"]
        
        # Create material
        data = MaterialFactory.create()
        mat_id = material.create(session, web, headers, data)
        assert mat_id is not None
        clean_test_db("material", mat_id)
        
        # List materials - verify it appears
        materials = utils.get_list(session, web, headers, "material")
        assert data["name"] in materials
        assert materials[data["name"]] == mat_id
        
        # Get material - verify data
        retrieved = utils.get_object(session, web, headers, mat_id, "material")
        assert retrieved["name"] == data["name"]
        assert retrieved["nuance"] == data["nuance"]
        
        # Delete material
        utils.del_object(session, web, headers, mat_id, "material")
        
        # Verify deleted
        materials = utils.get_list(session, web, headers, "material")
        assert data["name"] not in materials


@pytest.mark.integration
class TestHierarchicalCreation:
    """Integration tests for creating hierarchical objects."""
    
    def test_create_full_site_hierarchy(self, test_db_session, clean_test_db):
        """Test creating material -> part -> magnet -> site."""
        session = test_db_session["session"]
        web = test_db_session["web"]
        headers = test_db_session["headers"]
        
        # Create material
        mat_data = MaterialFactory.create()
        mat_id = material.create(session, web, headers, mat_data)
        clean_test_db("material", mat_id)
        
        # Create parts
        part_ids = []
        for i in range(3):
            part_data = PartFactory.create(material_id=mat_id)
            part_id = part.create(session, web, headers, part_data)
            part_ids.append(part_id)
            clean_test_db("part", part_id)
        
        # Create magnet with parts
        mag_data = MagnetFactory.create(part_ids=part_ids)
        mag_id = magnet.create(session, web, headers, mag_data)
        clean_test_db("magnet", mag_id)
        
        # Create site with magnet
        site_data = SiteFactory.create(magnet_ids=[mag_id])
        site_id = site.create(session, web, headers, site_data)
        clean_test_db("site", site_id)
        
        # Verify hierarchy
        site_obj = utils.get_object(session, web, headers, site_id, "site")
        assert mag_id in site_obj["magnets"]
        
        mag_obj = utils.get_object(session, web, headers, mag_id, "magnet")
        for part_id in part_ids:
            assert part_id in mag_obj["parts"]


@pytest.mark.integration
@pytest.mark.parametrize("count", [1, 5, 10])
def test_bulk_creation(test_db_session, clean_test_db, count):
    """Test creating multiple objects efficiently."""
    session = test_db_session["session"]
    web = test_db_session["web"]
    headers = test_db_session["headers"]
    
    created_ids = []
    
    # Create multiple materials
    for mat_data in MaterialFactory.batch(count):
        mat_id = material.create(session, web, headers, mat_data)
        created_ids.append(mat_id)
        clean_test_db("material", mat_id)
    
    # Verify all created
    assert len(created_ids) == count
    materials = utils.get_list(session, web, headers, "material")
    for mat_id in created_ids:
        assert mat_id in materials.values()
```

### Step 3.3: Integration Test for Computation

Create `tests/integration/test_computation.py`:

```python
"""Integration tests for computation modules."""

import pytest
from tests.fixtures.factories import MagnetFactory, PartFactory
from python_magnetapi import inductances, flow_params, hoop_stress


@pytest.mark.integration
@pytest.mark.slow
class TestInductanceComputation:
    """Integration tests for inductance computation."""
    
    def test_compute_inductances_magnet(self, test_db_session, clean_test_db):
        """Test inductance computation for magnet."""
        session = test_db_session["session"]
        web = test_db_session["web"]
        headers = test_db_session["headers"]
        
        # Create test magnet (simplified)
        # In practice, would need full hierarchy with geometry
        mag_id = 1  # Use existing test magnet
        
        # Compute inductances
        result = inductances.compute(
            session,
            web,
            headers,
            oid=mag_id,
            mtype="magnet"
        )
        
        # Verify result structure
        assert result is not None
        # Add more specific assertions based on expected output


@pytest.mark.integration
@pytest.mark.slow
class TestFlowParamsComputation:
    """Integration tests for flow parameters computation."""
    
    def test_compute_flow_params(self, test_db_session):
        """Test flow parameters computation."""
        session = test_db_session["session"]
        web = test_db_session["web"]
        headers = test_db_session["headers"]
        
        # Use existing test magnet
        mag_id = 1
        
        # Compute flow parameters
        result = flow_params.compute(
            session,
            web,
            headers,
            oid=mag_id,
            samples=5,  # Small sample for faster testing
        )
        
        assert result is not None
```

---

## Phase 4: CLI Testing

### Step 4.1: CLI Command Tests

Create `tests/cli/test_commands.py`:

```python
"""Tests for CLI command handlers."""

import pytest
from unittest.mock import Mock, patch
from python_magnetapi.cli.commands.list import ListCommand
from python_magnetapi.cli.commands.view import ViewCommand
from python_magnetapi.cli.context import CLIContext


@pytest.mark.unit
class TestListCommand:
    """Test list command handler."""
    
    @patch('python_magnetapi.cli.commands.list.utils.get_list')
    def test_list_magnets(self, mock_get_list):
        """Test listing magnets."""
        # Setup
        mock_get_list.return_value = {"M10": 1, "M11": 2}
        
        cmd = ListCommand()
        args = Mock()
        args.mtype = "magnet"
        
        context = Mock(spec=CLIContext)
        context.session = Mock()
        context.web = "http://test"
        context.headers = {}
        context.debug = False
        
        # Execute
        exit_code = cmd.execute(args, context)
        
        # Verify
        assert exit_code == 0
        mock_get_list.assert_called_once()


@pytest.mark.integration
class TestListCommandIntegration:
    """Integration tests for list command."""
    
    def test_list_real_api(self, test_db_session):
        """Test list command against real API."""
        from python_magnetapi.cli.commands.list import ListCommand
        from python_magnetapi.cli.context import CLIContext
        
        # Create context from test DB session
        context = CLIContext(
            server=test_db_session["config"]["server"],
            port=test_db_session["config"]["port"],
            api_key=test_db_session["config"]["api_key"],
            debug=True,
        )
        
        with context:
            cmd = ListCommand()
            args = Mock()
            args.mtype = "material"
            
            exit_code = cmd.execute(args, context)
            assert exit_code == 0
```

---

## Phase 5: Testing Documentation and CI/CD

### Step 5.1: Test Documentation

Create `tests/README.md`:

```markdown
# Python-MagnetAPI Test Suite

## Overview

The test suite consists of two tiers:
- **Unit tests** (fast, mocked) - Test individual functions in isolation
- **Integration tests** (slow, real DB) - Test against actual test database

## Running Tests

### Quick Start (Unit Tests Only)

```bash
# Run all unit tests (fast, no external dependencies)
pytest -m unit

# Run with coverage
pytest -m unit --cov=python_magnetapi --cov-report=html
```

### Full Test Suite (Unit + Integration)

**Prerequisites:**
- Docker and docker-compose installed
- Test database running

**Start test database:**

```bash
cd tests/
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be ready
docker-compose -f docker-compose.test.yml ps
```

**Run tests:**

```bash
# Run all tests (unit + integration)
pytest

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest -v -m integration
```

**Stop test database:**

```bash
cd tests/
docker-compose -f docker-compose.test.yml down
```

## Test Organization

```
tests/
├── unit/              # Unit tests (mocked, fast)
├── integration/       # Integration tests (real DB, slow)
├── cli/              # CLI tests
├── fixtures/         # Test data factories and mocks
└── data/             # Test data files
```

## Writing Tests

### Unit Tests

Use mocking for external dependencies:

```python
import pytest
from unittest.mock import Mock

@pytest.mark.unit
def test_my_function(mock_session, api_config):
    # Setup mock
    mock_session.get.return_value = Mock(status_code=200)
    
    # Test function
    result = my_function(mock_session)
    
    # Assert
    assert result is not None
```

### Integration Tests

Use real test database:

```python
import pytest

@pytest.mark.integration
def test_full_workflow(test_db_session, clean_test_db):
    # Create test data
    obj_id = create_object(test_db_session)
    clean_test_db("object_type", obj_id)  # Register for cleanup
    
    # Test workflow
    result = process_object(test_db_session, obj_id)
    
    # Assert
    assert result is not None
```

## Environment Variables

```bash
# For integration tests
export TEST_MAGNETDB_API_SERVER=localhost
export TEST_MAGNETDB_API_PORT=8001
export TEST_MAGNETDB_API_KEY=test-integration-key-12345
```

## Coverage

Generate coverage report:

```bash
pytest --cov=python_magnetapi --cov-report=html --cov-report=term
open htmlcov/index.html
```

## CI/CD

Tests run automatically in GitHub Actions on push/PR.

See `.github/workflows/test.yml` for configuration.
```

### Step 5.2: GitHub Actions Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Test Suite

on:
  push:
    branches: [ main, refactor-* ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run unit tests with coverage
        run: |
          pytest -m unit --cov=python_magnetapi --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-${{ matrix.python-version }}
  
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    
    services:
      test-db:
        image: postgres:15
        env:
          POSTGRES_DB: magnetdb_test
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Wait for test API
        run: |
          # Add logic to start test API or wait for it
          sleep 10
      
      - name: Run integration tests
        env:
          TEST_MAGNETDB_API_SERVER: localhost
          TEST_MAGNETDB_API_PORT: 8001
          TEST_MAGNETDB_API_KEY: test-integration-key
        run: |
          pytest -m integration -v
```

---

## Success Criteria

✅ **Implementation Complete When:**
1. Comprehensive conftest.py with fixtures for both mock and real DB
2. Test data factories for all resource types
3. Mock response library for unit tests
4. Unit tests for all modules (≥80% coverage)
5. Integration tests with docker-compose test database
6. CLI tests (unit + integration)
7. Documentation for running tests
8. CI/CD integration (GitHub Actions)
9. Performance/slow tests marked and skippable
10. Test coverage reporting integrated

✅ **Quality Metrics:**
- Test coverage ≥ 80%
- Unit tests run in < 10 seconds
- Integration tests run in < 2 minutes
- All tests pass in CI/CD
- Zero flaky tests
- Clear test organization and naming

✅ **Test Categories:**
- Unit tests: ≥ 100 tests
- Integration tests: ≥ 30 tests
- CLI tests: ≥ 20 tests
- Computation tests: ≥ 10 tests

---

## Implementation Timeline

**Week 1: Foundation**
- Create conftest.py with fixtures
- Create factories and mock responses
- Setup docker-compose for test DB
- Write test documentation

**Week 2: Unit Tests**
- Unit tests for utils.py
- Unit tests for domain modules
- Unit tests for computation modules
- Achieve 60% coverage

**Week 3: Integration Tests**
- Integration tests for CRUD
- Integration tests for computation
- Integration tests for CLI
- Achieve 80% coverage

**Week 4: CI/CD & Polish**
- GitHub Actions workflow
- Coverage reporting
- Performance optimization
- Documentation finalization

---

## Notes for Implementation

1. **Start with infrastructure** - Get conftest.py and factories working first
2. **Mock early, mock often** - Unit tests should be fast and isolated
3. **Use parametrize** - Reduce code duplication with parametrized tests
4. **Clean up after integration tests** - Always use clean_test_db fixture
5. **Mark slow tests** - Use @pytest.mark.slow for tests > 5 seconds
6. **Document test data** - Explain what each fixture file represents

## Dependencies

**Should be done after:**
- Error Handling Framework (for proper exception testing)
- Type Hints (for better test type safety)

**Recommended tools:**
- pytest-cov (coverage)
- pytest-xdist (parallel testing)
- pytest-mock (mocking utilities)
- responses (HTTP mocking)

---

## Document Version

**Version**: 1.0  
**Created**: 2026-03-12  
**Task**: Test Suite Enhancement and Fixture Population  
**Priority**: Tier 2 (Code Quality & Maintainability)  
**Status**: Ready for implementation
