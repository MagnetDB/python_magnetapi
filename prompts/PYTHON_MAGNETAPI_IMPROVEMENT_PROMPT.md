# Python-MagnetAPI Module Improvement Framework

## Project Context

**Project**: python-magnetapi  
**Purpose**: Python library and CLI for interacting with MagnetDB (magnetic materials database)  
**Current Version**: 0.1.0  
**Python Support**: 3.11+  
**Collaborators**: Christophe Trophime, Remi Caumette  
**Active Branch**: refactor-claude  
**Status**: Active development with recent major improvements

### Recent Major Achievements (March 2026)

The refactor-claude branch has seen significant progress across multiple improvement tiers:

- **✅ Documentation Complete**: Full Sphinx documentation infrastructure with 1,500+ lines of comprehensive docs covering API, CLI, installation, testing, and contributing
- **✅ Performance Optimized**: hoop_stress.py rewritten for better performance, plus parallel processing version
- **✅ Modern Packaging**: Migrated to pure pyproject.toml (removed setup.py), proper PEP 517/518 compliance
- **✅ Enhanced Dependencies**: Integrated python3-magnetcooling and python3-magnettools
- **✅ Demo Scripts Added**: Two comprehensive demo scripts with 494 lines showcasing real-world usage
- **✅ README Expansion**: README expanded from ~50 to 314 lines with detailed installation and usage guides
- **✅ Testing Framework**: pytest properly configured with test paths and coverage settings  

### Core Characteristics
- MagnetDB API client library with CLI tools
- Domain-specific modules for magnetic materials, parts, magnets, sites, and records
- Comprehensive CLI with multiple subcommands and computation capabilities
- Modern packaging (pyproject.toml) with multi-package-manager support (pip, uv, Poetry)
- Debian packaging integration
- DevContainer development environment

---

## Improvement Methodology

### Principle: Incremental, Prioritized Modernization

We follow a systematic, step-by-step approach to improve the codebase:

1. **Start with specific, bounded improvements** (e.g., single module or feature)
2. **Maintain backward compatibility** unless explicitly modernizing packaging
3. **Prioritize packaging infrastructure over API stability**
4. **Document decisions and learnings** from each iteration
5. **Test thoroughly** before and after changes

### Priority Tiers

**Tier 1 (High Impact, Foundation)** - ✅ MOSTLY COMPLETE
- ✅ Version consistency across all configuration files
- ✅ Test suite setup (pytest configuration)
- ✅ Modern packaging (pyproject.toml migration)
- ⏳ Debian packaging modernization (debhelper, pybuild) - REMAINING
- ⏳ Error handling and exception framework - REMAINING
- ⏳ Type hints and static analysis setup - PARTIAL

**Tier 2 (Code Quality & Maintainability)** - 🛠️ IN PROGRESS
- ✅ Performance optimization (hoop_stress.py rewritten)
- ✅ Parallel processing capability added
- ✅ Modern library integration (python3-magnetcooling)
- ⏳ CLI module refactoring (reduce complexity from 900+ lines) - REMAINING
- ⏳ Test suite enhancement and fixture population - REMAINING
- ⏳ Logging implementation (replace print statements) - REMAINING
- ⏳ Configuration management (move hardcoded values) - REMAINING

**Tier 3 (Documentation & Developer Experience)** - ✅ COMPLETE
- ✅ Sphinx documentation generation
- ✅ API reference documentation
- ✅ Architecture and design documentation
- ✅ Contributing guidelines
- ✅ Demo scripts and examples

**Tier 4 (Polish & Advanced Features)** - 📅 FUTURE
- Performance optimization (further improvements)
- Advanced error recovery
- Interactive CLI improvements
- Plugin/extension system

---

## How to Use This Framework

### For Each Improvement Task

**1. Problem Definition**
```
When discussing an improvement, clearly state:
- What specific component/file is being improved?
- What is the current limitation or issue?
- What is the desired outcome?
- What is the scope (single file, module, cross-cutting)?
```

