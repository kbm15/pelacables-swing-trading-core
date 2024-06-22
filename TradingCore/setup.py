from setuptools import setup, find_packages

setup(
    name="TradingCore",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "yfinance"
    ],
    description="A Python library for financial data analysis and backtesting.",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/TradingCore",
)
