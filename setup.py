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
        "attrs==23.1.0; python_version >= '3.5'",
        "autobahn[twisted]==23.1.2",
        "automat==22.10.0",
        "blinker==1.6.2; python_full_version >= '3.7.0'",
        "certifi==2022.12.7; python_version >= '3.6'",
        "cffi==1.15.1",
        "charset-normalizer==3.1.0; python_full_version >= '3.7.0'",
        "click==8.1.3; python_full_version >= '3.7.0'",
        "constantly==15.1.0",
        "cryptography==40.0.2; python_version >= '3.6'",
        "flask==2.3.2",
        "flask-restx==1.1.0",
        "hyperlink==21.0.0",
        "idna==3.4; python_version >= '3.5'",
        "importlib-metadata==6.6.0; python_version < '3.10'",
        "incremental==22.10.0",
        "itsdangerous==2.1.2; python_full_version >= '3.7.0'",
        "jinja2==3.1.2; python_full_version >= '3.7.0'",
        "jsonschema==4.17.3; python_full_version >= '3.7.0'",
        "markupsafe==2.1.2; python_full_version >= '3.7.0'",
        "netifaces==0.11.0",
        "pillow==9.5.0; python_full_version >= '3.7.0'",
        "plumbum==1.8.1",
        "pycparser==2.21; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pymcws==1.1.0",
        "pyrsistent==0.19.3; python_full_version >= '3.7.0'",
        "pytz==2023.3",
        "pyyaml==6.0",
        "requests==2.29.0",
        "setuptools==67.7.2; python_full_version >= '3.7.0'",
        "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "twisted==22.10.0; python_full_version >= '3.7.1'",
        "txaio==23.1.1; python_full_version >= '3.7.0'",
        "typing-extensions==4.5.0; python_full_version >= '3.7.0'",
        "urllib3==1.26.15; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5'",
        "wakeonlan==3.0.0",
        "werkzeug==2.3.3",
        "zipp==3.15.0; python_full_version >= '3.7.0'",
        "zope.interface==6.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'"
    ],
    tests_require=["pytest", "pytest-httpserver"],
    include_package_data=True,
    zip_safe=False,
)
