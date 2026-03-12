# Tier 1 Debian Packaging Modernization Prompt

## IMPROVEMENT FOCUS: Debian Packaging Modernization
**PRIORITY TIER**: 1 (Foundation)  
**SCOPE**: Debian packaging configuration files (debian/ directory)  
**ESTIMATED COMPLEXITY**: Medium  
**BLOCKING OTHER WORK**: Yes - packaging consistency affects distribution  

---

## CURRENT STATE

### What Exists Now

The python-magnetapi package currently uses:
- **debhelper-compat version 12** (outdated, released 2019)
- **dh-python** in Build-Depends (legacy)
- **pybuild** without explicit pybuild-plugin-pyproject
- **Standards-Version 4.5.1** (from 2020)
- **Manual build rules** with custom PYBUILD_NAME export

### Current debian/control
```
Build-Depends: debhelper-compat (= 12),
 dh-python,
 python3-setuptools,
 python3-all,
 python3-magnetrun,
 python3-magnetsetup,
 python3-rich
Standards-Version: 4.5.1
```

### Current debian/rules
```makefile
export PYBUILD_NAME=magnetapi
%:
	dh $@ --with python3 --buildsystem=pybuild
```

### Why This Is Problematic

1. **Outdated debhelper**: Version 12 (2019) is 5+ years old
   - Missing security patches
   - No support for modern Python packaging (PEP 517/518)
   - Tools expect debhelper >= 13

2. **Implicit pybuild behavior**: 
   - pybuild-plugin-pyproject is not explicitly declared
   - Risk of fallback to legacy setup.py behavior (which we removed)
   - Unpredictable behavior across different Debian versions

3. **Legacy dh-python dependency**:
   - Not needed when using pybuild with pyproject.toml
   - Can be removed to simplify dependencies

4. **Outdated Standards-Version**:
   - Current Debian standard is 4.7.0+ (as of 2024)
   - Signals outdated packaging practices

5. **Version consistency**:
   - debian/changelog shows version 0.0.1 series
   - pyproject.toml has version 0.1.0
   - Inconsistency that must be fixed

---

## DESIRED STATE

### What We Want to Achieve

A modernized, standards-compliant Debian package that:

1. **Uses current debhelper** (13 or 14)
   - Modern PEP 517/518 support
   - Security patches included
   - Proper pyproject.toml handling

2. **Explicitly uses pybuild-plugin-pyproject**
   - No ambiguity about build backend
   - Guaranteed to use PEP 517/518 build system
   - Works across Debian 11, 12, 13+ consistently

3. **Removes legacy dependencies**
   - No dh-python (handled by pybuild-plugin-pyproject)
   - Cleaner, more minimal Build-Depends

4. **Updates Standards-Version**
   - Current standard compliance (4.7.0)
   - Signals actively maintained package

5. **Resolves version consistency**
   - Single source of truth: pyproject.toml
   - debian/changelog next entry will bump to 0.1.0
   - Consistent across all configuration

### Success Criteria

✅ debian/control updated with modern build requirements  
✅ debian/rules simplified and modernized  
✅ pybuild-plugin-pyproject explicitly declared and working  
✅ Standards-Version updated to current (4.7.0)  
✅ dh-python removed from dependencies  
✅ debhelper-compat updated to 13 or 14  
✅ Version consistency between pyproject.toml and debian/changelog  
✅ Debian package builds successfully on Debian 12/13  
✅ Package is installable and functional after build  
✅ All changes documented in debian/changelog  

---

## CONSTRAINTS

### Must Maintain

- **Backward compatibility**: Package must still install on Debian 11+ (bullseye or later)
- **Functionality**: No changes to what the package does
- **Target distros**: Works on Debian bookworm (12) and later
- **Build isolation**: Clean builds without residual files

### Cannot Break

- Existing CI/CD pipelines (if any)
- Package naming (python3-magnetapi)
- Installation paths
- Dependencies on python3-magnetrun, python3-magnetsetup, python3-rich
- Functionality of installed scripts and modules

### Safe to Change

- Build system declarations
- Build-time dependencies (not runtime)
- Standards compliance version
- Helper tool versions
- debian/rules implementation details
- debian/control Build-Depends

---

## TECHNICAL DETAILS TO REVIEW

### Key Questions to Answer

1. **Python version support**: pyproject.toml requires Python 3.11+
   - Does Debian 12 default Python support 3.11? (Yes - python3 is 3.11.2)
   - Should we add explicit python3.11-* build-depends? (No - python3-all covers it)

