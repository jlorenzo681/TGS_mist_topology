from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="mist_topology",
    version="1.0.0",
    description="Efficient bulk topology retrieval for Juniper Mist networks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="jlorenzo681",
    author_email="jlorenzo681@gmail.com",
    url="https://github.com/jlorenzo681/TGS_mist_topology",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.6",
    install_requires=[
        "requests",
        "python-dotenv",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="juniper, mist, topology, network, api, rest, bulk",
    entry_points={
        "console_scripts": [
            "mist-topology=mist_topology.cli:main",
        ],
    },
)
