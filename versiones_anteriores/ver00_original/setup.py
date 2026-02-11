from setuptools import setup, find_packages

setup(
    name="ianae",
    version="0.1",
    packages=find_packages(include=['ianae', 'ianae.*']),
    package_dir={'': '.'},
    install_requires=[
        'numpy',
        'torch',
        'torchvision', 
        'Pillow'
    ],
)
