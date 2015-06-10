import sys
import tempfile

sys.path.append("extentions/_modules")
sys.path.append("extentions")

from salt.modules import cmdmod
import netbeans_linux as netbeans

import pytest
from tests.unit.modules.netbeans.fixtures import mock_salt_plugins


class TestFindPlugin(object):
  def test_version_is_not_installed(self, mock_salt_plugins):
    pytest.raises(
        netbeans.NoInstallFound, netbeans.find_plugin,
        "missing-plugin", "missing-version", root=tempfile.tempdir
    )

  def test_plugin_does_not_exists(self, mock_salt_plugins):
    netbeans.__salt__ = {
        "cmd.retcode": cmdmod.retcode,
        "cmd.run": cmdmod.run
    }
    pytest.raises(
        netbeans.NoPluginFound, netbeans.find_plugin,
        "missing-plugin", "salt-plugins", root=tempfile.tempdir
    )

  def test_plugin_is_available(self, mock_salt_plugins):
    (state, version) = netbeans.find_plugin(
        "com.jelastic.plugin.netbeans",
        "salt-plugins", root=tempfile.tempdir
    )
    assert state   == "available"
    assert version == "1.1.3"

  def test_plugin_is_installed_but_not_up_to_date(self, mock_salt_plugins):
    (state, version) = netbeans.find_plugin(
        "org.netbeans.modules.nbjunit",
        "salt-plugins", root=tempfile.tempdir
    )
    assert state   == "update"
    assert version == ("1.83.1", "1.84.1")

  def test_plugin_is_installed_but_not_enabled(self, mock_salt_plugins):
    (state, version) = netbeans.find_plugin(
        "org.netbeans.modules.php.zend",
        "salt-plugins", root=tempfile.tempdir
    )
    assert state   == "installed"
    assert version == "1.27.1"

  def test_plugin_is_enabled(self, mock_salt_plugins):
    (state, version) = netbeans.find_plugin(
        "org.netbeans.modules.versioning.core",
        "salt-plugins", root=tempfile.tempdir
    )
    assert state   == "enabled"
    assert version == "1.21.1.1.42"
