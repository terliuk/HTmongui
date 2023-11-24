import setuptools
def extract_requirements(rfile):
    with open(rfile) as f:
        req_list = f.read().splitlines()
    return req_list

# Get requirements from requirements.txt, stripping the version tags
requirements = extract_requirements("requirements.txt")

setuptools.setup(
    name="htmon",
    version="0.0.0",
    description="HT monitor for POCAM calibration",
    author="A. Terliuk (for now)",
    python_requires=">=3.8",
    install_requires=requirements,
    scripts=[
        "bin/htmongui",
    ]
)