**2. Assessment**
```
Ask Claude to:
- Review current implementation
- Identify dependencies and side effects
- Suggest backward compatibility approach
- Assess test impact
```

**3. Implementation Planning**
```
Request Claude to:
- Show the modified code
- Explain changes and rationale
- Identify files to create/modify/remove
- Propose testing strategy
```

**4. Implementation**
```
Have Claude:
- Create/modify files
- Provide code with inline comments
- Generate tests or test fixtures
- Create summary of changes
```

**5. Verification**
```
Verify:
- No syntax errors
- Files are in correct locations
- Changes align with project structure
- Ready for integration/review
```

---

## Key Project Knowledge

### Project Structure
```
python-magnetapi/
├── pyproject.toml              # Build config (PEP 517/518 compliant)
├── debian/                      # Debian packaging
│   ├── control                  # Package metadata
│   ├── rules                    # Build rules
│   ├── changelog                # Version history
│   └── watch                    # Upstream version tracking
├── .devcontainer/               # Development environment
├── python_magnetapi/            # Main package
│   ├── __init__.py              # Package version management
│   ├── cli.py                   # CLI (900+ lines - refactor target)
│   ├── utils.py                 # API utility functions
│   ├── material.py              # Material domain module
│   ├── part.py                  # Part domain module
│   ├── magnet.py                # Magnet domain module
│   ├── site.py                  # Site domain module
│   ├── record.py                # Record domain module
│   ├── attachment.py            # Attachment handling
│   ├── geometry.py              # Geometry management
│   ├── inductances.py           # Computation module
│   ├── hoop_stress.py           # Computation module (optimized)
│   ├── hoop_stress_parallel.py  # Parallel computation module
│   └── flow_params.py           # Computation module (uses python3-magnetcooling)
├── tests/                       # Test suite
│   ├── test_list.py             # Comprehensive test class
│   └── *.dat, *.json            # Test fixtures
├── examples/                    # Demo scripts
│   ├── demo_part_history.py     # Part hoop stress history demo
│   ├── demo_part_site_records.py # Part site records demo
│   └── README-demos.md          # Demo documentation
├── docs/                        # Sphinx documentation (COMPLETE)
│   ├── conf.py                  # Sphinx configuration
│   ├── index.rst                # Documentation index
│   ├── cli.rst, usage.rst       # User guides
│   ├── installation.rst         # Installation guide
│   ├── testing.rst              # Testing guide
│   ├── contributing.rst         # Contributor guide
│   └── api/                     # API reference docs
├── old/                         # Legacy examples (informational)
└── README.md                    # Usage documentation (EXPANDED)
```

### Key Dependencies
- **Core**: requests, pandas, numpy, scipy, param, rich
- **Domain-specific**: python3-magnetsetup, python3-magnetcooling, python3-magnettools
- **Dev**: pytest, pytest-cov
- **Doc**: sphinx, sphinx-rtd-theme

### Version Management
- Single source of truth: `pyproject.toml` [project] → version
- `python_magnetapi/__init__.py` reads version from package metadata
- Debian changelog tracks releases
- setup.py removed (now uses modern PEP 517/518 build system)

---

## Common Improvement Scenarios

### Scenario A: Refactoring a Module
```
When improving a module like cli.py:
1. Request detailed review of current structure
2. Propose modular reorganization
3. Create new module structure
4. Migrate functionality piece by piece
5. Update imports and tests
6. Remove old files
```

### Scenario B: Adding Modern Python Features
```
When modernizing Python code:
1. Review Python 3.11+ features
2. Identify deprecations or opportunities
3. Implement type hints gradually
4. Add mypy configuration
5. Test with multiple Python versions
6. Update CI/CD if applicable
```

### Scenario C: Fixing Debian Packaging
```
When updating Debian packaging:
1. Review current standards (debhelper, etc.)
2. Check compatibility with target distros
3. Update debian/control and debian/rules
4. Test package building
5. Verify installation
6. Document changes in debian/changelog
```

