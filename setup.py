import setuptools

setuptools.setup(
    name="htmongui",
    version="0.0.0",
    description="HT monitor for POCAM calibration",
    author="A. Terliuk (for now)",
    python_requires=">=3.8",
    scripts=[
        "bin/htmongui",
    ]
)