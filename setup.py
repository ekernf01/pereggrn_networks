from setuptools import setup
from setuptools import find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
	long_description = fh.read()

setup(
    name='pereggrn_networks',
	py_modules=['pereggrn_networks'],
    version='0.0.1',
    description='Efficiently load and manipulate gene regulatory networks',
    long_description=long_description,
	long_description_content_type='text/markdown',
    author='Eric Kernfeld',
    author_email='eric.kern13@gmail.com',
    install_requires=[
        "pandas",
        "duckdb",
        "numpy",
		"pyarrow",
    ],
    python_requires=">=3.7", 
    url='https://github.com/ekernf01/pereggrn_networks',
)