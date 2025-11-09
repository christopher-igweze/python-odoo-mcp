# Contributing to Python Odoo MCP

Thank you for contributing! This document outlines our development workflow and testing requirements.

## Development Workflow

We follow a **micro-commit philosophy** with atomic, focused changes:

### 1. Micro-Commits

Each commit should be a single, focused change that can be understood in isolation.

**Format:** Use glassbear emoji + conventional commit style

```bash
# Examples
git commit -m "✨ feat(auth): add encrypted API key generation"
git commit -m "🐛 fix(scope): handle wildcard permission override"
git commit -m "🧪 test(encryption): add credential roundtrip tests"
git commit -m "📝 docs(readme): update n8n usage section"
```

**Emoji Reference:**
- ✨ `feat` - New feature
- 🐛 `fix` - Bug fix
- 🧪 `test` - Test additions/updates
- 📝 `docs` - Documentation
- 🔧 `chore` - Build, config, dependencies
- ♻️ `refactor` - Code restructuring
- 🎨 `style` - Code formatting
- 🔒 `security` - Security improvements

### 2. Branch Strategy

- Create feature branches from `main`: `feature/your-feature-name`
- Make micro-commits to your feature branch
- Push regularly (every 3-5 commits or hourly)
- Create a pull request when complete
- Get explicit approval before merging to main

### 3. Testing Requirements

All code changes must include tests. We enforce:

- **Coverage threshold:** 75% (currently working toward this)
- **Test organization:**
  - Unit tests in `tests/unit/`
  - Integration tests in `tests/integration/`
  - E2E tests in `tests/e2e/` (for live deployments)

### 4. Running Tests Locally

Before pushing, ensure all tests pass:

```bash
# Install development dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Run specific tests
pytest tests/unit/test_encryption.py -v
pytest -k "scope_validator" -v

# Run by marker
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
```

## Test Structure

### Unit Tests (`tests/unit/`)

Test individual components in isolation, no external dependencies.

**When to write:**
- Configuration management
- Encryption/decryption logic
- Scope parsing and validation
- Core business logic

**Example:**

```python
import pytest
from src.auth.scope_validator import ScopeValidator

class TestScopeValidator:
    def test_parse_single_model_with_permissions(self):
        """Test parsing single model scope"""
        validator = ScopeValidator("res.partner:RWD")
        assert validator.can_call("res.partner", "search")
        assert validator.can_call("res.partner", "create")
        assert validator.can_call("res.partner", "unlink")

    def test_parse_invalid_scope_raises_error(self):
        """Test invalid scope syntax raises error"""
        with pytest.raises(ScopeValidationError):
            ScopeValidator("invalid_scope")
```

### Integration Tests (`tests/integration/`)

Test multiple components working together, with app instance but no external services.

**When to write:**
- API endpoint behavior
- Authentication workflows
- Tool invocation (without actual Odoo calls)

**Example:**

```python
import pytest
from starlette.testclient import TestClient
from src.server import app

class TestAuthEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_generate_api_key(self, client):
        """Test API key generation endpoint"""
        payload = {
            "url": "https://test.odoo.com",
            "database": "test_db",
            "username": "user@test.com",
            "password": "password123",
            "scope": "res.partner:RWD"
        }
        response = client.post("/auth/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert "user" in data
```

### E2E Tests (`tests/e2e/`)

Test against live deployments (optional, for coverage measurement).

**When to use:**
- Measuring coverage of tool implementations
- Testing against real Odoo instances
- Integration testing with external systems

**Note:** These are temporary and should be deleted after use per clean slate requirement.

## GitHub Actions CI

The project runs automated tests on:

- Push to `main`, `develop`, `feature/*` branches
- Pull requests to `main` and `develop`

**What runs:**
- Unit and integration tests (Python 3.9, 3.10, 3.11)
- Coverage report generation
- Code quality checks (flake8, black, isort)
- Security checks (bandit, safety)

**Before PR:**
1. All tests must pass locally
2. Coverage must not decrease
3. No security warnings from bandit/safety

## Pull Request Process

1. **Create feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make micro-commits:**
   ```bash
   git commit -m "✨ feat(scope): add wildcard support"
   git commit -m "🧪 test(scope): add wildcard tests"
   git push origin feature/your-feature-name
   ```

3. **Push every 3-5 commits:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create PR when complete**
   - Include clear description of changes
   - Link related issues
   - Ensure all tests pass in CI

5. **Wait for approval**
   - Don't merge without explicit confirmation
   - Address review feedback with new commits
   - Ensure CI passes after each update

6. **Merge to main**
   - Squash or rebase if preferred
   - Delete feature branch after merge

## Code Style

We follow PEP 8 with automatic formatting:

- **Black** for code formatting (line length: 88)
- **isort** for import sorting
- **flake8** for linting

Run before committing:

```bash
black src tests
isort src tests
flake8 src tests
```

## Documentation

- Update README.md for user-facing changes
- Update CONTRIBUTING.md for process changes
- Add docstrings to new functions/classes
- Document any new environment variables

Example docstring:

```python
def encrypt_credentials(self, credentials: Credentials) -> str:
    """Encrypt credentials to encrypted API key.

    Args:
        credentials: Odoo credentials with url, database, username, password, scope

    Returns:
        Encrypted API key string

    Raises:
        ValueError: If credentials are invalid
    """
```

## Security

- Never commit real credentials or secrets
- Use `.env` files for local development (in `.gitignore`)
- Store `ENCRYPTION_KEY` as environment variable
- Follow OWASP guidelines for authentication/encryption

## Coverage Monitoring with Codecov

We use [Codecov](https://codecov.io/) to track test coverage over time and monitor code quality.

### Setting Up Codecov (Maintainers Only)

1. **Sign up at Codecov:**
   - Go to https://codecov.io/
   - Sign in with GitHub account
   - Grant access to `christopher-igweze/python-odoo-mcp` repository
   - Codecov will automatically sync and start receiving coverage reports

2. **Get Upload Token (Recommended):**
   - Navigate to repository settings in Codecov dashboard
   - Copy the "Repository Upload Token"
   - Add to GitHub as a Secret:
     1. Go to repository Settings → Secrets and variables → Actions
     2. Click "New repository secret"
     3. Name: `CODECOV_TOKEN`
     4. Value: (paste token from Codecov)
   - GitHub Actions will use this token to securely upload coverage

3. **Verify Integration:**
   - Push a commit to main or a feature branch
   - GitHub Actions should run tests and upload coverage to Codecov
   - Check Codecov dashboard to see coverage report
   - PRs will show coverage impact comments

### Understanding Coverage Reports

**What coverage measures:**
- **Line coverage:** % of source code lines executed during tests
- **Branch coverage:** All if/else paths tested
- **Files:** Which files have gaps and need more tests

**Reading reports:**
- Red/uncovered lines = not tested
- Green/covered lines = tested during test runs
- Trending graphs show if coverage is improving

**Coverage impact on PRs:**
- Shows lines added/removed/changed
- Indicates if PR improves or decreases coverage
- Comments on PR with summary

### For Contributors

When submitting PRs:
1. Ensure new code has corresponding tests
2. Aim for 80%+ coverage on files you modify
3. Check local coverage: `pytest --cov=src --cov-report=html`
4. Codecov will comment automatically if coverage drops

## Need Help?

- Check existing issues and PRs
- Review test examples in `tests/`
- Read function docstrings in `src/`
- Ask in GitHub discussions

Thank you for contributing to Python Odoo MCP!
