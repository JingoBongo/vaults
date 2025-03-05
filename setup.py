from setuptools import setup, find_packages

setup(
    name='vaults',
    version='1.0.0',
    description='A persistent key-value store using SQLite with an async interface.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Mscebec',
    author_email='mpakaboy@gmail.com',
    url='https://github.com/JingoBongo/vaults',  # Update with your repository URL
    py_modules=['vaults'],
    packages=find_packages(),
    install_requires=[
        'SQLAlchemy'
    ],
    classifiers=[
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
