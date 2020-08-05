from setuptools import setup, find_packages

setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name='learthengine',
    url='https://github.com/leonsnill/learthengine.git',
    author='Leon Nill',
    author_email='leon.nill@hu-berlin.de',
    # Needed to actually package something
    packages=find_packages(),
    # Needed for dependencies
    install_requires=['numpy', 'cdsapi'],
    # *strongly* suggested for sharing
    version='0.1',
    # The license can be anything you like
    license='MIT',
    description='A selection of earth engine function',
    # We will also need a readme eventually (there will be a warning)
    # long_description=open('README.txt').read(),
)
