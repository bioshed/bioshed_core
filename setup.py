from setuptools import setup
setup(
    name='bioshed',
    version='0.1.21',
    description='BioShed Cloud Bioinformatics Tookit',
    install_requires=[
        'boto3',
        'pyyaml',
        'pandas',
        'requests'
    ],
    include_package_data=True,
    python_requires='>=3.0',            # Minimum version requirement of the package
    py_modules=["bioshed"],             # Name of the python package
    package_dir={'bioshed':'bioshed/src'},     # Directory of the source code of the package
    packages=['bioshed/src/', 'bioshed/src/bioshed_utils', 'bioshed/src/bioshed_atlas', 'bioshed/src/bioshed_atlas/bioshed_utils', 'bioshed/src/bioshed_atlas/files'],
    package_data={'bioshed.src.bioshed_utils': ['bioshed_utils/*.json', 'bioshed_utils/*.yaml'], \
                  'bioshed.src.bioshed_atlas.files': ['bioshed_atlas/files/*.txt']},
    entry_points={
        'console_scripts': [
            'bioshed=bioshed.src.bioshed:bioshed_cli_entrypoint'
        ]
    }
)