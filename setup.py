from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="next_attendance",
    version="1.0.0",
    description="Attendance app backend for Next Attendance mobile app — employee punch-in/out, kiosk mode, and person attendance tracking.",
    author="TechNiti",
    author_email="rohanrambhiya59@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
