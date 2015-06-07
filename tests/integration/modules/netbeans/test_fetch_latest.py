import imp

netbeans = imp.load_source('make', 'extentions/_modules/netbeans_linux.py')


def test_list_versions():
  versions = netbeans.list_versions()
  assert '8.0' in versions
  assert '8.0.1' in versions
  assert '8.0.2' in versions


def test_install_url_802_default():
  url = netbeans._get_installer_url('8.0.2')
  assert url == 'http://download.netbeans.org/netbeans/8.0.2/final/bundles/netbeans-8.0.2-linux.sh'


class TestPickLatestVersion(object):
  def test_pick_first(self):
    latest = netbeans._pick_latest_version(['1.2.3', '0'])
    assert latest == '1.2.3'

  def test_pick_last(self):
    latest = netbeans._pick_latest_version(['0', '0.1.2', '1.2.3'])
    assert latest == '1.2.3'
