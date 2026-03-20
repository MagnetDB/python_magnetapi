# Tier 1 Debian Packaging Modernization Prompt

## IMPROVEMENT FOCUS: Debian Packaging Modernization
**PRIORITY TIER**: 1 (Foundation)
**SCOPE**: Debian packaging configuration files (debian/ directory)
**ESTIMATED COMPLEXITY**: Low — most modernization already done, cleanup remaining
**STATUS**: 🛠️ IN PROGRESS — foundation complete, cleanup needed

---

## CURRENT STATE (as of 2026-03-20)

### What Has Been Done ✅

- **debhelper-compat 13** — upgraded (was 12)
- **Standards-Version 4.7.0** — updated (was 4.5.1)
- **pybuild-plugin-pyproject** — explicitly declared in Build-Depends
- **`--with python3` removed** from debian/rules (no longer needed)
- **`override_dh_auto_test`** — skips tests with informative message
- **Runtime dependencies expanded** — requests, pandas, numpy, scipy, param, rich, magnetsetup, magnetcooling, magnettools all declared
- **Homepage field** — added to debian/control
- **Version 0.1.1-1** — debian/changelog up to date (CLI refactoring + packaging update documented)

### Current debian/control (actual file)

```
Source: python-magnetapi
Section: python
Priority: optional
Maintainer: Christophe Trophime <christophe.trophime@lncmi.cnrs.fr>
Build-Depends: debhelper-compat (= 13),
 dh-python,
 pybuild-plugin-pyproject,
 python3-setuptools,
 python3-all,
 pybuild-plugin-pyproject,          ← DUPLICATE
 python3-requests,
 python3-pandas,
 python3-numpy,
 python3-scipy,
 python3-param,
 python3-rich,
 python3-magnetsetup,
 python3-magnetcooling,
 python3-magnettools                ← MISSING TRAILING COMMA
 python3-rich                       ← DUPLICATE (no comma separator)
Standards-Version: 4.7.0
Homepage: https://github.com/MagnetDB/python_magnetapi
#Vcs-Browser: https://github.com/MagnetDB/python_magnetapi
#Vcs-Git: https://github.com/MagnetDB/python_magnetapi.git
#Testsuite: autopkgtest-pkg-python
Rules-Requires-Root: no
```

### Current debian/rules (actual file)

```makefile
#!/usr/bin/make -f

export PYBUILD_NAME=magnetapi

%:
	dh $@ --buildsystem=pybuild

# Sphinx build commented out (kept for reference)
#override_dh_auto_build: ...

override_dh_auto_test:
	@echo "Skipping tests - requires external MagnetDB API server"
	@echo "Set MAGNETDB_API_SERVER and MAGNETDB_API_KEY environment variables to run tests"
```

### Current debian/changelog (latest entry)

```
python-magnetapi (0.1.1-1) UNRELEASED; urgency=medium

  * rebuild for trixie
  * Refactor CLI module into modular package structure
  * Add type hints and docstrings throughout cli/ package
  * Fix logic bug in setup command available_models validation
  * Eliminate redundant API calls in view and compute commands
  * Update pyproject.toml to declare cli/ sub-packages
  * Modernize Debian packaging:
    - Update Standards-Version to 4.7.0

 -- Christophe Trophime <christophe.trophime@lncmi.cnrs.fr>  Thu, 20 Mar 2026 00:00:00 +0100
```

---

## REMAINING ISSUES

### 1. Duplicate and broken entries in debian/control Build-Depends

The current Build-Depends has two bugs that will cause `dpkg-buildpackage` to either warn or fail:

- `pybuild-plugin-pyproject` listed **twice**
- `python3-rich` listed **twice** (once inside the block with a comma, once at the end without a comma separator after `python3-magnettools`)
- Missing comma after `python3-magnettools` line (syntax error)

**Fix**: Clean up to a single, correctly comma-separated list.

### 2. `dh-python` still in Build-Depends

With `pybuild-plugin-pyproject` explicit and `--with python3` removed from rules, `dh-python` is no longer needed as a Build-Depends. It can be dropped.

### 3. `python3-setuptools` still in Build-Depends

`setup.py` was removed; the project is pure pyproject.toml. `python3-setuptools` is not needed at build time with `pybuild-plugin-pyproject`.

### 4. `Vcs-Browser` and `Vcs-Git` still commented out

These fields should be uncommented — the GitHub repository is public and the URL is known.

### 5. debian/changelog entry timestamp

The current entry has a placeholder timestamp (`00:00:00`). Should be set to the actual release time when releasing.

---

## DESIRED STATE

### Clean debian/control Build-Depends

```
Build-Depends: debhelper-compat (= 13),
 pybuild-plugin-pyproject,
 python3-all,
 python3-requests,
 python3-pandas,
 python3-numpy,
 python3-scipy,
 python3-param,
 python3-rich,
 python3-magnetsetup,
 python3-magnetcooling,
 python3-magnettools
```

Removed: `dh-python`, `python3-setuptools`, duplicates.

### Uncommented Vcs fields

```
Vcs-Browser: https://github.com/MagnetDB/python_magnetapi
Vcs-Git: https://github.com/MagnetDB/python_magnetapi.git
```

### debian/rules — no changes needed

The current rules file is correct and clean. `PYBUILD_NAME=magnetapi` is still needed so pybuild installs the package under the right name.

---

## CONSTRAINTS

### Must Maintain

- **Target distros**: Debian 12 (bookworm) and 13 (trixie)
- **Package naming**: `python3-magnetapi`
- **Runtime Depends**: All entries in the `Depends:` stanza are correct — do not remove
- **`override_dh_auto_test`**: Keep — tests need external API server

