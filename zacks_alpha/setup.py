from setuptools import setup, find_packages

setup(
    name='zacks_alpha',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'requests',
        'beautifulsoup4'
    ],
    description='A library to fetch and parse stock data from Zacks.com',
    author='wirestripper15',
    #author_email='your.email@example.com',
    #url='https://github.com/yourusername/zacks_data',  # Replace with your actual URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
