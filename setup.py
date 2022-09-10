import os
from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

if os.path.exists("cmdserver/VERSION"):
    with open("cmdserver/VERSION", "r") as f:
        version = f.read()
else:
    version = "0.0.1-alpha.1+dirty"

setup(
    name="ezmote-cmdserver",
    version=version,
    description="A small webapp which can be used for web based home cinema automation",
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Development Status :: 4 - Beta",
    ],
    url="http://github.com/3ll3d00d/cmdserver",
    author="Matt Khan",
    author_email="mattkhan+cmdserver@gmail.com",
    license="MIT",
    packages=find_packages(exclude=("test", "docs")),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "cmdserver = cmdserver.main:main",
        ],
    },
    install_requires=[
        "aniso8601==9.0.1; python_version >= '3.5'",
        "attrs==22.1.0; python_version >= '3.5'",
        "autobahn[twisted]==22.7.1",
        "automat==20.2.0",
        "certifi==2022.6.15.1; python_full_version >= '3.6.0'",
        "cffi==1.15.1",
        "charset-normalizer==2.1.1; python_full_version >= '3.6.0'",
        "click==8.1.3; python_version >= '3.7'",
        "constantly==15.1.0",
        "cryptography==38.0.1; python_full_version >= '3.6.0'",
        "flask==2.1.3",
        "flask-restx==0.5.1",
        "hyperlink==21.0.0",
        "idna==3.3; python_version >= '3.5'",
        "importlib-metadata==4.12.0; python_version < '3.10'",
        "incremental==21.3.0",
        "itsdangerous==2.1.2; python_version >= '3.7'",
        "jinja2==3.1.2; python_version >= '3.7'",
        "jsonschema==4.16.0; python_version >= '3.7'",
        "markupsafe==2.1.1; python_version >= '3.7'",
        "netifaces==0.11.0",
        "pillow==9.2.0; python_version >= '3.7'",
        "plumbum==1.7.2",
        "pycparser==2.21; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pymcws==1.1.0",
        "pyrsistent==0.18.1; python_version >= '3.7'",
        "pytz==2022.2.1",
        "pyyaml==6.0",
        "requests==2.28.1",
        "setuptools==65.3.0; python_version >= '3.7'",
        "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "twisted==22.8.0; python_full_version >= '3.7.1'",
        "txaio==22.2.1; python_full_version >= '3.6.0'",
        "typing-extensions==4.3.0; python_version >= '3.7'",
        "urllib3==1.26.12; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5' and python_version < '4'",
        "wakeonlan==2.1.0",
        "werkzeug==2.1.2",
        "zipp==3.8.1; python_version >= '3.7'",
        "zope.interface==5.4.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
    ],
    tests_require=["pytest", "pytest-httpserver"],
    include_package_data=True,
    zip_safe=False,
)
