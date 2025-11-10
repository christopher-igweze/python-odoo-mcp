# Contributing to Python Odoo MCP Server

Thank you for your interest in contributing! This document covers development setup, testing, and our contribution workflow.

## Development Setup

### Local Environment

```bash
# Clone and install
git clone https://github.com/christopher-igweze/python-odoo-mcp.git
cd python-odoo-mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run Server Locally

```bash
python -m src.server
# Server starts on http://localhost:3000
```

### Docker Setup

```bash
docker-compose up --build
# Server starts on http://localhost:3000
```

## Testing

### Running Tests

The project includes comprehensive unit and integration tests using pytest:

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_encryption.py -v

# Run tests matching pattern
pytest -k "scope_validator" -v

# Run with markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow         # Slow/e2e tests
```

### Test Structure

```
tests/
├── unit/                           # Unit tests (no external dependencies)
│   ├── test_config.py             # Config management & encryption key validation
│   ├── test_encryption.py         # Credential encryption/decryption
│   ├── test_scope_validator.py    # Scope parsing and permission checking
│   ├── test_odoo_client.py        # OdooClient read/write/delete operations
│   ├── test_connection_pool.py    # Connection pooling and caching
│   ├── test_connection_manager.py # Connection authentication and pooling
│   ├── test_header_parser.py      # X-Auth-Credentials header parsing
│   └── test_tools.py              # Tool implementations with mocking
├── integration/                    # Integration tests (with app instance)
│   ├── test_auth_endpoints.py     # /auth/generate and /auth/validate
│   ├── test_health.py             # Health check endpoints
│   └── test_tools_endpoints.py    # /tools/list and /tools/call
└── conftest.py                    # Shared pytest fixtures
```

### Test Coverage

**Current Status:**
- Overall coverage: **75.37%** ✅ (target: 75%+)
- 142 tests passing
- High coverage areas:
  - Authentication & encryption: 89%
  - Scope validation: 89%
  - Connection pool: 100%
  - Header parser: 100%
- Lower coverage areas:
  - Tool error paths: 82%
  - Odoo client integration: 88%
  - Server endpoints: 30% (requires live Odoo)

**Coverage Monitoring:**

This project uses [Codecov](https://codecov.io/) for continuous coverage tracking:

- View detailed coverage dashboard: https://codecov.io/gh/christopher-igweze/python-odoo-mcp
- Coverage reports generated automatically on every push via GitHub Actions
- Pull requests show coverage impact

**Understanding Coverage Reports:**
1. **Line Coverage** - Percentage of source code lines executed during tests
2. **Branch Coverage** - All code paths (if/else) tested
3. **Uncovered Lines** - Listed with file paths for targeting improvement
4. **Trending** - See if coverage increases or decreases with each commit

**Generate Local Reports:**

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# View in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Testing Health Check

```bash
curl http://localhost:3000/health
```

### List Available Tools

```bash
curl -X POST http://localhost:3000/tools/list
```

### Testing Scripts

We provide a test script for quick integration testing:

```bash
./test_server.sh
```

## Development Workflow

### Micro-Commit Philosophy

We follow the **micro-commit philosophy** - each commit should be a single, focused change:

```bash
# ✅ GOOD: One focused change
git commit -m "🔧 fix(scope): handle wildcard permission override"

# ✅ GOOD: Another focused change
git commit -m "✨ feat(tools): add search_count operation"

# ❌ AVOID: Multiple unrelated changes
git commit -m "🔧 fix multiple bugs and refactor"
```

### Commit Message Format

Use the glassbear emoji + conventional commit format:

```
{emoji} {type}({scope}): {description}
```

**Emoji Guide:**
- ✨ `feat` - New feature
- 🐛 `fix` - Bug fix
- 🧪 `test` - Tests or test improvements
- 📝 `docs` - Documentation changes
- 🔧 `chore` - Configuration, dependencies, non-code changes
- 🎨 `style` - Code style/formatting (no logic change)
- ♻️ `refactor` - Code refactoring (no feature/fix)

**Examples:**
```
✨ feat(scope): add support for explicit permission denial
🐛 fix(connection): handle disconnection in pool
🧪 test(tools): add comprehensive error handling tests
📝 docs(readme): update n8n integration guide
🔧 chore(deps): upgrade cryptography library
```

### Code Style

```bash
# Check formatting
black --check src tests

# Format code
isort src tests
black src tests

# All together
./test_server.sh  # runs checks before tests
```

### Creating a Pull Request

1. **Branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make focused commits:**
   ```bash
   git commit -m "✨ feat(feature): implement thing"
   git commit -m "🧪 test(feature): add tests"
   ```

3. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **PR should include:**
   - Clear description of what changed and why
   - Link to any related issues
   - Test coverage for new code
   - Updated documentation if needed

### Coverage Requirements for Contributors

When implementing new features:

1. **Write tests alongside implementation**
   - Don't write code first, add tests later
   - Use TDD approach when possible

2. **Aim for 80%+ coverage on new code**
   - Run `pytest --cov` to see your coverage
   - Target overall 75%+ coverage maintenance

3. **Before pushing:**
   ```bash
   pytest tests/ --cov=src --cov-report=term-missing
   # Check that your new code is tested
   ```

4. **After pushing:**
   - Codecov will comment on your PR with coverage impact
   - Address any coverage regressions before merging

## Adding New Features

### Step 1: Plan the Feature
- Create an issue describing the feature
- Discuss API design if adding endpoints
- Consider test approach before coding

### Step 2: Implement with Tests

```bash
# Feature branch
git checkout -b feature/my-new-feature

# Write test first (TDD approach)
# File: tests/unit/test_my_feature.py
class TestMyFeature:
    def test_something(self):
        assert True

# Implement the feature
# File: src/my_module.py

# Run tests to verify
pytest tests/unit/test_my_feature.py -v

# Check coverage
pytest --cov=src tests/unit/test_my_feature.py
```

### Step 3: Document

```bash
# Update README if adding public features
# Update docstrings in code

git commit -m "📝 docs(readme): document new feature"
```

### Step 4: Submit PR

Include in PR description:
- What does this add?
- Why was it needed?
- How does someone use it?
- Any breaking changes?

## Debugging

### Enable Debug Logging

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Run server
python -m src.server
```

### Test a Specific Component

```bash
# Test only authentication
pytest tests/unit/test_encryption.py -v

# Test with print statements
pytest tests/unit/test_something.py -v -s
```

### Debug with pdb

```python
# In your test or code
import pdb; pdb.set_trace()

# Then run pytest with -s flag
pytest tests/ -s
```

## Common Issues

### Tests Fail: "No module named 'src'"

**Solution:** Make sure you're running pytest from the repo root:
```bash
cd /path/to/python-odoo-mcp
pytest tests/
```

### Coverage Not Generated

**Solution:** Make sure pytest-cov is installed:
```bash
pip install pytest-cov
```

### Port 3000 Already in Use

**Solution:** Kill the process or use different port:
```bash
# Kill process using port 3000
lsof -i :3000
kill -9 <PID>

# Or use different port
PORT=3001 python -m src.server
```

## Performance Testing

We track performance metrics. To test local performance:

```bash
# Time test execution
time pytest tests/integration/

# Profile specific test
pytest tests/integration/test_tools_endpoints.py --profile

# Check connection pool efficiency
pytest tests/unit/test_connection_pool.py -v -s
```

## Getting Help

- **Questions?** Open an issue with `[question]` label
- **Bug reports?** Include: Python version, error message, steps to reproduce
- **Feature requests?** Describe use case and expected behavior

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to make Python Odoo MCP Server better! 🙏
