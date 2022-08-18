from setuptools import setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

version = "1.0.2.7"

setup(
    name="ajm_discord",
    version=version,
    py_modules=["ajm_discord"],
    author="Andrew McGrail",
    author_email="andrewjerrismcgrail@gmail.com",
    url="https://github.com/challos/ajm_discord",
    license="MIT License (MIT)",
    description="Some useful discord cog/bots.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=["py-cord (>=2.0.0rc1)", "python-docx"],
    packages=["ajm_discord"],
)
