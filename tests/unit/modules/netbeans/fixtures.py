import os
import shutil
import tempfile

import pytest

def mock_install_tree(request, version, script=None):
  root = tempfile.mkdtemp()

  # When done, delete the entire thing.
  def cleanup():
    shutil.rmtree(root)
  request.addfinalizer(cleanup)

  # Create expected structure.
  bin    = os.path.join(root, "bin")
  locale = os.path.join(root, "nb", "core", "locale")
  bundle = os.path.join(root, "tmp", "org", "netbeans", "core", "startup")
  os.makedirs(bin)
  os.makedirs(locale)
  os.makedirs(bundle)

  # Create structure for version info.
  # -> org/netbeans/core/startup/Bundle_nb.properties
  info = open(os.path.join(bundle, "Bundle_nb.properties"), 'w')
  info.write("LBL_splash_window_title=Starting NetBeans IDE\n")
  info.write(
      "currentVersion=NetBeans IDE {0} (Build 2)\n".format(version)
  )
  info.close()

  # Create files
  # -> root/bin/netbeans*
  main = open(os.path.join(bin, "netbeans"), 'w')
  if script is None:
    main.write("#!/bin/sh\n")
    main.write("echo Testing script for Salt state\n")

  else:
    source = open(script)
    main.write(source.read())

  main.close()
  os.chmod(os.path.join(bin, "netbeans"), 0755)

  # Pack version structure in JAR.
  # -> root/nb/core/locale/core_nb.jar
  os.system("jar -cf '{target}' -C {tmp} org".format(
    target=os.path.join(locale, "core_nb.jar"),
    tmp=os.path.join(root, "tmp")
  ))

  # Remove structure for JAR.
  shutil.rmtree(os.path.join(root, "tmp"))
  return root


@pytest.fixture
def mock_salt_demo(request):
  return mock_install_tree(request, "salt-demo")


@pytest.fixture
def mock_salt_test(request):
  return mock_install_tree(request, "salt-test")


@pytest.fixture
def mock_salt_plugins(request):
  return mock_install_tree(
      request, "salt-plugins",
      "extentions/tests/unit/modules/netbeans/mock-bin"
  )