### Safe to Change

- Build-Depends (build-time only)
- Vcs fields (informational)
- Duplicate/broken entries cleanup

---

## IMPLEMENTATION STEPS

### Step 1: Fix debian/control

Remove duplicates, drop unneeded build-time deps, uncomment Vcs fields.

**Target debian/control:**

```
Source: python-magnetapi
Section: python
Priority: optional
Maintainer: Christophe Trophime <christophe.trophime@lncmi.cnrs.fr>
Build-Depends: debhelper-compat (= 13),
 pybuild-plugin-pyproject,
 python3-all,
 python3-requests,
 python3-pandas,
 python3-numpy,
 python3-scipy,
 python3-param,
 python3-rich,
 python3-magnetsetup,
 python3-magnetcooling,
 python3-magnettools
Standards-Version: 4.7.0
Homepage: https://github.com/MagnetDB/python_magnetapi
Vcs-Browser: https://github.com/MagnetDB/python_magnetapi
Vcs-Git: https://github.com/MagnetDB/python_magnetapi.git
Rules-Requires-Root: no

Package: python3-magnetapi
Architecture: all
Depends: ${python3:Depends}, ${misc:Depends},
 python3-requests,
 python3-pandas,
 python3-numpy,
 python3-scipy,
 python3-param,
 python3-rich,
 python3-magnetsetup,
 python3-magnetcooling,
 python3-magnettools
Suggests: python-magnetapi-doc
Description: Python library and CLI for interacting with MagnetDB
 Python MagnetAPI provides utilities to interact with MagnetDB, a database
 for magnetic materials, parts, magnets, and sites.
 .
 Features include:
  - Listing, viewing, creating, and deleting database objects
  - Setting up and running simulations
  - Computing derived quantities (inductances, flow parameters, hoop stress)
  - Post-processing simulation results
 .
 This package installs the library for Python 3.

Package: python-magnetapi-doc
Architecture: all
Section: doc
Depends: ${sphinxdoc:Depends}, ${misc:Depends}
Description: Python library and CLI for MagnetDB (documentation)
 Python MagnetAPI provides utilities to interact with MagnetDB, a database
 for materials, parts, magnets, and sites.
 .
 This package provides the common documentation including Sphinx-generated
 HTML documentation, API reference, and usage guides.
```

### Step 2: Update debian/changelog

Add new entry for the cleanup:

```
python-magnetapi (0.1.1-2) UNRELEASED; urgency=low

  * Fix Build-Depends: remove duplicate pybuild-plugin-pyproject and
    python3-rich entries; remove unused dh-python and python3-setuptools
  * Uncomment Vcs-Browser and Vcs-Git fields

 -- Christophe Trophime <christophe.trophime@lncmi.cnrs.fr>  DATE
```

Or fold into the existing `0.1.1-1 UNRELEASED` entry since it hasn't been released yet.

### Step 3: Verify Build

```bash
dpkg-buildpackage -F --no-sign
lintian -i ../*.deb
dpkg -c ../*.deb
python3 -m python_magnetapi.cli --help
```

---

## SUCCESS CRITERIA

- [x] debhelper-compat 13
- [x] pybuild-plugin-pyproject declared
- [x] Standards-Version 4.7.0
- [x] `--with python3` removed from rules
- [x] override_dh_auto_test skips with clear message
- [x] Version 0.1.1-1 in changelog
- [ ] Duplicate Build-Depends entries removed
- [ ] `dh-python` removed from Build-Depends
- [ ] `python3-setuptools` removed from Build-Depends
- [ ] Vcs-Browser / Vcs-Git uncommented
- [ ] Package builds without lintian errors
- [ ] `python -m python_magnetapi.cli --help` works after install

---

## DEBIAN COMPATIBILITY MATRIX

| Aspect | Debian 11 (bullseye) | Debian 12 (bookworm) | Debian 13 (trixie) |
|--------|----------------------|----------------------|-------------------|
| Python 3.11 | Backports only | Yes (default) | Yes |
| debhelper 13 | Yes | Yes | Yes |
| pybuild-plugin-pyproject | Yes | Yes | Yes |
| python3-magnetcooling | From repo | From repo | From repo |

**Primary target**: Debian 13 (trixie) — `UNRELEASED` in changelog reflects this.

---

## REFERENCE: CURRENT debian/ DIRECTORY STATE

```
debian/
├── control              # Needs duplicate/syntax cleanup
├── rules                # OK — clean and correct
├── changelog            # 0.1.1-1 UNRELEASED, needs timestamp fix on release
├── copyright            # OK
├── watch                # OK
├── patches/series       # OK (empty)
├── source/
│   ├── format           # "3.0 (quilt)" — OK
│   └── options          # egg-info ignore — OK
├── python-magnetapi-docs.docs  # Doc package — OK
├── README.Debian        # Informational — OK
└── README.source        # OK
```

---

## FOLLOW-UP ACTIONS (After This Cleanup)

Once debian/control is clean:
- Propagate custom exception hierarchy across domain modules (error handling)
- Complete type hints for utils.py, part.py, magnet.py, site.py, record.py
- Consider enabling `Testsuite: autopkgtest-pkg-python` once unit tests don't need external API

---

## Document Information

**Prompt Type**: Actionable Tier 1 Improvement
**Component**: Debian Packaging (debian/ directory)
**Scope**: Build configuration cleanup
**Estimated Time**: 30 minutes (cleanup + verify)
**Difficulty**: Low (configuration cleanup only)
**Risk Level**: Low
**Last Updated**: 2026-03-20
**Version**: 2.0
