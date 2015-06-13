# -*- coding: utf-8 -*-
"""
State module to install Jenkins Plugins.
"""

# Import python modules.
from __future__ import absolute_import
import json
import logging
import os


# Import external modules.
import requests


log = logging.getLogger(__name__)


class PluginCache(object):
  """Manages the list of plugins available in the update center."""
  PLUGINS_URL="https://updates.jenkins-ci.org/update-center.json"

  def __init__(self):
    super(PluginCache, self).__init__()
    self._cache = None

  def _update(self, force=False):
    if force or self._cache is None:
      log.info("Downloading plugin information")
      # Fetch the JSONP file.
      data = requests.get(PluginCache.PLUGINS_URL).text
      data = data.split("\n")[1]
      self._cache = json.loads(data)["plugins"]

  def download(self, name, target):
    self._update()
    if name not in self._cache:
      raise Exception("Cannot download inexisting plugin")

    location = self._cache[name]["url"]
    log.debug("Downloading Jenkins Plugin {name} from {url}".format(
      name=name, url=location
    ))

    stream = requests.get(location, stream=True)
    with open(target, "wb") as f:
      for chunk in stream.iter_content(chunk_size=1024):
        if chunk: # filter out keep-alive new chunks
          f.write(chunk)
          f.flush()

  def get_dependencies(self, name):
    """
    :param str name: The name of the plugin to fetch the dependencies of.
    :returns: a list of required plugin names.
    """
    self._update()
    deps = self._cache.get(name, {}).get("dependencies", [])
    return [dep["name"] for dep in deps if not dep["optional"]]

  def get_latest_version(self, name):
    self._update()
    return self._cache.get(name, {}).get("version")


class PluginDownloader(object):
  """
  Downloads a plugin and it's dependencies,
  only if they are not installed or out of date.
  """
  def __init__(self, cache, home, update):
    self._cache  = cache
    self._home   = home
    self._update = update

  def _download_one(self, name, new, old):
    """Downloads one specific plugin.
    :returns: A tuple of result, comment.
      The result can be True on success, False on error or None for test.
      The comment is a string that describes what was done.
    """
    path = os.path.join(self._home, "plugins", name + ".hpi")
    if __opts__["test"]:
      return (
        None, "Would download {name}, version {new} to {path}"
        .format(name=name, new=new, path=path)
      )

    self._cache.download(name, path)
    if old is None:
      return (
        True, "Installed plugin {name} version {new}"
        .format(name=name, new=new)
      )

    return (
        True, "Updated plugin {name} from version {old} to version {new}"
        .format(name=name, new=new, old=old)
    )

  def _get_installed_version(self, name):
    """Finds the version of the plugin that is currently installed, if any.
    :param str name: The name of the plugin to check.
    :returns: The installed version or None if the plugin is not installed.
    """
    metadata_location = os.path.join(
        self._home, "plugins", name, "META-INF", "MANIFEST.MF"
    )
    if not os.path.exists(metadata_location):
      return None

    with open(metadata_location, "r") as metadata:
      version = [
          line for line in metadata.readlines()
          if line.startswith("Plugin-Version: ")
      ][0][15:].strip()
      log.debug("Detected installed version {version}".format(version=version))
      return version

  def _latest_version(self, name):
    """Fetches the latest version available for the given plugin.
    :param str name: The name of the plugin to fetch.
    :returns: The latest version if the plugin was found, None otherwise.
    """
    latest_version = self._cache.get_latest_version(name)
    if latest_version is None:
      log.error("Unable to find plugin {name}.".format(name=name))
      return None

    log.debug("Found plugin {name}, version {version}".format(
      name=name, version=latest_version
    ))
    return latest_version

  def _resolve_dependencies(self, name):
    """
    Lists all the plugin names that are,
    directly or indirectly, required.
    :param str name: The name of the plugin to fetch the dependencies of.
    :returns: a list of requred dependendency names.
    """
    package_deps  = self._cache.get_dependencies(name)
    resolved_deps = []
    seen_deps = set()

    # Resolve the recoursive dependencies.
    for dep in package_deps:
      for rec_dep in self._resolve_dependencies(dep):
        if rec_dep not in seen_deps:
          resolved_deps.append(rec_dep)
          seen_deps.add(rec_dep)

    # Assume no cycles are allowed in the update centers.
    resolved_deps.append(name)
    return resolved_deps

  def download(self, name):
    """Starts the download routine.
    :returns: the overall state of the operation, the comment and the changes made.
    """
    # Resolve dependencies.
    deps = self._resolve_dependencies(name)

    # Get latest and installed versions.
    changes = {}
    for dep in deps:
      new = self._cache.get_latest_version(dep)
      old = self._get_installed_version(dep)
      if new != old:
        changes[dep] = { 'new': new, 'old': old }

    # Download all missing or out of date plugins.
    comments = []
    result   = True
    for dep in deps:
      if dep not in changes:
        comments.append("Plugin {name} up to date.".format(name=dep))
        continue

      (res, comm) = self._download_one(
          dep, changes[dep]['new'], changes[dep]['old']
      )
      comments.append(comm)
      result = None if res is None else res and result

    # Build the result.
    return {
      "name":    name,
      "comment": "\n".join(comments),
      "changes": changes,
      "result":  result
    }


_cache = PluginCache()


def ensure(home="/var/lib/jenkins", name=None, update=True, **kwargs):
  downloader = PluginDownloader(_cache, home, update)
  return downloader.download(name)
