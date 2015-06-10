# Plugin (install, enable, disable).
# Upgrade all.
# Uninstall.
import logging
from os import path

log = logging.getLogger(__name__)


def __virtual__():
  return "netbeans.exceptions" in __salt__


def _check_version(version):
  """Checks a version for validiti and converts latest to an actual version.

  version:
    The version to check.
  """
  # Update cache if needed.
  if _check_version._versions_cache is None:
    log.debug("Loading versions cache ...")
    _check_version._versions_cache = __salt__["netbeans.list_versions"]()

  # Convert latest.
  if version is None or version == "latest":
    return __salt__["netbeans.pick_latest_version"](
        _check_version._versions_cache
    )

  # Check if version is available.
  if version not in _check_version._versions_cache:
    return None
  return version

# Module level version cache.
_check_version._versions_cache = None


def install(name, version, features='', source_url=None):
  """Installs the named version of NetBeans on the system.

  name:
    The name of the task, not currently used.

  version:
    The version of NetbBeans to install.
    Currently supports only versions 7.3 and above.
    This is due to the naming of the install file in versions below 7.3.

  features:
    Determines which installer to download based on features.
    If left empty (which is the default) the installer for all features
    will be downloaded.
    Otherwise the options are:
      - cpp
      - javaee
      - javase
      - php

  source_url:
    Remote URL from which the installer will be downloaded.
  """
  result = {
    "changes": None,
    "comment": "",
    "name":    name,
    "result":  False
  }

  # Resolve version.
  resolved_version = _check_version(version)
  if resolved_version is not None:
    version = resolved_version

  # Look for existing installation.
  # Look even for invalid versions because it could be a
  # locally installed version that is not available on the
  # specified source.
  exceptions = __salt__["netbeans.exceptions"]()
  try:
    found = __salt__["netbeans.find_installation"](version)
    result["comment"] = "NetBeans {ver} already installed at {path}.".format(
        path=found, ver=version
    )
    result["result"]  = True
    return result
  
  except exceptions["NoInstallFound"]:
    pass

  # Check if the version is valid.
  if resolved_version is None:
    result["comment"] = "Invalid version {ver}.".format(ver=version)
    result["result"]  = False
    return result

  # Download installer.
  installer = None
  try:
    installer = __salt__["netbeans.download_installer"](
        version, features=features, url=source_url
    )

  except Exception as ex:
    result["comment"] = "Could not fetch installer: {0}".format(ex)
    result["result"]  = False
    return result

  # Bail now on test.
  if __opts__["test"]:
    result["comment"] = "Installer downloaded to {path}.".format(path=installer)
    result["result"]  = None
    result["changes"] = {"new": version}
    return result

  # Install in silent mode.
  install_code = __salt__["cmd.retcode"](installer + " --silent")
  if install_code != 0:
    result["comment"] = "Installation failed with code {}".format(install_code)
    result["result"]  = False
    return result

  # Find the installation path again.
  install_path = __salt__["netbeans.find_installation"](version)
  result["comment"] = "Installed version {ver} to {path}.".format(
      path=install_path, ver=version
  )
  result["result"]  = True
  result["changes"] = {"new": version}
  return result


