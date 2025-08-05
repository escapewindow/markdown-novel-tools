# Wiki
- [ ] wiki frontmatter metadata
  - [ ] Style Sheet metadata
    - [ ] define
    - [ ] add to wiki
    - [ ] add script to scrape the metadata
    - [ ] generate Style Sheet from this
  - [ ] visual style, allows for italics, e.g. sonyu -> *sonyu*
  - [ ] wiki frontmatter schema
    - [ ] define the schema
    - [ ] `frontmatter check`, `frontmatter update`, `novel lint` support for non-manuscript files

# Outline
- [ ] Table schema
  - [ ] Define the schema
  - [ ] script to check/fix outline file(s)
- [ ] outline convert tags and aliases
- [ ] Add book num to scene number, allow for creating multi-book outlines

# Tests
- [ ] 100% test coverage
- [ ] Automate the tests in GitHub actions

# Documentation
- [ ] Documentation

# Conversion
- [X] epub backmatter
- [X] epub ' - ' to emdash
- [ ] tempdir for conversion
  - [ ] start using a tempdir to avoid polluting the artifact dir
  - [ ] this could be specifiable to see the intermediate artifacts if wanted
- [ ] _write_to_file_helper to preserve headers if exists

# Enhancements
- [ ] script(s) to add to outline
  - [ ] differentiate between script-added beats and manually-sorted beats - script-added requires human intervention
