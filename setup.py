"""Packaging for the CloudOps Infra Toolkit.

Standard-library only at runtime; ``pytest`` is the only dev dependency.
"""

from setuptools import find_packages, setup

setup(
    name="cloudops-infra-toolkit",
    version="1.0.0",
    description="A dependency-free CLI for cost reporting, Docker health, "
    "and safe Kubernetes pod remediation.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Shivam Tripathi",
    license="MIT",
    packages=find_packages(exclude=("tests", "tests.*")),
    python_requires=">=3.9",
    install_requires=[],
    extras_require={"dev": ["pytest>=7.0"]},
    entry_points={
        "console_scripts": [
            "cloudops = cloudops.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Monitoring",
    ],
)