def pinstall(name=None, version=None):
  """Install and enable a plugin.

  name:
    The name of the plugin to install.

  version:
    The version of NetBeans to install the plugin for.
    Defaults to latest available.
  """
  result = {
    "changes": None,
    "comment": "",
    "name":    name,
    "result":  False
  }

  # Resolve version.
  version = _check_version(version)
  if version is None:
    result["comment"] = "Invalid version {} specified.".format(version)
    result["result"]  = False
    return result

  # Look for the plugin state.
  exceptions   = __salt__["netbeans.exceptions"]()
  plugin_state = None
  plugin_version = None
  try:
    (state, version) = __salt__["netbeans.find_plugin"](version, name)
    plugin_state   = state
    plugin_version = version

  except exceptions["NoInstallFound"]:
    result["comment"] = "NetBeans {} not installed.".format(version)
    result["result"]  = False
    return result

  except exceptions["NoPluginFound"]:
    result["comment"] = "Plugin {} not found for NetBeans {}.".format(
        name, version
    )
    result["result"] = False
    return result

  # If up to date and installed done.
  if plugin_state == "enabled":
    result["comment"] = "Plugin already installed and enabled."
    result["result"]  = True

  # Get ready to run the command.
  args    = []
  comment = None
  fail_comment = None
  test_comment = None

  # If not enabled prepare for enable.
  if plugin_state == "installed":
    args.extend(["--enable", name])
    comment = "Plugin enabled."
    fail_comment = "Could not enable plugin."
    test_comment = "Plugin will be enabled."
    result["changes"] = { "state": {
      "new": "enabled",
      "old": "installed"
    } }

  # If not up to date prepare for update.
  if plugin_state == "update":
    args.extend(["--update", name])
    comment = "Plugin updated."
    fail_comment = "Could not update plugin."
    test_comment = "Plugin will be updated."
    result["changes"] = { "version": {
      "new": plugin_version[1],
      "old": plugin_version[0]
    } }

  # If not installed prepare for install.
  if plugin_state == "available":
    args.extend(["--install", name])
    comment = "Plugin installed."
    fail_comment = "Could not install plugin."
    test_comment = "Plugin will be installed."
    result["changes"] = {
      "state": {
        "new": "enabled",
        "old": "available"
      },
      "version": {
        "new": plugin_version,
        "old": None
      }
    }

  if not args:
    result["comment"] = "Unrecognised state {} for plugin.".format(
        plugin_state
    )
    result["result"]  = False
    return result

  # If __opts__["test"] return now.
  if __opts__["test"]:
    result["comment"] = test_comment
    result["result"]  = None
    return result

  # Run the command.
  full_args = [
    "--locale", "en",
    "--nogui",
    "--nosplash",
    "--modules"
  ]
  full_args.extend(args)
  output = __salt__["cmd.retcode"](bin + " " + " ".join(full_args))


def start(name, version=None, args=None):
  """Ensures that NetBeans is running.
  The command line interface is very limited and has the
  huge problem that it actually starts the IDE even when
  module commands are specified.

  If the IDE **is not** running, when the command is completed,
  the process will stay alive in full IDE mode.
  If the IDE **is** already running, when the command is completed,
  the process will terminate.

  This state should be used as a prerequisite of all other
  states so that the IDE is guaranteed to be running.

  version:
    The version of the IDE to run.

  args:
    List of arguments to pass to the command line.
  """
  result = {
    "changes": None,
    "comment": "",
    "name":    name,
    "result":  False
  }

  # Resolve version.
  version = _check_version(version)
  if version is None:
    result["comment"] = "Invalid version {} specified.".format(version)
    result["result"]  = False
    return result

  # Look for the plugin state.
  exceptions = __salt__["netbeans.exceptions"]()
  try:
    nb_path = __salt__["netbeans.find_installation"](version)
    bin  = path.join(nb_path, "bin", "netbeans")
    args = ["--locale", "en", "--nogui", "--nosplash"]
    code = __salt__["cmd.shell"]("nohup " + bin + " " + " ".join(args))

    if code == 0:
      result["comment"] = "Started NetBeans in silent mode."
      result["result"]  = True

    else:
      result["comment"] = "Could not start NetBeans in silent mode."
      result["result"]  = False
    return result

  except exceptions["NoInstallFound"]:
    result["comment"] = "NetBeans {} not installed.".format(version)
    result["result"]  = False
    return result


def stop(name, version=None):
  """
  """
  result = {
    "changes": None,
    "comment": "",
    "name":    name,
    "result":  False
  }

  # Resolve version.
  version = _check_version(version)
  if version is None:
    result["comment"] = "Invalid version {} specified.".format(version)
    result["result"]  = False
    return result

  # Look for the plugin state.
  exceptions   = __salt__["netbeans.exceptions"]()
  try:
    nb_path = __salt__["netbeans.find_installation"](version)
    native  = path.join(nb_path, "platform", "lib")
    cmd = (
        "ps -ef | grep '" + native +
        "' | grep -v grep | awk '{ print $2 }' | xargs kill"
    )
    __salt__["cmd.shell"](cmd)

  except exceptions["NoInstallFound"]:
    result["comment"] = "NetBeans {} not installed.".format(version)
    result["result"]  = False
    return result
