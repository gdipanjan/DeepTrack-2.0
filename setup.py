import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="deeptrack", # Replace with your own username
    version="1.0.0",
    author="Benjamin Midtvedt",
    author_email="benmid@chalmers.com",
    description="A machine learning framework for digital microscopy.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/softmatterlab/DeepTrack-2.0",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)