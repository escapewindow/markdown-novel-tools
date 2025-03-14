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
- [ ] script(s) to convert from one source of truth to the other(s)
  - currently arcs, povs, scenes, all-in-one
  - copy from script bin, change from shell script to python
- [x] Table object is able to refer to columns by name rather than column number - done?
- [ ] Table schema
  - [ ] script to check/fix outline file(s)

# Manuscript
- [x] script to query scene frontmatter
  - [ ] if querying, e.g. tags, allow for returning a set of all tags, rather than a list of tags per scene
- [x] diff scene summary and outline summary
  - [x] script to check - unhardcode
- [x] script to replace frontmatter with outline + standard-formatted yaml
- [x] verify frontmatter schema
- [ ] fix frontmatter schema
  - [ ] including key order
- [x] function to walk the entire manuscript

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

# Config
- [ ] config file
  - [ ] config filename in .gitignore
  - [ ] example config
  - [ ] --config-path arg
  - [ ] search in pwd, base git dir, $XDG_CONFIG_HOME/md-novel, $HOME
  - [ ] get rid of all hardcodes - move to config?
- [x] move `frontmatter` from individual scripts to subcommands?
- [x] move `novel` from individual scripts to subcommands?

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
