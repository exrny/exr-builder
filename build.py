import sys, re, os
from vulcan.builder import task
import sh

@task()
def apidoc():
  """
  Generate API documentation using epydoc.
  """
  sh.epydoc("--config", "epydoc.config", _out=sys.stdout, _err_to_out=True)


@task()
def validate():
      sh.pycodestyle('vulcan', '--max-line-length=110', _out=sys.stdout, _err_to_out=True)

    
@task(validate)
def test(*args):
  """
  Run unit tests.
  """
  pyTest = sh.Command("py.test")
  pyTest(args, _out=sys.stdout, _err_to_out=True)

@task()
def check_uncommited():
  result = sh.git('status', '--porcelain')
  if result:
    raise Exception('There are uncommited files')

@task()
def generate_rst():    
  sh.pandoc('-f', 'markdown', '-t', 'rst', '-o', 'README.rst', 'README.md', _out=sys.stdout, _err_to_out=True)
  sh.pandoc('-f', 'markdown', '-t', 'rst', '-o', 'CHANGES.rst', 'CHANGES.md', _out=sys.stdout, _err_to_out=True)
  filenames_diff = sh.git('diff', '--name-only')
  if 'README.rst' in filenames_diff or 'CHANGES.rst' in filenames_diff:
    sh.git('commit', 'README.rst', 'CHANGES.rst', '-m', 'Autogenerated from markdown files', _out=sys.stdout, _err_to_out=True)

@task()
def update_version(ver = None):
  with open('vulcan/meta_builder.py', 'r') as f:
    file_str = f.read()

  if not ver:
    regexp = re.compile('__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*')
    m = regexp.search(file_str)
    if m:
      ver = m.group(1)
  
  minor_ver = int(ver[ver.rfind('.')+1:])
  ver = '{}.{}'.format(ver[:ver.rfind('.')], minor_ver+1)

  file_str = re.sub(
      '__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*',
      '__version__ = "{}"\n'.format(ver),
      file_str)

  with open('vulcan/meta_builder.py', 'w') as f:
    f.write(file_str)

  sh.git('commit', 'vulcan/meta_builder.py', '-m', 'Version updated to {}'.format(ver), _out=sys.stdout, _err_to_out=True)

@task()
def create_tag():
  with open('vulcan/meta_builder.py', 'r') as f:
    file_str = f.read()
  regexp = re.compile('__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*')
  m = regexp.search(file_str)
  if m:
    ver = m.group(1)
  else:
    raise "Can't find/parse current version in './vulcan/meta_builder.py'"

  sh.git.tag('-a', '-m', 'Tagging version {}'.format(ver), ver, _out=sys.stdout, _err_to_out=True)

@task()
def push():
  sh.git.push('--verbose', _out=sys.stdout, _err_to_out=True)
  sh.git.push('--tags', '--verbose', _out=sys.stdout, _err_to_out=True)

@task(test)
def release(ver = None):
  check_uncommited()
  update_version(ver)
  generate_rst()
  create_tag()
  push()

@task(test)
def pypi():
  sh.python('setup.py', 'sdist', _out=sys.stdout, _err_to_out=True)
  args = ['upload']
  
  travis_pull_request = (os.environ.get('TRAVIS_PULL_REQUEST', 'false') == 'true')
  travis_tag = os.environ.get('TRAVIS_TAG', False)
  
  if not travis_pull_request and travis_tag:
    args.append('--repository-url')
    args.append('https://upload.pypi.org/legacy/')
  else:
    args.append('--skip-existing')
    args.append('--repository-url')
    args.append('https://test.pypi.org/legacy/')

  args.append('dist/vulcan-builder-*')

  sh.twine(args, _out=sys.stdout, _err_to_out=True)

__DEFAULT__ = test
