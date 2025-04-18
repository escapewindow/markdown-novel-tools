# Wiki
- [ ] wiki frontmatter metadata
  - [ ] pronunciation frontmatter
    - [ ] build pronunciation guide from this
  - [ ] stylesheet metadata
    - [ ] build stylesheet from this
  - [ ] display format, allows for italics
  - [ ] go through manuscript to see which wiki pages to include
  - [ ] config - alphabetical order? order by appearance?
- [ ] wiki frontmatter schema
  - [ ] script to check/fix
- [ ] function to walk the entire wiki

# Outline
- [x] script(s) to convert from one source of truth to the other(s)
  - currently arcs, povs, scenes, all-in-one
  - copy from script bin, change from shell script to python
- [x] Table object is able to refer to columns by name rather than column number - done?
- [ ] Table schema
  - [ ] script to check/fix outline file(s)

# Conversion
- [x] conversion script in repo
  - [x] copy convert.py in, add to console scripts
- [x] epub support
  - [ ] example / custom css instead of hardcoding
  - [ ] cover, filename format in config
- [x] markdown support
- [x] pdf support
  - [ ] example / custom css instead of hardcoding
  - [x] allow for splitting manuscript into chunks, to avoid githug git-lfs issues after annotating by hand
- [x] odt manuscript submission format
  - [ ] data dir with reference.odt etc?
- [ ] docx manuscript submission format

# Tests
- [x] add github action on push to main
- [ ] 100% test coverage

# Documentation
- [ ] document the above
  - [ ] github wiki?

# Enhancements
- [ ] non-yaml frontmatter support
- [ ] script(s) to add to outline
  - [ ] differentiate between script-added beats and manually-sorted beats - script-added requires human intervention
- [ ] move contents of TODO.md to github issues
