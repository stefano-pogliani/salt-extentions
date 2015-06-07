# Plugin (install, enable, disable).
# Upgrade all.
# Uninstall.


def __virtual__():
  return "netbeans.exceptions" in __salt__


def _check_version(version):
  """Checks a version for validiti and converts latest to an actual version.

  version:
    The version to check.
  """
  # Update cache if needed.
  if _check_version._versions_cache is None:
    _check_version._versions_cache = __salt__["netbeans.list_versions"]()

  # Convert latest.
  if version == "latest":
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
