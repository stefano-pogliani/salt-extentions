# Plugin (install, enable, disable).
# Upgrade all.
# Uninstall.


def __virtual__():
  return "netbeans.find_installation" in __salt__


def install(name, features='', source_url=None):
  """Installs the named version of NetBeans on the system.

  name:
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
  # Resolve 'latest' version.

  # Look for existing installation.
  try:
    found = __salt__["netbeans.find_installation"](version)
    result["comment"] = "NetBeans {ver} already installed at {path}.".format(
        path=found, ver=version
    )
    result["result"]  = True
    return result
  
  except __salt__["netbeans.NoInstallFound"]:
    pass

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
    result["changes"] = {"new": name}
    return result

  # Install in silent mode.
  install_code = __salt__["cmdmod.retcode"](installer + " --silent")
  if install_code != 0:
    result["comment"] = "Installation failed with code {}".format(install_code)
    result["result"]  = False
    return result

  # Find the installation path again.
  install_path = __salt__["netbeans.find_installation"](version)
  result["comment"] = "Installed version {ver} to {path}.".format(
      path=install_path, ver=name
  )
  result["result"]  = True
  result["changes"] = {"new": name}
  return result