2. **Runtime vs Build dependencies**:
   - runtime: python3-magnetrun, python3-magnetsetup, python3-rich
   - build-time: Should we add python3-dev? (Not needed with pybuild)
   - build-time: Do we need python3-magnetrun, python3-magnetsetup at build time? (Check if needed for tests)

3. **Test execution**:
   - Current debian/rules has: `override_dh_auto_test: echo "skip dh_auto_test"`
   - Should we keep skipping tests? (Depends on CI/CD strategy)
   - Tests need MAGNETDB_API_SERVER to run (external dependency)

4. **Documentation build**:
   - Sphinx is optional (in [project.optional-dependencies])
   - No documentation is currently built
   - Is this intentional or can we skip it? (Skip for now - keep Tier 3)

### Debian Compatibility Matrix

| Aspect | Debian 11 (bullseye) | Debian 12 (bookworm) | Debian 13 (trixie) |
|--------|----------------------|----------------------|-------------------|
| Python 3.11 | Available (backports) | Yes (default) | Yes |
| debhelper 13 | Available | Yes | Yes |
| debhelper 14 | Not by default | Available | Yes |
| pybuild-plugin-pyproject | Available | Yes | Yes |

**Recommendation**: Target debhelper 13 (works on Debian 11+, good compromise)

---

## FILES TO MODIFY

### Primary Changes

**1. debian/control** - CRITICAL
- Update Build-Depends
- Update Standards-Version
- Verify Depends list

**2. debian/rules** - IMPORTANT
- Simplify if possible
- Ensure consistent with modern pybuild

**3. debian/changelog** - REQUIRED
- Add entry for next version (0.1.0-1)
- Document Debian packaging modernization

### Secondary Review (No changes needed unless issues found)

- debian/copyright - verify formatting
- debian/watch - verify it still works
- debian/source/format - should stay "3.0 (quilt)"
- debian/source/options - OK as-is (egg-info ignore)

---

## IMPLEMENTATION STEPS

### Phase 1: Analysis & Planning
```
1. Review current Build-Depends and their purposes
2. Verify pybuild-plugin-pyproject availability on target distros
3. Check if any build-time dependencies are actually needed
4. Confirm test execution requirements
```

### Phase 2: Update debian/control
```
Suggested changes:
- Build-Depends: debhelper-compat (= 13),
                 pybuild-plugin-pyproject,
                 python3-all,
                 python3-magnetrun,
                 python3-magnetsetup,
                 python3-rich
- Standards-Version: 4.7.0
- Add Vcs-* fields (GitHub URLs)
```

### Phase 3: Update debian/rules
```
Simplify to:
#!/usr/bin/make -f

%:
	dh $@ --buildsystem=pybuild

override_dh_auto_test:
	echo "Skipping tests - requires external MagnetDB API server"
```

### Phase 4: Update debian/changelog
```
Add entry:
python-magnetapi (0.1.0-1) UNRELEASED; urgency=medium

  * Modernize Debian packaging
  * Update debhelper-compat to 13
  * Use pybuild-plugin-pyproject explicitly
  * Update Standards-Version to 4.7.0
  * Remove legacy dh-python dependency

 -- Christophe Trophime <christophe.trophime@lncmi.cnrs.fr>  YYYY-MM-DD HH:MM:SS +0200
```

### Phase 5: Verify Build
```
Test build in clean environment:
- dpkg-buildpackage -F
- Check for lintian warnings
- Verify package contents
- Verify installation works
```

---

## POTENTIAL ISSUES & MITIGATIONS

### Issue 1: pybuild-plugin-pyproject Not Available
**Risk**: Low (available in Debian 11+)  
**Mitigation**: Falls back to auto-detection, but explicit is better  
**Action**: Explicitly declare it

### Issue 2: Build Fails Due to Missing Imports
**Risk**: Medium (if test imports are needed at build time)  
**Mitigation**: Keep runtime deps in Build-Depends if needed  
**Action**: Try minimal first, add back if build fails

### Issue 3: lintian Warnings
**Risk**: Medium (new debhelper version may have new checks)  
**Mitigation**: Review warnings, they're often informational  
**Action**: Fix only blockers, document intentional overrides

### Issue 4: Version Mismatch in debian/changelog
**Risk**: High (already present)  
**Mitigation**: Next entry should be 0.1.0-1 to match pyproject.toml  
**Action**: Set correctly in new changelog entry

---

## TESTING STRATEGY