### Scenario D: Enhancing Error Handling
```
When improving error handling:
1. Map current error scenarios
2. Define custom exceptions
3. Create exception hierarchy
4. Add error context and logging
5. Update CLI error messages
6. Add error handling tests
```

---

## Communication Pattern

### When Starting a Discussion

Include in your request to Claude:

```
IMPROVEMENT FOCUS: [Component/Feature Name]
PRIORITY TIER: [1-4]
SCOPE: [single file / module / cross-module]

CURRENT STATE:
- [What exists now]
- [Why it's problematic]

DESIRED STATE:
- [What should be achieved]
- [Success criteria]

CONSTRAINTS:
- [Backward compatibility needs]
- [Dependencies to consider]
- [Testing requirements]

NEXT STEPS:
- [What should Claude do first?]
```

### Example

```
IMPROVEMENT FOCUS: CLI Module Refactoring
PRIORITY TIER: 2
SCOPE: python_magnetapi/cli.py (module split)

CURRENT STATE:
- 900+ line monolithic cli.py
- Mixed argument parsing, business logic, and output
- Hard to test individual command handlers

DESIRED STATE:
- Modular CLI structure with handlers per subcommand
- Clear separation of concerns
- Each handler independently testable

CONSTRAINTS:
- Maintain exact same CLI interface for users
- No breaking changes to existing scripts
- Must work with current argument structure

NEXT STEPS:
- Analyze current cli.py structure
- Propose modular architecture
- Show what handlers structure would look like
```

---

## Tracking Progress

### Completed Improvements

#### Tier 1 (Foundation) - ✅ COMPLETED
- ✅ Version consistency modernization (pyproject.toml updates, improved __init__.py)
- ✅ Packaging modernization (removed setup.py, clean pyproject.toml with proper dependencies)
- ✅ Test framework setup (pytest configuration in pyproject.toml)

#### Tier 2 (Code Quality) - ✅ MAJOR PROGRESS
- ✅ Performance optimization of hoop_stress.py (rewritten: +760 lines improvements)
- ✅ Parallel processing capability added (hoop_stress_parallel.py with 484 lines)
- ✅ flow_params.py modernized to use python3-magnetcooling library

#### Tier 3 (Documentation) - ✅ COMPLETED
- ✅ Full Sphinx documentation structure created
- ✅ Comprehensive documentation added:
  - API reference documentation for all modules
  - CLI documentation (cli.rst)
  - Usage guide (usage.rst)
  - Installation guide (installation.rst)
  - Testing guide (testing.rst)
  - Contributing guide (contributing.rst)
  - Configuration guide (configuration.rst)
- ✅ README significantly expanded (from ~50 to 314 lines)
- ✅ Demo scripts added with documentation:
  - demo_part_history.py (225 lines)
  - demo_part_site_records.py (269 lines)
  - README-demos.md (210 lines)

#### Dependencies Updated - ✅ COMPLETED
- ✅ Added python3-magnetcooling
- ✅ Added python3-magnettools
- ✅ Updated numpy, scipy, and other core dependencies

### In-Progress Improvements
- Type hints and static analysis (partially implemented)
- Error handling framework (needs systematic implementation)

### Next Planned Improvements

#### Priority: Tier 1 Remaining
1. Debian packaging modernization (debhelper, pybuild)
2. Comprehensive error handling and exception framework
3. Type hints completion and mypy configuration

#### Priority: Tier 2 Remaining
4. CLI module refactoring (reduce complexity from 900+ lines)
5. Test suite enhancement and fixture population
6. Logging implementation (replace remaining print statements)
7. Configuration management (move hardcoded values)

#### Priority: Tier 4 (Future)
8. Interactive CLI improvements
9. Plugin/extension system

---

## Focus Areas for Next Phase

Based on the completed work, here are the recommended focus areas:

### High Priority (Tier 1 Completion)
1. **Debian Packaging Modernization**
   - Update debian/rules to use dh-python and pybuild
   - Ensure compatibility with modern Debian/Ubuntu standards
   - Test package building and installation

