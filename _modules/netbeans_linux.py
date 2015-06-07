import  logging
from os import chmod
from os import path
from os import stat
from os import walk
import re
import shutil
from stat import S_IXUSR
from stat import ST_MODE
import sys
import tempfile

import salt.exceptions


__virtualname__ = "netbeans"
log = logging.getLogger(__name__)
requests = None

try:
  import requests
except ImportError:
  log.debug("Unable to import requests module.", exc_info=True)


DEFAULT_LIST_URL = "http://download.netbeans.org/netbeans/"
BUNDLES_PATH = "/final/bundles/"
FILE_FORMAT = "/netbeans-{version}{features}{platform}"

VERSION_RE = re.compile(
    "\s*<[Aa]\s*[hH][rR][eE][fF]\s*=\s*['\"]([0-9][.0-9]*)/?['\"].*>.*"
)


class NoInstallFound(Exception):
  def __init__(self, version):
    super(NoInstallFound, self).__init__(
        "No install path found for version {0}".format(version)
    )


def __virtual__():
  if sys.platform != "linux" and sys.platform != "linux2":
    return False

  if requests is None:
    log.warn(
      "NetBeans execution module is not available because "
      "requests could not be imported."
    )
    return False

  # Check if jar command is available.
  return __virtualname__


def _pick_latest_version(versions):
  """Returns the higher version available in the given list of versions.

  versions:
    Array of strings with the availalbe versions.
  """
  def from_string(version):
    return tuple(int(part) for part in version.split('.'))

  def to_string(version):
    return '.'.join(str(part) for part in version)

  int_versions = [from_string(version) for version in versions]
  latest = max(int_versions)
  return to_string(latest)


def _get_installer_url(version, features='', url=None):
  """Returns the URL from which the installed can be downloaded.

  version:
    The vestion of NetBeans to download.

  features:
    The set of features to support such as cpp or php.
    Defaults to all featurs.

  url:
    The base URL to download from.
    Defaults to http://download.netbeans.org/netbeans
  """
  url = url or DEFAULT_LIST_URL
  template = "{url}/{version}/{subpath}/{filename}"
  filename = FILE_FORMAT.strip('/').format(
      features='-' + features if features else '',
      platform='-linux.sh',
      version=version
  )
  return template.format(
      filename=filename,
      subpath=BUNDLES_PATH.strip('/'),
      url=url.rstrip('/'),
      version=version
  )


def download_installer(version, features='', url=None):
  """Downloads the installer for the given version and returns a path to it.

  version:
    The version of NetBeans to install.

  features:
    The set of features to support such as cpp or php.
    Defaults to all featurs.

  url:
    The base URL to download from.
    Defaults to http://download.netbeans.org/netbeans
  """
  # Get tmp directory path.
  url = url or DEFAULT_LIST_URL
  tmp = tempfile.tempdir

  # Get filename.
  filename = FILE_FORMAT.strip('/').format(
      features='-' + features if features else '',
      platform='-linux.sh',
      version=version
  )
  full_url = _get_installer_url(versio, features=features, url=url)
  full_path = path.join(tmp, filename)

  # Download to {tmp}/{filename}
  response = requests.get(full_url, stream=True)
  with open(full_path, "wb") as f:
    for chunk in response.iter_content(chunk_size=1024): 
      if chunk: # filter out keep-alive new chunks
        f.write(chunk)
        f.flush()

  # Make executable.
  chmod(full_path, 0755)
  return full_path


def exceptions():
  """Returns a dicrionary with the exceptions exposed by this module."""
  return {
    "NoInstallFound": NoInstallFound
  }


def find_installation(version, root='/'):
  """Finds the installation path for the given version.

  version:
    The version to look for.

  root:
    The root path to scan for the installation path.
  """
  for (dir, _, _) in walk(root):
    # Look for bin and version information file.
    expected_bin    = path.join(dir, "bin", "netbeans")
    expected_locale = path.join(dir, "nb", "core", "locale", "core_nb.jar")

    # Move on if they either does not exist.
    if not path.isfile(expected_bin) or not path.isfile(expected_locale):
      continue

    # Check executable flag and version.
    perms = stat(expected_bin)[ST_MODE]
    if not (perms & S_IXUSR):
      continue

    # Check version.
    unpack_path = tempfile.mkdtemp()
    try:
      # Unpack splash tranlation file.
      unpack_code = __salt__["cmd.retcode"](
          "jar -xf {jar} org/netbeans/core/startup/Bundle_nb.properties"
          .format(jar=expected_locale), cwd=unpack_path
      )

      # Is the JAR archive valid? 
      if unpack_code != 0:
        continue

      # Read the file looking for the right line.
      splash_strings = path.join(
          unpack_path, "org", "netbeans", "core", "startup",
          "Bundle_nb.properties"
      )
      found_version = None
      version_re = re.compile(
          r"currentVersion=NetBeans IDE ([^ ]+).*"
      )
      with open(splash_strings) as f:
        for line in f:
          match = version_re.match(line)
          if match:
            found_version = match.group(1)
            break

      # Now we can compare the required value to the found one.
      if version != found_version:
        continue

    finally:
      #  Clean up temp dir.
      shutil.rmtree(unpack_path)

    # Found a valid path.
    return dir
  # Could not find a valid path.
  raise NoInstallFound(version)


def list_versions(url=None):
  """Returns the list of versions of NetBeans that were found.

  url:
    The URL to download the list of versions from.
    Defaults to http://download.netbeans.org/netbeans
  """
  # Get the HTML list.
  url = url or DEFAULT_LIST_URL
  response = requests.get(url)
  if response.status_code != 200:
    raise SaltException(
        "Unable to download NetBeans versions. URL: {}".format(url)
    )

  # Process each line.
  versions = []
  for line in response.iter_lines():
    match = VERSION_RE.match(line)
    if match:
      versions.append(match.group(1))
      
  return versions
