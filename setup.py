try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='multiversion',
    author='Armin Ronacher',
    author_email='armin.ronacher@active-4.com',
    version='1.0',
    url='http://github.com/mitsuhiko/multiversion',
    py_modules=['multiversion'],
    description='Allows loading of multiple versions of the same Python module',
    long_description=None,
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python'
    ]
)
