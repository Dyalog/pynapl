from setuptools import setup

setup(
        name='APLPy',
        version='0.0.2.dev1',
        
        description='Python - Dyalog APL bridge',
        long_description="""
This package allows communication between Python and Dyalog APL.
""",
        
        url='TODO',
        
        author='TODO',
        author_email='TODO',

        license='TODO',

        classifiers=[
            'Development Status :: 2 - Pre-Alpha',

            'Intended Audience :: Developers',

            'Programming Language :: APL',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7'
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
        ],

        keywords='apl dyalog-apl bridge',

        packages=['aplpy'],

        package_data={
            'aplpy': [
                'Py.dyalog',
                'PyTest.dyalog',
                'WinPySlave.dyalog',
                'WinPySlave.dyapp'
            ]
        },
)
