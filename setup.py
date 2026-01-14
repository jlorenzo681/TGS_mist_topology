from setuptools import setup, find_packages

setup(
    name="mist_topology",
    version="1.0.0",
    description="Efficient bulk topology retrieval for Juniper Mist networks",
    author="jlorenzo681",
    author_email="jlorenzo681@gmail.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.6",
    install_requires=[
        "requests",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "mist-topology=mist_topology.cli:main",
        ],
    },
)
