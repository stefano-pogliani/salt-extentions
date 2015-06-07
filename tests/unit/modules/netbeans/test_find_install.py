import imp
import os
import shutil
import tempfile

from salt.modules import cmdmod

import pytest

netbeans = imp.load_source("make", "extentions/_modules/netbeans_linux.py")


def mock_install_tree(request, version):
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
  main.write("#!/bin/sh\n")
  main.write("echo Testing script for Salt state\n")
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
def mock_salt_test(request):
  return mock_install_tree(request, "salt-test")


@pytest.fixture
def mock_salt_demo(request):
  return mock_install_tree(request, "salt-demo")


def test_none_found():
  pytest.raises(
    Exception, netbeans.find_installation, "salt-missing",
    root="/path/that/should/not/exist/on/any/reasonable/system"
  )


def test_found_one(mock_salt_test):
  netbeans.__salt__ = {"cmd.retcode": cmdmod.retcode}
  path = netbeans.find_installation("salt-test", root=tempfile.tempdir)
  assert path == mock_salt_test


def test_found_right_version(mock_salt_test, mock_salt_demo):
  netbeans.__salt__ = {"cmd.retcode": cmdmod.retcode}
  path = netbeans.find_installation("salt-test", root=tempfile.tempdir)
  assert path == mock_salt_test