### Before Changes
```bash
# Build current package
dpkg-buildpackage -F
dpkg -l | grep python-magnetapi
python3 -c "import python_magnetapi; print(python_magnetapi.__version__)"
```

### After Changes
```bash
# Build modernized package
dpkg-buildpackage -F
lintian -i *.deb
dpkg -l | grep python-magnetapi
python3 -c "import python_magnetapi; print(python_magnetapi.__version__)"
python3 -m python_magnetapi.cli --help
```

### Verification Checklist
- [ ] Package builds without errors
- [ ] No critical lintian warnings
- [ ] Package installs correctly
- [ ] Imported modules work
- [ ] CLI is accessible
- [ ] Version is correct (0.1.0)
- [ ] Maintainer info is correct

---

## REFERENCE: CURRENT debian/ DIRECTORY STATE

```
debian/
├── control              # Package metadata (needs update)
├── rules                # Build rules (can simplify)
├── changelog            # Version history (needs new entry)
├── copyright            # License info (OK)
├── watch                # Upstream tracking (OK)
├── source/
│   ├── format           # "3.0 (quilt)" (OK)
│   └── options          # egg-info ignore (OK)
├── python-magnetapi-docs.docs  # Doc package (OK)
└── README.Debian        # Release notes (informational)
```

---

## WHAT CLAUDE SHOULD DO

1. **Review current debian/control and debian/rules** - identify all legacy elements
2. **Propose updated versions** - show what each file should look like
3. **Explain each change** - why we're making it
4. **Show the diff** - before/after comparison
5. **Suggest verification steps** - how to test the changes work
6. **Provide updated debian/changelog entry** - with proper format and message

---

## EXPECTED OUTCOME

After this improvement:

**Version Control**
- Consistent version across pyproject.toml, __init__.py, and debian/changelog
- Next release will be 0.1.0-1

**Build System**
- Modern debhelper (13) with pyproject.toml native support
- Explicit pybuild-plugin-pyproject usage
- Simplified debian/rules
- Removed legacy dependencies

**Compliance**
- Standards-Version 4.7.0 (current)
- No breaking changes
- Works on Debian 12+ (primary target)
- Backward compatible with Debian 11 if needed

**Maintainability**
- Clearer what the build system expects
- Less mystery around tool versions
- Easier to update in future
- Signals actively maintained project

---

## FOLLOW-UP ACTIONS (After This Tier 1 Task)

Once Debian packaging is modernized:
- Tier 1 Task 2: Version consistency across all files (if not done here)
- Tier 1 Task 3: Error handling framework in python_magnetapi/
- Tier 1 Task 4: Type hints and mypy configuration

---

## Document Information

**Prompt Type**: Actionable Tier 1 Improvement  
**Component**: Debian Packaging (debian/ directory)  
**Scope**: Build configuration modernization  
**Estimated Time**: 1-2 hours (analysis + implementation + testing)  
**Difficulty**: Medium (configuration work, not code)  
**Risk Level**: Low (non-core code changes)  

---

## How to Start

**Use this prompt by saying:**

> "I want to modernize the Debian packaging for python-magnetapi to Tier 1 standards. Please review the current debian/control and debian/rules files and propose a modernized version using debhelper-compat (= 13) and explicit pybuild-plugin-pyproject support. Then show me what the updated files should look like and how to verify they work."

**Or provide this entire prompt and say:**

> "Here's a detailed prompt for Debian packaging modernization. Please follow this structure: first analyze the current state, then propose changes, then show the implementation, and finally suggest verification steps."

---

## Key Learnings from Similar Projects

From python-magnetsetup and python-magnetrun (sibling projects):
- Both use similar architecture (pyproject.toml + Debian packaging)
- Similar runtime dependencies on param, rich, etc.
- Could align packaging approaches across projects
- devcontainer setup has proven effective

---

## Questions to Clarify (If Needed)

Before starting:

1. **Do you want Python 3.11-specific package support?**
   - Currently Python 3.11+ general, should we specify python3.11?
   - Answer: No - let distro default python3 handle it

2. **Should documentation generation be added?**
   - Sphinx is optional, not currently used
   - Answer: No - that's Tier 3, keep packaging minimal

3. **What's the target distribution list?**
   - Primary: Debian 12 (bookworm)
   - Support: Debian 11+ if possible
   - Answer: Use debhelper 13 as compromise

4. **Should we add GitHub VCS fields?**
   - Would help users find repository
   - Not breaking, good practice
   - Answer: Yes, add Vcs-Browser and Vcs-Git

---

**Ready to proceed? Provide this prompt to Claude and request the implementation!**
