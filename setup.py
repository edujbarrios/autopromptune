from setuptools import setup, find_packages

setup(
    name="autopromptune",
    version="0.1.0",
    author="Eduardo J. Barrios",
    author_email="eduardojbarriosgarcia@gmail.com",
    description=(
        "LLM-powered prompt tuning tool — MSc AI thesis research by Eduardo J. Barrios"
    ),
    url="https://github.com/edujbarrios/autopromptune",
    packages=find_packages(),
    package_data={"autopromptune": ["templates/*.j2"]},
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.0.0",
        "jinja2>=3.1.0",
        "streamlit>=1.32.0",
        "python-dotenv>=1.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "autopromptune=cli:main",
        ]
    },
)
