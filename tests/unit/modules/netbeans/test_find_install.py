import sys
sys.path.append("extentions/_modules")
sys.path.append("extentions")

import tempfile

from salt.modules import cmdmod

import pytest

import netbeans_linux as netbeans

from tests.unit.modules.netbeans.fixtures import mock_salt_demo
from tests.unit.modules.netbeans.fixtures import mock_salt_test


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


class TestPickLatestVersion(object):
  def test_pick_first(self):
    latest = netbeans.pick_latest_version(['1.2.3', '0'])
    assert latest == '1.2.3'

  def test_pick_last(self):
    latest = netbeans.pick_latest_version(['0', '0.1.2', '1.2.3'])
    assert latest == '1.2.3'
