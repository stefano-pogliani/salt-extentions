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
