# logrotate-ng

An improved logrotate, supporting recursion into directories.

Needs python 3.8+ due to the use of match/case and insertion ordered dicts.

## Directives supported

1. Action directives:
  create
  compress
  start
  prerotate
  postrotate
  preremove
  scratchdir

2. Criteria directives:
  recursive
  rotate
  maxsize
  maxage

3. Control flow directives:
  nosharedscripts
  sharedscripts
  endscript
  nomissingok

If any of the criteria isn't met, no rotation takes place.

## Changes from logrotate

No wildcard support for specifying target file (untested yet).

'compress' takes an optional extension paramter (e.g. '.tar.gz').

Currently, all compression happens with tar and an additional filter,
if compress is specified.

No global options supported yet.

## To do

Preserve file mtime across rotate (de-compress/rename/compress) cycle.
