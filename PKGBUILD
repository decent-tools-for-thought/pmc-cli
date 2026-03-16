pkgname=pmc-tool
pkgver=0.1.0
pkgrel=1
pkgdesc="Europe PMC CLI for literature and grants search"
arch=('any')
url="https://www.ebi.ac.uk/europepmc/"
license=('custom')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=()
sha256sums=()

build() {
  cd "$startdir"
  rm -rf build dist *.egg-info src/*.egg-info src/pmc_tool.egg-info
  python -m build --wheel --no-isolation
}

package() {
  cd "$startdir"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