2. **Error Handling Framework**
   - Define custom exception hierarchy
   - Implement consistent error handling across all modules
   - Add contextual error messages
   - Create error handling tests

3. **Type Hints Completion**
   - Add type hints to all public APIs
   - Configure mypy for static analysis
   - Add py.typed marker
   - Gradually improve type coverage

### Medium Priority (Tier 2 Focus)
4. **CLI Module Refactoring**
   - Split 900+ line cli.py into modular handlers
   - Separate concerns (parsing, logic, output)
   - Maintain backward compatibility
   - Add per-handler tests

5. **Logging Framework**
   - Replace print statements with proper logging
   - Add configurable log levels
   - Support log file output
   - Add request/response logging for API calls

6. **Configuration Management**
   - Extract hardcoded values to configuration
   - Support environment variables
   - Add configuration file support
   - Document all configuration options

---

## Reference Documents

### Style & Quality Standards
- **Python Version**: 3.11+ (use modern syntax)
- **Type Hints**: Gradually add to all new/modified functions
- **Docstrings**: NumPy/Google style with type information
- **Testing**: pytest with descriptive test names
- **Linting**: Follow black formatting, flake8 compliance

### Configuration Files to Consider
- `pyproject.toml` [tool.pytest], [tool.coverage], [tool.mypy]
- `.pre-commit-config.yaml` (for automated checks)
- `.github/workflows/` (for CI/CD)

### Documentation Standards
- Inline comments for why, not what
- Docstrings for public APIs
- README sections for features
- CHANGELOG entries for releases

---

## Questions to Ask Claude

Use these types of questions systematically:

### Discovery
- "What are all the places this module is imported?"
- "What functions depend on this implementation?"
- "What would break if we changed this?"

### Design
- "What's the cleanest way to structure this?"
- "Are there design patterns that fit?"
- "How do we maintain backward compatibility?"

### Implementation
- "Can you implement this change?"
- "Where should this code live?"
- "How do we test this thoroughly?"

### Quality
- "What are potential edge cases?"
- "How could this fail in production?"
- "What error handling is needed?"

---

## Success Metrics

For each improvement cycle:

✅ **Code Quality**
- Type hints added or extended
- Cyclomatic complexity reduced
- Test coverage maintained or improved

✅ **Functionality**
- No breaking changes (or documented)
- All tests pass
- Backwards compatibility maintained

✅ **Documentation**
- Changes documented
- Usage examples updated if needed
- Architecture implications noted

✅ **Maintainability**
- Code is easier to understand
- Changes are easier to make
- Testing is easier to write

---

## Anti-Patterns to Avoid

❌ **Scope Creep**: Stay focused on one component per discussion  
❌ **Premature Optimization**: Fix clarity before performance  
❌ **Breaking Changes**: Maintain compatibility unless explicitly modernizing  
❌ **Incomplete Testing**: All changes need test coverage  
❌ **Undocumented Decisions**: Explain the "why" in comments/docstrings  

---

## Getting Started

**For the next discussion**, use this prompt as context and specify:

1. **What component** you want to improve (reference the structure above)
2. **What the current issue is** (reference the review findings)
3. **What success looks like** (be specific)
4. **Any constraints** I should know about

Example:

> "I want to improve error handling in the utils.py module. Currently, API errors are just printed. I want custom exceptions and better error context. This should maintain backward compatibility at the CLI level but can change internal APIs. Let's start by reviewing current error scenarios."

---

## Document Version

**Version**: 2.0  
**Created**: 2025-01-28  
**Last Updated**: 2026-03-12  
**Scope**: python-magnetapi package improvements  
**Major Changes**: Documented completion of Tier 1, 2, and 3 improvements; updated dependencies; added examples and documentation sections  

---

## Footer

This framework guides iterative, systematic improvements to python-magnetapi while maintaining code quality, backward compatibility, and clear communication. Each improvement builds on previous work, creating a cohesive modernization path.

**Next steps**: Reference this prompt in future discussions with Claude to ensure consistent methodology and context across all improvements.
