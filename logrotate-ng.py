#!/usr/bin/python3

""" logrotate-ng.py

An improved logrotate, supporting recursion into directories.
Needs python 3.8+ due to the use of match/case and insertion ordered dicts.

Supports the following logrotate directives

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

Changes from logrotate:
  No wildcard support for specifying target file (untested yet)
  'compress' takes an optional extension paramter (e.g. '.tar.gz')
  Currently, all compression happens with tar and an additional filter,
  if compress is specified.
  No global options supported yet

To do:
  Preserve file mtime across rotate (de-compress/rename/compress) cycle

"""

import sys, os, re, time
from calendar import monthrange

def debug(*args):
  if os.environ.get('DEBUG'):
    print(*args)

def parse_conf(f):
  comment = re.compile('^#')
  path = re.compile('(/\S+)')
  statement = re.compile(r'^\s*(?P<directive>[^\n\s=]+)(?:(=|\s+)*)(?P<params>\S*.*)')
  start = re.compile(r'.*\s*{')
  end = re.compile('}')
  entries = []
  paths = []
  entry = None
  for line in f:
    if comment.match(line):
      print(f'Ignoring comment: {line.rstrip()}')
      continue
    if start.match(line):
      entry = {}
      entry['paths'] = paths
      debug(f'Opening stanza for {",".join(entry["paths"])}')
    if path.match(line):
      paths.extend(path.findall(line))
      debug('Paths:', *paths)
      continue
    if end.match(line):
      debug(f'Closing stanza for {",".join(entry["paths"])}')
      entries.append(entry)
      entry = None
      paths = []
      continue
    if statement.match(line):
      if not entry:
        print('No paths provided ahead of stanza')
        return
      m = re.search(statement, line)
      directive, params = m.group('directive'), m.group('params')
      debug(f'Directive: {directive}; params: {params}')
      match directive:
        case 'prerotate'|'postrotate'|'preremove':
          entry[directive] = []
          continue
      last_directive = list(entry.keys())[-1]
      match last_directive:
        case 'prerotate'|'postrotate'|'preremove':
          if directive != 'endscript':
            entry[last_directive].append(f'{directive} {params}'.rstrip())
          continue
      entry[directive] = params
  return entries

def parse_size(input):
  p = re.compile(r'\s*([0-9.]+)([a-zA-Z]?)')
  m = p.search(input)
  names = [ 'kilo', 'mega', 'giga', 'tera' ]
  i = 0
  mult = 1
  if m.group(2):
    for u, i in zip([l[0] for l in names], range(1, len(units) + 1)):
      if m.group(2) == u:
        break
      else:
        mult *= 1024
  return int(m.group(1)), mult, names[i] + 'byte' + ('s' if (abs(int(m.group(1)) > 1)) else '')

def parse_timeunit(input):
  p = re.compile(r'\s*([0-9.]+)([a-zA-Z]?)')
  m = p.search(input)
  units = 'smhdMY'
  values = [1, 60, 60, 24, 31, 12, 365]
  default = 'minute'
  names = [default, 'second', 'minute', 'hour', 'day', 'month', 'year']
  mult = 1
  i = 1
  if m.group(2):
    for u, i in zip(list(units), range(1, len(units) + 1)):
      if m.group(2) == u:
        break
      else:
        mult *= values[i]
  return int(m.group(1)), mult, names[i] + ('s' if (abs(int(m.group(1)) > 1)) else '')

def parse_ordinal(n):
  n = abs(int(n))
  match (n % 10):
    case 1 if (n < 10) or (n % 100) != 11:
      u = 'st'
    case 2 if (n < 10) or (n % 100) != 12:
      u = 'nd'
    case 3 if (n < 10) or (n % 100) != 13:
      u = 'rd'
    case _:
      u = 'th'
  return u

def parse_tar_filter(ext):
  p = re.compile(r'.([a-zA-Z0-9]+$)')
  m = p.search(ext)
  ext_opts = { 'bz2': 'j', 'gz': 'z', 'xz': 'J', 'tar': '' }
  if m and m.group(1) in ext_opts:
    return ext_opts[m.group(1)]
  exit(f'{ext} unsupported as compress extension')

def run_tar(type, file, ext, entry):
  opt = parse_tar_filter(ext)
  dirname = os.path.dirname(file)
  basename = os.path.basename(file)
  dir = entry['scratchdir'] if 'scratchdir' in entry.keys() else dirname
  if type:
    text = f'de-compressing {file}{ext} to {dir}/{basename}'
    cmd = f'tar --warning=none -C {dir} -x{opt}f {file}{ext} 2>/dev/null'
  else:
    text = f'compressing {dir}/{basename} to {file}{ext}'
    cmd = f'tar --warning=none --remove-files -C {dir} -c{opt}f {dirname}/{basename}{ext} {basename} 2>/dev/null'
  print(text)
  debug('# ' + cmd)
  os.system(cmd)

def decompress_file(file, ext, entry):
  run_tar(True, file, ext, entry)

def compress_file(file, ext, entry):
  run_tar(False, file, ext, entry)

def run_cmds(entry, directive):
  directives = entry.keys()
  if directive in directives:
    for cmd in entry[directive]:
      debug('# ' + cmd)
      os.system(cmd)
  if 'sharedscripts' in directives and 'nosharedscripts' not in directives:
    entry[directive] = None

frequencies = {
  'hourly'  : 60 * 60,
  'daily'   : 24 * 60 * 60,
  'weekly'  : 7,
  'monthly' : 1,
  'yearly'  : 1,
}

