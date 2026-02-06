import os
import shutil
import glob
import subprocess
import sys

src_dir = "bc7_src"

with open("setup_temp.py", "w") as f:
    f.write(f'''
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

extensions = [
    Extension(
        "bc7_encoder",
        sources=["{src_dir}/bc7_encoder.pyx", "{src_dir}/bc7enc.cpp"],
        include_dirs=[np.get_include(), "{src_dir}"],
        extra_compile_args=["/O2", "/std:c++17"],
        language="c++",
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
    )
]

setup(
    name="bc7_encoder",
    ext_modules=cythonize(extensions, language_level=3),
)
''')

print("Building extension...")
result = subprocess.run([sys.executable, "setup_temp.py", "build_ext", "--inplace"])

if result.returncode != 0:
    print("Build failed!")
    sys.exit(1)

print("\nCleaning intermediate files...")
patterns = [
    "bc7_src/bc7_encoder.cpp",
    "setup_temp.py",
]

for pattern in patterns:
    for file in glob.glob(pattern):
        os.remove(file)
        print(f"  Removed {file}")

if os.path.exists("build"):
    shutil.rmtree("build")
    print("  Removed build/ directory")

pyd_files = glob.glob("bc7_encoder*.pyd") + glob.glob("bc7_encoder*.so")
if pyd_files:
    print(f"\nBuild successful! Generated: {pyd_files[0]}")
else:
    print("\nWarning: No .pyd/.so file found")