def process_time(path, entry):
  age = 1
  frequencies.keys()
  for freq in frequencies.keys():
    if freq in entry.keys():
      localtime = localtime or time.localtime()
      field_offset = 4
      first_field = field_offset - list(frequencies.keys()).index(freq)
    else:
      continue
    debug(f'freq = {freq}, first_field = {first_field}')
    temp_time[first_field:6] = (1, 1, 0, 0, 0)[first_field:6]
    time_ref = time.mktime(tuple(temp_time))
    debug(f'freq = {freq}, time_ref = {time_ref}, first_field = {first_field}, temp_time = {temp_time}')
    match (freq):
      case 'monthly':
        age = age * monthrange(localtime.tm_year, localtime.tm_mon)[1]
      case 'yearly':
        age = age * (366 if (monthrange(localtime.tm_year, 2)[1] == 28) else 365)
      case _:
        age = age * frequencies[freq]
    if (diff := time_ref - os.lstat(path).st_mtime) < age:
      flag = False
    print(f'{path} {flag} older than a {freq[0:-2].replace("i", "y")} {os.lstat(path).st_mtime:.0f} {time_ref:.0f} (by {diff:.2f} seconds)')
    age = frequencies['daily']

def process_maxsize(path, entry):
  size, mult, sizeunit = parse_size(entry['maxsize'])
  print(f'{path} ',end='')
  if (diff := os.lstat(path).st_size - size * mult) <= 0:
    flag = False
  print(('larg' if diff > 0 else 'small') + f'er than {size} {sizeunit} (by {abs(diff)} byte' + ('s' if diff != 1 else '') + ')')

def process_maxage(path, entry):
  age, mult, timeframe = parse_timeunit(entry['maxage'])
  mult = 3600 * 24 if not mult else mult
  if (diff := time.time() - os.lstat(path).st_mtime) <= age * mult:
    flag = False
  print(f'{path} not older than {age} {timeframe} ({diff:.2f} seconds)')

def process_rotate(path, entry, compress):
  start = int(entry['start']) if 'start' in entry.keys() else 1
  rotate = int(entry['rotate'])
  if start - rotate:
    run_cmds(entry, 'prerotate')
  debug(f'Rotation extensions from range {start}-{rotate}')
  length = len(str(rotate))
  base = path + '.'
  for r in range(rotate, start, -1):
    prior = str(r - 1).zfill(length)
    prior_file = base + prior
    if os.path.lexists(prior_file + compress):
      if compress:
        decompress_file(prior_file, compress, entry)
    if os.path.lexists(prior_file):
      cur = str(r).zfill(length)
      cur_file = base + cur
      print(f'back-renaming {prior_file} -> {cur_file}')
      os.rename(prior_file, cur_file)
      if compress:
        compress_file(cur_file, compress, entry)
  next_file = base + str(start).zfill(length)
  if os.path.lexists(next_file):
    print(f'overwriting {next_file} by {path}')
  print(f'renaming {path} -> {next_file}')
  os.rename(path, next_file)
  if compress:
    compress_file(next_file, compress, entry)
  run_cmds(entry, 'postrotate')

def process_delete(path, entry):
  run_cmds(entry, 'preremove')
  print(f'deleting {path}')
  os.remove(path)

def process_create(path):
  if not os.path.exists(path):
    with open(path, encoding="utf-8", mode='w'):
      print(f'created {path}')
  else:
    print(f'{path} exists, not creating')

def process_file(path, entry):
  flag = True
  directives = entry.keys()
  compress = (entry['compress'] if entry['compress'] else '.tar.gz') if 'compress' in directives else ''
  p = re.compile(r'(.*)[.]([0-9]+)(' + compress + ')?$')
  if (m := p.match(path)):
    ordinal = parse_ordinal(m.group(2))
    debug(f'{path} after {m.group(2)}{ordinal} rotation of {m.group(1)}, ignoring')
    return
  else:
    debug(f'{path} is a primary file')
  process_time(path, entry)
  if 'maxage' in directives:
    process_maxage(path, entry)
  if 'maxsize' in directives:
    process_maxsize(path, entry)
  if not flag:
    return
  if 'rotate' in directives:
    process_rotate(path, entry, compress)
  else:
    process_delete(path, entry)
  if 'create' in directives:
    process_create(path)

def process_path(path, entry):
  directives = entry.keys()
  if os.path.isdir(path):
    if 'recursive' in directives:
      debug(f'Recursing into {path}')
      [process_path(f[0] + '/' + g, entry) for f in os.walk(path) for g in reversed(sorted(f[2])) if not f[1] and g]
    else:
      print(f'{path} is a directory but recursion is not enabled')
    return
  else:
    debug(f'Found file {path}')
    process_file(path, entry)

def process_entry(entry):
  for p in entry['paths']:
    if os.path.lexists(p):
      process_path(p, entry)
    else:
      if 'nomissingok' in entry.keys():
        debug(f'{p} not found, not processing further entries')
        return
      else:
        debug(f'Skipping non-existent {p}')

def process_conf(conf):
  for entry in conf:
    process_entry(entry)

if sys.version_info.major < 3 or sys.version_info.minor < 8:
  exit(f'{sys.argv[0]} needs at least python 3.8')
if len(sys.argv) > 1:
  file = sys.argv[1]
  if os.path.exists(file):
    with open(file, encoding="utf-8") as f:
      parsed = parse_conf(f)
  else:
    exit(f'File {file} does not exist')
else:
  exit('{} requires an argument'.format(sys.argv[0]))

process_conf(parsed)
